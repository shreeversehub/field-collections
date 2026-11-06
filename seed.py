import random
from datetime import date, timedelta
import app


def run():
    c = app.conn()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return
    pw = app.hash_pw("Demo@1234")
    for u in [("rahul", "Rahul Chouhan", "officer", "Indore-East", "452001,452010"),
              ("neha", "Neha Solanki", "officer", "Indore-West", "452002,452003"),
              ("imran", "Imran Qureshi", "officer", "Indore-East", "452011,452012"),
              ("manager", "Head of Collections", "manager", "All", "")]:
        c.execute("INSERT INTO users(username,name,role,branch,pincodes,pw) VALUES(?,?,?,?,?,?)", (*u, pw))
    rng, today = random.Random(7), date.today()
    rows = ["LN-10293,Company B (packaging unit),9000000001,452001,640000,12,2026-11-05",
            "LN-10871,Company C (fertiliser shop),9000000002,452002,310000,27,",
            "LN-11930,Company D (printing press),9000000003,452011,220000,19,2026-10-31"]
    for i in range(21):
        pd = (today + timedelta(days=rng.randint(-8, 6))).isoformat() if rng.random() < .4 else ""
        rows.append(f"LN-{12000+i},Trader {i+1},90000{10+i:05d},{rng.choice(['452001','452002','452003','452010','452011','452012'])},{rng.randrange(80000, 700000, 5000)},{rng.randint(1, 60)},{pd}")
    app.import_csv(c, "loan_id,borrower,phone,pincode,outstanding,dpd,promise_date\n" + "\n".join(rows))
    c.commit(); c.close()


if __name__ == "__main__":
    run()
