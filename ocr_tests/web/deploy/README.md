# Putting the Reading Desk on your own domain

What is here: a container image (`Dockerfile`), a Compose file that runs it behind Caddy (which gets and renews the HTTPS certificate by itself), a settings template (`.env.example`) and a check you can run against the live address (`../tests/smoke_remote.py`).

**What was verified, and what was not.** Verified inside a container built from this Dockerfile (Ubuntu 24.04, Python 3.12, no root, read-only file system, all Linux capabilities dropped): the 37 tests pass, including PDF files through the real poppler and Tesseract; the site starts, passes `smoke_remote.py` and reads the demo; the Caddyfile and the Compose file validate. **Not verified, because it needs your domain and a server: the HTTPS certificate, Caddy and the app together, and your provider's own steps.** `smoke_remote.py` tells you within a minute whether the live site is right.

## Before you start (decisions that are yours)

1. **May client papers go to Google's Gemini service?** Every page picture, and the text read from it, is sent there. Nobody who built this has checked Google's terms for your key's plan, the Advocates Act and Bar Council rules, or the Digital Personal Data Protection Act 2023 and its 2025 Rules. As a lawyer you can judge that; until you have, use only your own test papers. The site's "How your papers are handled" page says what it does; read it as the site's visitors will.
2. **Who gets access.** Each person gets a name and a long random access code. There is no password reset and no sign-up page; adding a person means editing `.env` and restarting.
3. **A key for this site alone**, with a budget alert on the Google account. The site's spending caps use the pipeline's own estimates, which the real bill has exceeded by 1.5 to 2 times.

## 1. A server

Any Linux server will do: Ubuntu 24.04, 2 GB of memory, 20 GB of disk, **in an Indian region** if you can (Mumbai or Bangalore: DigitalOcean, AWS Lightsail, Vultr and Linode all have one). Roughly 6 to 12 US dollars a month [Likely]. Reading is paid separately, to Google.

Install Docker on it (the provider's one-click "Docker" image, or follow https://docs.docker.com/engine/install/ubuntu/). Allow ports 80 and 443 in the provider's firewall and keep 22 for you.

## 2. The domain

At the company where you bought the domain, add a DNS record that points a name at the server: an **A record**, name `desk` (or whatever you like), value the server's IPv4 address. If the DNS service is Cloudflare, switch the orange cloud off for this name (DNS only). Wait until `ping desk.yourdomain.com` shows the server's address.

## 3. The site

On the server:

```
git clone --depth 1 --branch claude/sweet-franklin-wo742p --filter=blob:none --sparse <your repository address> reading-desk
cd reading-desk && git sparse-checkout set ocr_tests      # only the site's files, not the rest of the repository
cd ocr_tests/web/deploy
cp .env.example .env && chmod 600 .env
nano .env                                                  # fill in: RD_DOMAIN, GEMINI_API_KEY, RD_USERS, RD_SITE_NAME, RD_CONTACT
docker compose run --rm app python3 ocr_tests/web/server.py --new-code     # prints a random access code for RD_USERS (run again for each person)
docker compose up -d --build
docker compose logs -f app                                 # Ctrl-C to leave
```

Open `https://desk.yourdomain.com`. The first visit may take a few seconds while the certificate is fetched.

## 4. Check it

From any computer with Python (this one needs nothing installed):

```
python ocr_tests/web/tests/smoke_remote.py https://desk.yourdomain.com YOURNAME YOURCODE
```

It checks the HTTPS redirect and header, that nothing opens without signing in, that a wrong code is refused, that the cookie is `Secure` and `HttpOnly`, and runs the demo end to end (invented pages, no model, no cost; the demo job is deleted). Every line must say `ok`. Then upload one page of your own with the real reader and look at what it costs.

## Running it

- **Update:** `cd reading-desk && git pull && cd ocr_tests/web/deploy && docker compose up -d --build`.
- **Add or remove a person:** edit `.env`, then `docker compose up -d`. Everyone is signed out.
- **Where things are:** papers and usage records live in the Docker volume `deploy_rd_data` (mounted at `/data` in the app); certificates in `deploy_caddy_data`. **Papers are not backed up on purpose**: they are deleted `RD_RETENTION_HOURS` after a job ends. Keep a copy of `.env`; losing the volume only signs people out and resets the spending counters.
- **Spending:** the three limits in `.env` (per job, per person a day, whole site a month) are estimates. Put a budget alert on the Google account too, and look at the Usage page.
- **Watch:** `docker compose ps` (both services up, `app` healthy), `docker compose logs --tail 100 app` (failed sign-ins are logged with the address, never the code), and an uptime monitor on `https://desk.yourdomain.com/healthz` (UptimeRobot's free plan will do).
- **Stop everything:** `docker compose down`. Add `-v` to delete the volumes, and with them every paper.

## Hosting services instead of a server

Render, Railway, Fly.io and similar can build this `Dockerfile` directly (build context: the repository root). They need: the settings from `.env.example` as environment variables, **a persistent disk mounted at `/data`** (without one, the spending counters and sign-ins reset at every restart, which defeats the caps), and your domain attached in their dashboard (they provide the certificate). They set `PORT`; the site listens on it. Not tried.

## What this does not give you

No encryption of the disk (turn on the provider's volume encryption if it offers it), no backup of papers (by design), no audit of who opened what (only who marked a page as read), no password reset, no payments, no second server. The person who runs the server can read papers while they exist; the handling page says so. If the site becomes something clients use, the parts to add first are an audit log, per-person codes you can revoke without a restart, and a written retention and incident policy.
