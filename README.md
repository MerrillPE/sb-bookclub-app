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
This prints a token/path. Once the app is running (next step), visit `http://127.0.0.1:5000/auth/register/<the printed token>` to create your account — or just go to the login page and click "Have an invite token?" to paste the bare token in directly instead of using the full link.

**5. Run the app**
```
flask run
```
Visit `http://127.0.0.1:5000`.

## Making an account an admin

Admins can edit/delete any book and manage invites/password resets from a web UI (`/admin/invites`, `/admin/members`, both linked from the account dropdown once you're an admin) — but becoming the *first* admin has to be set directly, via `flask shell`, since there's no bootstrapping route:
```python
>>> from app.models import Member
>>> from app.extensions import db
>>> m = Member.query.filter_by(username="your-username").first()
>>> m.is_admin = True
>>> db.session.commit()
```

## Forgot your password?

There's no email integration, so password resets are admin-initiated: an admin generates a one-time reset link for you from `/admin/members`, valid for 24 hours. Visit the link (or paste the bare token into "Have a password reset token?" on the login page) to set a new password yourself — the admin never sees or chooses it.

## Editing styles

CSS is built from Tailwind and the compiled output is committed to git, so you don't need Node installed just to run the app. If you're changing templates/styles (Node 22+ recommended — Node 18 is EOL):
```
npm install
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```
