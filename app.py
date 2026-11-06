import base64, csv, hashlib, hmac, io, json, os, sqlite3, time
from datetime import date, datetime
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from compliance import TEMPLATES, can_contact, safe
from scoring import score_loan

SECRET = os.environ["APP_SECRET"].encode()  # required; never committed
DB = os.environ.get("DB_PATH", "collections.db")
OUTCOMES = {"paid", "promise", "not_reachable", "dispute"}
app = FastAPI(title="Field Collections")


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, name TEXT, role TEXT, branch TEXT, pincodes TEXT, pw TEXT);
    CREATE TABLE IF NOT EXISTS loans(id TEXT PRIMARY KEY, borrower TEXT, phone TEXT, pincode TEXT, outstanding INTEGER, dpd INTEGER, promise_date TEXT, promise_status TEXT, officer_id INTEGER, branch TEXT, score REAL, reasons TEXT);
    CREATE TABLE IF NOT EXISTS outcomes(client_id TEXT PRIMARY KEY, loan_id TEXT, officer_id INTEGER, type TEXT, promise_date TEXT, lat REAL, lng REAL, at TEXT);
    CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, loan_id TEXT, officer_id INTEGER, channel TEXT, at TEXT, blocked INTEGER);
    """)
    c.commit(); c.close()


def hash_pw(pw, salt=None):
    salt = salt or os.urandom(8).hex()
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()


def _sig(b):
    return hmac.new(SECRET, b.encode(), "sha256").hexdigest()


def me(authorization: str = Header("")):
    try:
        b, s = authorization.removeprefix("Bearer ").split(".")
        if not hmac.compare_digest(s, _sig(b)):
            raise ValueError
        p = json.loads(base64.urlsafe_b64decode(b))
        if p["exp"] < time.time():
            raise ValueError
    except Exception:
        raise HTTPException(401, "Not signed in")
    c = conn(); u = c.execute("SELECT * FROM users WHERE id=?", (p["u"],)).fetchone(); c.close()
    if not u:
        raise HTTPException(401, "Unknown user")
    return dict(u)


def need(role):
    def dep(u=Depends(me)):
        if u["role"] != role:
            raise HTTPException(403, "Not allowed for your role")
        return u
    return dep


def own(c, u, lid):
    l = c.execute("SELECT * FROM loans WHERE id=? AND officer_id=?", (lid, u["id"])).fetchone()
    if not l:
        raise HTTPException(404, "Loan not found")
    return l


def rescore(c, lid):
    l = dict(c.execute("SELECT * FROM loans WHERE id=?", (lid,)).fetchone())
    n = c.execute("SELECT COUNT(*) FROM outcomes WHERE loan_id=? AND type='not_reachable'", (lid,)).fetchone()[0]
    s, r = score_loan(l, n, date.today())
    c.execute("UPDATE loans SET score=?, reasons=? WHERE id=?", (s, json.dumps(r), lid))


def import_csv(c, text, today=None):
    """Validate rows, auto-assign by pincode then lowest workload, score."""
    today, ok, errors = today or date.today(), 0, []
    officers = [dict(o) for o in c.execute("SELECT * FROM users WHERE role='officer'")]
    load = lambda o: c.execute("SELECT COUNT(*) FROM loans WHERE officer_id=?", (o["id"],)).fetchone()[0]
    for n, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            pin, pd = row["pincode"].strip(), (row.get("promise_date") or "").strip()
            amt, dpd = int(row["outstanding"]), int(row["dpd"])
            assert len(pin) == 6 and pin.isdigit() and amt > 0 and 1 <= dpd <= 90 and row["loan_id"].strip()
            st = "none" if not pd else ("broken" if date.fromisoformat(pd) < today else "pending")
        except Exception:
            errors.append(f"row {n}: invalid or missing field"); continue
        ex = c.execute("SELECT officer_id FROM loans WHERE id=?", (row["loan_id"],)).fetchone()
        o = next((x for x in officers if ex and x["id"] == ex[0]), None) \
            or min([x for x in officers if pin in x["pincodes"].split(",")] or officers, key=load)
        c.execute("INSERT OR REPLACE INTO loans VALUES(?,?,?,?,?,?,?,?,?,?,0,'[]')",
                  (row["loan_id"], row["borrower"], row["phone"], pin, amt, dpd, pd or None, st, o["id"], o["branch"]))
        rescore(c, row["loan_id"]); ok += 1
    return {"imported": ok, "errors": errors}


class Login(BaseModel): username: str; password: str
class Csv(BaseModel): text: str
class Out(BaseModel): client_id: str; type: str; promise_date: str | None = None; lat: float | None = None; lng: float | None = None
class Contact(BaseModel): channel: str


@app.post("/api/login")
def login(b: Login):
    c = conn(); u = c.execute("SELECT * FROM users WHERE username=?", (b.username,)).fetchone(); c.close()
    if not u or not hmac.compare_digest(hash_pw(b.password, u["pw"].split("$")[0]), u["pw"]):
        raise HTTPException(401, "Wrong username or password")
    p = base64.urlsafe_b64encode(json.dumps({"u": u["id"], "exp": time.time() + 8 * 3600}).encode()).decode()
    return {"token": p + "." + _sig(p), "name": u["name"], "role": u["role"]}


@app.post("/api/import")
def imp(b: Csv, u=Depends(need("manager"))):
    c = conn(); r = import_csv(c, b.text); c.commit(); c.close()
    return r


@app.get("/api/loans")
def loans(u=Depends(me)):
    c = conn()
    q, a = ("WHERE officer_id=?", (u["id"],)) if u["role"] == "officer" else ("", ())
    rows = c.execute(f"SELECT * FROM loans {q} ORDER BY score DESC", a).fetchall(); c.close()
    out = []
    for r in rows:
        d = dict(r); d.pop("phone"); d["reasons"] = json.loads(d["reasons"]); out.append(d)  # phone only via the contact gate
    return out


@app.post("/api/loans/{lid}/outcome")
def outcome(lid: str, b: Out, u=Depends(need("officer"))):
    if b.type not in OUTCOMES:
        raise HTTPException(422, "Unknown outcome")
    if b.type == "promise":
        try: date.fromisoformat(b.promise_date or "")
        except ValueError: raise HTTPException(422, "A promise needs a date")
    c = conn(); own(c, u, lid)
    new = c.execute("INSERT OR IGNORE INTO outcomes VALUES(?,?,?,?,?,?,?,?)",  # client_id makes offline retries safe
                    (b.client_id, lid, u["id"], b.type, b.promise_date, b.lat, b.lng, datetime.now().isoformat())).rowcount
    if new and b.type == "promise":
        c.execute("UPDATE loans SET promise_date=?, promise_status='pending' WHERE id=?", (b.promise_date, lid))
    if new and b.type == "paid":
        c.execute("UPDATE loans SET promise_status='kept' WHERE id=?", (lid,))
    if new:
        rescore(c, lid)
    c.commit(); c.close()
    return {"saved": bool(new)}


@app.post("/api/loans/{lid}/contact")
def contact(lid: str, b: Contact, u=Depends(need("officer"))):
    if b.channel not in ("call", "message"):
        raise HTTPException(422, "Unknown channel")
    c = conn(); l = own(c, u, lid); ok = can_contact()
    c.execute("INSERT INTO attempts(loan_id,officer_id,channel,at,blocked) VALUES(?,?,?,?,?)",
              (lid, u["id"], b.channel, datetime.now().isoformat(), int(not ok)))
    c.commit(); c.close()
    if not ok:
        raise HTTPException(403, "Contact is allowed only between 8 am and 7 pm")
    return {"phone": l["phone"]}


@app.get("/api/loans/{lid}/draft")
def draft(lid: str, lang: str = "en", u=Depends(need("officer"))):
    c = conn(); l = own(c, u, lid); c.close()
    if lang not in TEMPLATES:
        raise HTTPException(422, "Unsupported language")
    pd = l["promise_date"]
    when = {"en": f"by {pd}" if pd else "at the earliest", "hi": f"{pd} तक" if pd else "जल्द से जल्द"}[lang]
    text = TEMPLATES[lang].format(name=l["borrower"], loan=lid, amt=f"{l['outstanding']:,}", when=when)
    if not safe(text):
        raise HTTPException(422, "Draft blocked by language filter")
    return {"text": text}


@app.get("/api/dashboard")
def dashboard(u=Depends(need("manager"))):
    c = conn()
    br = [{"branch": r["branch"], "loans": r["n"], "roll_rate": round(100 * r["rolled"] / r["n"], 1), "broken": r["broken"]}
          for r in c.execute("SELECT branch, COUNT(*) n, SUM(dpd>30) rolled, SUM(promise_status='broken') broken FROM loans GROUP BY branch")]
    bp = [dict(r) for r in c.execute("SELECT l.id, l.borrower, l.promise_date, u.name officer FROM loans l JOIN users u ON u.id=l.officer_id WHERE promise_status='broken'")]
    act = [dict(r) for r in c.execute("SELECT u.name, (SELECT COUNT(*) FROM outcomes o WHERE o.officer_id=u.id) outcomes, (SELECT COUNT(*) FROM attempts a WHERE a.officer_id=u.id AND a.blocked=1) blocked FROM users u WHERE role='officer'")]
    c.close()
    return {"branches": br, "broken_promises": bp, "activity": act}


init()


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
