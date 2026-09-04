# Programming Radio

A small non-commercial programming radio built with FastAPI, Tortoise ORM, HTMX and PostgreSQL. Jamendo and Audius track metadata is cached in PostgreSQL; audio is played directly from its source provider.

## Run locally

1. Change `SECRET_KEY` and `ADMIN_PASSWORD` in `.env`.
2. Create the local PostgreSQL role/database (once): `CREATE ROLE pradio LOGIN PASSWORD '123123';` then `CREATE DATABASE pradio OWNER pradio;`
3. Create an environment and install: `python -m venv .venv && .venv/bin/pip install -e '.[dev]'`
4. Initialize and generate the native Tortoise migration:
   `tortoise init && tortoise makemigrations --name initial && tortoise migrate`
5. Seed stations: `python -m app.seed`
6. Start: `uvicorn app.main:app --reload`

Open <http://127.0.0.1:8000>. Admin is at `/admin`.

## Storage and licensing

Every provider API response used by a station is upserted into `tracks`, including provider identity, attribution, license URL, and the original response. The station-to-track relationship, pagination cursor, votes, and play counters are persisted too. Global provider track IDs and station relationships are deduplicated, and each station is pruned back to its configured limit. Audius API access is optional for public reads; set `AUDIUS_API_KEY` for higher rate limits.

Audio is deliberately not mirrored locally. Jamendo distinguishes streaming from downloading and artists may disable downloads. A future downloader must use the documented file endpoint only when `download_allowed` is true, preserve license and attribution metadata, remove unavailable works, and be reviewed against the license of each track and Jamendo's current API terms.

This project must remain non-commercial unless separate permission/licensing is obtained from every configured provider. Do not add ads, paid access, sponsorship, or donations without resolving that first.
