from datetime import date, datetime
from fastapi.testclient import TestClient
import app, seed
from compliance import IST, can_contact
from scoring import score_loan

seed.run()
cl = TestClient(app.app)
auth = lambda u: {"Authorization": "Bearer " + cl.post("/api/login", json={"username": u, "password": "Demo@1234"}).json()["token"]}
first = lambda u: cl.get("/api/loans", headers=auth(u)).json()[0]["id"]


def test_contact_window_edges():
    t = lambda h, m=0: datetime(2026, 11, 6, h, m, tzinfo=IST)
    assert can_contact(t(8)) and can_contact(t(18, 59))
    assert not can_contact(t(7, 59)) and not can_contact(t(19))


def test_broken_promise_outranks_kept():
    base = dict(outstanding=220000, dpd=19, promise_date="2026-10-31", promise_status="broken")
    broken, _ = score_loan(base, 0, date(2026, 11, 6))
    kept, _ = score_loan({**base, "promise_status": "kept"}, 0, date(2026, 11, 6))
    assert broken > kept


def test_reasons_max_three():
    assert len(score_loan(dict(outstanding=640000, dpd=29, promise_date=None, promise_status="none"), 3, date.today())[1]) == 3


def test_requires_login_and_role():
    assert cl.get("/api/loans").status_code == 401
    assert cl.post("/api/import", json={"text": ""}, headers=auth("rahul")).status_code == 403


def test_officer_sees_only_own_loans():
    mine = cl.get("/api/loans", headers=auth("neha")).json()
    assert mine and "phone" not in mine[0]
    assert cl.post(f"/api/loans/{first('rahul')}/outcome", headers=auth("neha"),
                   json={"client_id": "x1", "type": "paid"}).status_code == 404


def test_outcome_is_idempotent_and_validated():
    h, lid = auth("rahul"), first("rahul")
    body = {"client_id": "c-1", "type": "not_reachable", "lat": 22.7, "lng": 75.8}
    assert cl.post(f"/api/loans/{lid}/outcome", json=body, headers=h).json()["saved"] is True
    assert cl.post(f"/api/loans/{lid}/outcome", json=body, headers=h).json()["saved"] is False
    assert cl.post(f"/api/loans/{lid}/outcome", json={"client_id": "c-2", "type": "promise"}, headers=h).status_code == 422


def test_blocked_contact_is_refused_and_logged(monkeypatch):
    monkeypatch.setattr(app, "can_contact", lambda: False)
    assert cl.post(f"/api/loans/{first('rahul')}/contact", json={"channel": "call"}, headers=auth("rahul")).status_code == 403
    assert any(a["blocked"] >= 1 for a in cl.get("/api/dashboard", headers=auth("manager")).json()["activity"])


def test_import_rejects_bad_rows_and_assigns_by_pincode():
    csv = "loan_id,borrower,phone,pincode,outstanding,dpd,promise_date\nLN-1,A,9,452003,100000,5,\nLN-2,B,9,12,100000,5,\n"
    r = cl.post("/api/import", json={"text": csv}, headers=auth("manager")).json()
    assert r["imported"] == 1 and len(r["errors"]) == 1
    assert "LN-1" in {l["id"] for l in cl.get("/api/loans", headers=auth("neha")).json()}


def test_draft_is_template_only():
    assert "बकाया" in cl.get(f"/api/loans/{first('rahul')}/draft?lang=hi", headers=auth("rahul")).json()["text"]
