# Programming Radio

A small non-commercial programming radio built with FastAPI, Tortoise ORM, HTMX and PostgreSQL. Jamendo and Audius track metadata is cached in PostgreSQL; audio is played directly from its source provider.

**Listen online:** [https://pixelwave.dev/](https://pixelwave.dev/)

## Run locally

1. Create the PostgreSQL role and database once:

   ```sql
   CREATE ROLE pradio LOGIN PASSWORD 'change-me';
   CREATE DATABASE pradio OWNER pradio;
   ```

2. Copy the environment template and set at least `JAMENDO_CLIENT_ID`, `DATABASE_URL`,
   `SECRET_KEY`, and `ADMIN_PASSWORD`. For local HTTP development, set
   `PUBLIC_BASE_URL=http://127.0.0.1:8000` so session cookies are not HTTPS-only.

   ```bash
   cp .env.example .env
   ```

3. Create a Python 3.12+ virtual environment and install the project:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -e '.[dev]'
   ```

4. Apply the committed native Tortoise migrations. Do not run `tortoise init` or create a new
   initial migration during installation.

   ```bash
   .venv/bin/tortoise migrate
   ```

5. Seed the default stations:

   ```bash
   .venv/bin/python -m app.seed
   ```

6. Start the development server:

   ```bash
   .venv/bin/uvicorn app.main:app --reload
   ```

Open <http://127.0.0.1:8000>. Admin is at `/admin`.

## External players

Every public main or user channel exposes a shuffled M3U playlist at
`/channels/<slug>.m3u`. Audio URLs point directly to Jamendo or Audius; Pixelwave does not proxy
or rebroadcast the audio. For example:

```bash
mpv --shuffle --loop-playlist=inf https://pixelwave.dev/channels/night-protocol.m3u
```

The playlist includes artist/title attribution and source and license comments. Hidden channels
and Favorites do not expose M3U endpoints. Web-only features such as voting and personalized
dislike filtering are not available in external players.

## Telegram login

Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, and
`PUBLIC_BASE_URL` in `.env`. Telegram requires the webhook URL to be publicly reachable over
HTTPS, so webhook login cannot point directly to the local development server. After deploying,
register or update the webhook once:

```bash
.venv/bin/python -m app.telegram
```

The bot responds to private messages with a reusable login link that expires after one hour.
Public community channels are listed at `/user-channels`. Logged-in users manage their profile,
Favorites, and public or hidden channels at `/profile`. User channels sync only when created or
edited and cache at most 250 tracks from Jamendo plus 250 from Audius. Public user channels can be
played and rated by anyone; hidden channels are accessible only to their owner.

## Production deployment

1. Install PostgreSQL, Python 3.12+, and a reverse proxy such as Nginx. Check out the project into
   a directory owned by the service account.
2. Create `.env` from `.env.example`. Use strong, unique values for the database password,
   `SECRET_KEY`, `ADMIN_PASSWORD`, and `TELEGRAM_WEBHOOK_SECRET`. Set:

   ```env
   PUBLIC_BASE_URL=https://pixelwave.dev
   ```

3. Install the application and update the database:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -e .
   .venv/bin/tortoise migrate
   .venv/bin/python -m app.seed
   ```

4. Run Uvicorn without `--reload` behind the HTTPS reverse proxy. A systemd unit can look like
   this; replace `/srv/programming-radio` and `pradio` with the actual checkout path and Linux
   service account:

   ```ini
   [Unit]
   Description=Programming Radio
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=pradio
   Group=pradio
   WorkingDirectory=/srv/programming-radio
   EnvironmentFile=/srv/programming-radio/.env
   ExecStart=/srv/programming-radio/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

5. Enable the service, configure the reverse proxy to forward `https://pixelwave.dev` to
   `127.0.0.1:8000`, and then register the Telegram webhook:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now programming-radio
   .venv/bin/python -m app.telegram
   ```

6. Check application logs with:

   ```bash
   journalctl -u programming-radio -f
   ```

## Storage and licensing

Every provider API response used by a station is upserted into `tracks`, including provider identity, attribution, license URL, and the original response. The station-to-track relationship, pagination cursor, votes, and play counters are persisted too. Global provider track IDs and station relationships are deduplicated. The configured track-cache target applies independently to each provider, so the default permits 1,000 Jamendo and 1,000 Audius tracks per station. Audius API access is optional for public reads; set `AUDIUS_API_KEY` for higher rate limits.

Audio is deliberately not mirrored locally. Jamendo distinguishes streaming from downloading and artists may disable downloads. A future downloader must use the documented file endpoint only when `download_allowed` is true, preserve license and attribution metadata, remove unavailable works, and be reviewed against the license of each track and Jamendo's current API terms.

This project must remain non-commercial unless separate permission/licensing is obtained from every configured provider. Do not add ads, paid access, sponsorship, or donations without resolving that first.
