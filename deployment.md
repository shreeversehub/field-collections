# Deployment

## Run locally
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `export APP_SECRET=$(python -c "import secrets;print(secrets.token_hex(24))")`
4. `python seed.py` (creates demo users and 24 sample overdue loans)
5. `uvicorn app:app --reload` then open http://localhost:8000
6. Tests: `pytest -q`

## Environment variables (names only)
`APP_SECRET` (required, signs login tokens), `DB_PATH` (optional, SQLite file path)

## Deployed with
Not deployed yet. Any host that runs `uvicorn app:app --host 0.0.0.0 --port $PORT` works (Render or Railway). Set `APP_SECRET`, run `python seed.py` once, and use a persistent disk for `DB_PATH`.

## Demo logins (sample data only)
Officers: `rahul`, `neha`, `imran`. Manager: `manager`. Password for all: `Demo@1234`
