# Programming Radio contributor guide

## Product

Programming Radio is a deliberately small, non-commercial web radio for focused programming. It discovers independent music through Jamendo, groups tracks into administrator-managed stations, and plays Jamendo-hosted audio in the browser.

Keep the interface quiet, fast, and usable without a frontend build step. The visual language is dark, restrained neon: inspiration rather than a copy of nightride.fm.

## Stack and commands

- Python 3.12+, FastAPI, Jinja2, HTMX, Tortoise ORM, PostgreSQL.
- Local database: `pradio`, role `pradio`. Read credentials from `.env`; never commit `.env`.
- Install: `.venv/bin/pip install -e '.[dev]'`
- Migrations: use Tortoise ORM's built-in migration CLI, not Aerich.
- Create migrations: `.venv/bin/tortoise makemigrations --name <name>`
- Apply migrations: `.venv/bin/tortoise migrate`
- Seed defaults: `.venv/bin/python -m app.seed`
- Run: `.venv/bin/uvicorn app.main:app --reload`
- Check: `.venv/bin/ruff check .` and `.venv/bin/pytest`

## Architecture

- `app/models.py`: persisted station and Jamendo track metadata.
- `app/jamendo.py`: the only module that talks to Jamendo. Preserve caching and rate-limit-conscious behavior.
- `app/routes.py`: server-rendered public/admin routes and the small player JSON endpoint.
- `app/templates/` and `app/static/`: progressive server UI; use HTMX where it removes page-level boilerplate.
- `app/migrations/`: committed native Tortoise migrations.

## Product and licensing invariants

- The app is non-commercial. Do not add ads, subscriptions, sponsorship, donations, or other monetization without revisiting Jamendo's current terms.
- Store every fetched track's metadata, license URL, attribution, original API payload, and station association in PostgreSQL.
- Play audio from Jamendo's streaming URL. Do not proxy, mirror, or bulk-download audio by default.
- Any future local download feature must check `audiodownload_allowed`, use Jamendo's documented download endpoint, preserve attribution/license data, and account for removal when a work becomes unavailable. It needs an explicit licensing review before implementation.
- Always show track/artist attribution and a license link in the player.
- Never expose the Jamendo client ID in browser code; API calls go through the FastAPI service.

## Development rules

- Keep changes small and readable; avoid introducing a SPA framework or background queue until real usage requires it.
- Schema changes require a committed migration. Never use automatic schema generation in application startup.
- Preserve user changes in a dirty worktree. Use `ruff` and focused tests before handoff.
- Treat admin authentication and all mutations as security-sensitive. Production deployments require strong `.env` secrets and HTTPS-secure cookies.
