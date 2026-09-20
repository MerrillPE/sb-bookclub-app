# Spine Busters Book Club Tracker

A small Flask app for a small book club to track books read, log individual ratings/comments, and browse reading history. Membership is invite-only — there's no public signup, an admin generates a one-time invite link for each person to register with.

See `docs/sb-bookclub-app-plan.md` for the full requirements/design doc.

## Running it locally

**1. Clone and set up a virtual environment**
```
git clone git@github.com:MerrillPE/sb-bookclub-app.git
cd sb-bookclub-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Create a `.env` file** in the repo root with:
```
SECRET_KEY=<a random value, see below>
FLASK_APP=run.py
FLASK_DEBUG=1
```
Generate a real `SECRET_KEY` rather than typing one by hand:
```
python3 -c "import secrets; print(secrets.token_hex(32))"
```
(No database URL is needed — it defaults to a local SQLite file at `instance/app.db` if `SQLALCHEMY_DATABASE_URI` isn't set.)

**3. Create the database**
```
flask db upgrade
```

**4. Create your account**

There's no signup page — accounts are created via invite link:
```
flask create-invite
```
This prints a token/path. Once the app is running (next step), visit `http://127.0.0.1:5000/auth/register/<the printed token>` to create your account.

**5. Run the app**
```
flask run
```
Visit `http://127.0.0.1:5000`.

## Making an account an admin

Admins can edit/delete any book and (eventually) manage invites from a web UI — for now this has to be set directly, via `flask shell`:
```python
>>> from app.models import Member
>>> from app.extensions import db
>>> m = Member.query.filter_by(username="your-username").first()
>>> m.is_admin = True
>>> db.session.commit()
```

## Editing styles

CSS is built from Tailwind and the compiled output is committed to git, so you don't need Node installed just to run the app. If you're changing templates/styles:
```
npm install
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```
