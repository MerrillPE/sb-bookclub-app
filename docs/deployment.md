# Deployment

This app runs in production as a Docker container (gunicorn) on **Google Cloud Run**, against a **Neon** Postgres database. The two are deliberately separate services — Cloud Run redeploys replace the running container entirely, so keeping the database on its own host (rather than, say, a SQLite file baked into the container) is what makes app redeploys not wipe data.

## Why this combination

Checked directly against current pricing/policy before deciding (see `docs/sb-bookclub-app-plan.md`'s Tech Stack table for the short version):

- **Cloud Run** has a free tier (2M requests/month, scales to zero when idle) that comfortably covers a 4-person app — effectively $0/month.
- **Cloud SQL for Postgres**, the fully-GCP-native alternative, has a ~$30+/month baseline regardless of actual usage — not worth it at this scale.
- **Neon**'s free Postgres tier has no hard expiration and needs no credit card. Render's free Postgres is auto-deleted after 30 days + a 14-day grace period; Supabase's free tier pauses (recoverable, but unreachable until manually restored) after 7 days of database inactivity — both real risks for a low-traffic hobby app. Railway and Fly.io no longer have meaningful free tiers as of 2026.

## One-time setup

### 1. Create the Neon database

Create a free Neon project (pick a region close to wherever you'll run Cloud Run, to minimize latency between the two). Copy the **pooled** connection string, not the direct one — Cloud Run can run more than one container instance at once under load, each holding its own connection pool, and Neon's PgBouncer-based pooler handles that better than a direct connection. It looks like:
```
postgresql://<user>:<password>@<host>-pooler.<region>.aws.neon.tech/<dbname>?sslmode=require
```

**Get this from the Neon dashboard's Connection Details panel — that's all this app needs.** Neon's project-creation flow also surfaces a CLI-based onboarding prompt (`npm i -g neon`, `neon login`, `neon mcp`, `neon skills`, a `neon.ts` policy file via `@neon/config`, `neon deploy`). Skip all of it here: that tooling is for declaratively managing Neon-specific concerns — per-branch compute/autoscaling policies, "Neon Functions" (serverless functions Neon itself hosts), and an MCP server + agent-skills package that give AI coding agents live, ongoing database-management tools. None of that applies to this app's architecture (Cloud Run for compute, Neon purely as a managed Postgres instance, one environment, no branch-per-PR workflow) — it would only add a global npm install, an interactive OAuth login, a new MCP server (a real capability/trust change for any AI agent working in this repo), and this repo's first TypeScript/Node runtime file, for no benefit here. The plain connection string above is genuinely sufficient.

### 2. Generate a production `SECRET_KEY`

Never reuse your local dev value:
```
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Enable the required GCP APIs

```
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### 4. Build and deploy

This project's actual values — used literally below rather than as placeholders, since this doc describes this specific deployment, not a generic template:
- **Project ID**: `sb-bookclub-app`
- **Region**: `us-west1` (The Dalles, Oregon) — the closest GCP region to the Neon database (also Oregon, AWS `us-west-2`), minimizing Cloud Run↔Neon latency. Earlier drafts of this doc briefly moved this to `us-central1`, reasoning that `gcloud run domain-mappings` (see "Custom domain" below) only worked in a handful of regions per Google's own Preview documentation — in practice, domain mapping worked fine directly against `us-west1`, so that move was unnecessary and reverted. Worth knowing if you hit a real region restriction later: the documented list was `us-central1`/`us-east1`/`europe-west1`/`asia-northeast1`, but don't assume it's accurate or current without checking.

Create an Artifact Registry Docker repository once per project (`gcr.io`/Container Registry was fully shut down in March 2025 — Artifact Registry is the current replacement, and is what `gcloud builds submit --tag` now needs to target):
```
gcloud artifacts repositories create sb-bookclub-app \
  --repository-format=docker \
  --location=us-west1 \
  --description="sb-bookclub-app container images"
```
Then build and deploy:
```
gcloud builds submit --tag us-west1-docker.pkg.dev/sb-bookclub-app/sb-bookclub-app/sb-bookclub-app

gcloud run deploy sb-bookclub-app \
  --image us-west1-docker.pkg.dev/sb-bookclub-app/sb-bookclub-app/sb-bookclub-app \
  --region us-west1 \
  --allow-unauthenticated \
  --set-env-vars="SECRET_KEY=<from step 2>,SQLALCHEMY_DATABASE_URI=<from step 1>,FLASK_DEBUG=0,OPEN_LIBRARY_CONTACT=<a real contact URL or email>"
```
If your database URL or any value contains a comma, `--set-env-vars`' comma-separated `KEY=VALUE` list will misparse it — use `--set-env-vars="^:^KEY=VALUE:KEY2=VALUE2"` (custom delimiter) or an `--env-vars-file` instead.

For anything beyond a first pass, consider moving `SECRET_KEY` and the database URL into [Secret Manager](https://cloud.google.com/secret-manager) and referencing them via `--set-secrets` instead of plain `--set-env-vars` — more setup, but the values won't be visible in the Cloud Run service's own config/logs to anyone with read access to it.

### 5. Run the first migration

Cloud Run has no built-in "release phase" hook the way some other platforms do, and Neon accepts direct external connections (no VPC/proxy needed, unlike Cloud SQL) — so for an app this size, the simplest approach is running migrations from your own machine, pointed at the production database:
```
export SQLALCHEMY_DATABASE_URI="<the same Neon connection string from step 1>"
flask db upgrade
unset SQLALCHEMY_DATABASE_URI
```
If this gets tedious later, a [Cloud Run Job](https://cloud.google.com/run/docs/create-jobs) running `flask db upgrade` against the same image is a reasonable next step — not needed for a first deploy.

### 6. Create the first invite and promote yourself to admin

Same pattern as local dev (see the README's "Making an account an admin" section), just pointed at the production database:
```
export SQLALCHEMY_DATABASE_URI="<the same Neon connection string>"
flask create-invite
```
Visit `https://<your-cloud-run-url>/auth/register/<the printed token>` to create your account, then:
```
flask shell
>>> from app.models import Member
>>> from app.extensions import db
>>> m = Member.query.filter_by(username="your-username").first()
>>> m.is_admin = True
>>> db.session.commit()
```
```
unset SQLALCHEMY_DATABASE_URI
```

### 7. Verify

Visit the Cloud Run URL, log in, add a book, and specifically try the Open Library lookup — this app's only outbound HTTP call (see `CLAUDE.md`'s "Open Library auto-fill"/"Open Library cover picker" notes) needs no special Cloud Run config, but is worth checking for real once actually deployed rather than assuming it behaves the same as on localhost.

## Custom domain (optional)

You need a domain name registered somewhere first — any standard registrar works (Cloudflare Registrar, Namecheap, Porkbun, Squarespace, etc.); it doesn't matter which, since you're just pointing DNS records at Google afterward. (Google Domains, the old GCP-integrated consumer registrar, shut down in 2023 — don't look for it.)

This app uses **`sbbookclub.app`**, registered via Cloud Domains and hosted on Cloud DNS (the auto-created `sbbookclub-app` zone) — both within this same GCP project, so DNS record changes happen in the same console as everything else. `.app` is an HSTS-preloaded TLD (baked into browsers, not opt-in): the domain is unreachable over plain HTTP unconditionally, so HTTPS has to be fully working before it's reachable at all — no gradual rollout. Cloud Run's managed cert (provisioned automatically as part of the mapping below) handles that; no app or code changes needed.

Two ways to connect a domain to Cloud Run:

- **`gcloud run domain-mappings` (used here)**: free, one command (or the Cloud Run console's "Manage Custom Domains" → "Add Mapping"). Still `beta`/Preview as of this writing (not GA) — Google's own docs describe it as limited to a handful of regions and "not production-ready" due to latency at scale, but neither concern held up in practice here: it worked directly against `us-west1` (not one of the documented supported regions) with no issues, and the latency caveat doesn't really apply to a private 4-person app regardless.
- **External Application Load Balancer + Serverless NEG**: Google's actual recommended production path, guaranteed to work with any Cloud Run region, but costs a real ~$18–25/month minimum just for the load balancer's forwarding rule — regardless of traffic. Not used here, since the whole point of this setup is staying near $0/month and the simpler path already worked.

If your Google account/domain isn't already verified in [Search Console](https://search.google.com/search-console), verify it there first — required before Cloud Run will let you map it (skipped automatically if the domain was registered through Cloud Domains on the same account, as here).

```
gcloud beta run domain-mappings create --service=sb-bookclub-app --domain=sbbookclub.app --region=us-west1
```
This prints the DNS records to add — for `sbbookclub.app` (an apex/root domain, no subdomain), 4 `A` records and 4 `AAAA` records, added as two record sets (one `A`, one `AAAA`, each holding all 4 values) in the `sbbookclub-app` Cloud DNS zone, not as 8 separate record sets. Then wait — SSL cert provisioning is usually ~15 minutes but can take up to 24 hours, during which the domain is fully unreachable (not just a browser warning) due to the HSTS-preload behavior noted above.

Check status with:
```
gcloud beta run domain-mappings describe --domain=sbbookclub.app --region=us-west1
```
`Ready: True` in the output means it's live.

## Redeploying

**Code-only changes** (no schema change): just repeat step 4 (`gcloud builds submit` + `gcloud run deploy`). The Neon database is never touched by this — this is what makes redeploys safe for existing data.

**Schema changes**: generate the migration locally as usual (`flask db migrate -m "..."`, review it, commit it), then repeat step 5 against the production database *in addition to* step 4, before or after deploying the new revision (order matters only if the new code depends on the new column/table existing — for an additive migration like a new nullable column, either order is safe).

## Things to know

- No CI/CD pipeline exists yet (e.g. auto-deploy on push to `main`) — every deploy above is a manual `gcloud` invocation. Worth adding later (GitHub Actions + `gcloud builds submit`/`gcloud run deploy`, or a Cloud Build trigger) once the manual flow feels repetitive, not before.
- Consider setting a GCP budget alert — Cloud Run is usage-based, and while the free tier should cover this app's real traffic, it's cheap insurance against a surprise bill from unexpected load or a misconfiguration.
- Static files (CSS/JS) are served directly by Flask — fine at this scale, no CDN needed.
- Nothing in this app assumes a writable local disk beyond the SQLite fallback path (unused once `SQLALCHEMY_DATABASE_URI` is set) — cover images are always external URLs (`Book.cover_url`), never downloaded/cached locally, so there's nothing here that Cloud Run's ephemeral filesystem would break.
- The synchronous `requests.get()` calls in the Open Library lookup routes (`app/books/routes.py`) tie up whichever gunicorn worker handles that request for up to their 5s timeout. Low risk at 2 workers / 4 users, but worth remembering if the app ever feels sluggish under concurrent use.
