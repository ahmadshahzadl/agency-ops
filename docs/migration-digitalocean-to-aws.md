# Migrating Fuorix from DigitalOcean to AWS

Moving both `fuorix.com` (Next.js) and `app.fuorix.com` (FastAPI + React portal)
from the DigitalOcean droplet (159.223.44.3, DO region SGP1/Singapore) to a
single AWS EC2 instance (planned: `t3a.small`, `ap-south-1`/Mumbai, using free-tier
credits). Both apps currently share one droplet; this plan keeps them sharing
one EC2 instance the same way.

**Does this affect SEO or AI-discoverability (GEO)?** No, as long as the domain
stays the same and the cutover has effectively zero downtime — which is exactly
what the `/etc/hosts` smoke-test step below is for. Crawlers (Googlebot, GPTBot,
ClaudeBot, PerplexityBot) index by domain and URL, not server IP; nothing about
`llms.txt`, the JSON-LD schema, `robots.txt`, or indexed pages needs to change.
Latency to Pakistan/UAE visitors should improve (Mumbai is ~30-50ms from
Pakistan vs. ~80-100ms from Singapore), which is a mild Core Web Vitals
positive, not a risk. The things that *can* actually hurt you are self-inflicted:
extended downtime, a broken TLS cert right after cutover, or a missed env var
that silently breaks a feature. Every step below exists to prevent one of those three.

---

## 0. Capture the real current config first — don't guess

Before touching AWS, SSH into the **existing** droplet and save the actual
running configuration. Don't rely on `docs/deployment-droplet.md` as ground
truth — it's a template; the live server may have drifted from it.

```bash
ssh root@159.223.44.3

# Save everything that defines how the box actually runs today:
mkdir -p ~/migration-snapshot
cp -r /etc/nginx/sites-available ~/migration-snapshot/nginx-sites-available
cp -r /etc/nginx/sites-enabled ~/migration-snapshot/nginx-sites-enabled
cp /etc/systemd/system/fuorix.service ~/migration-snapshot/ 2>/dev/null
pm2 list > ~/migration-snapshot/pm2-list.txt
pm2 show fuorix > ~/migration-snapshot/pm2-show-fuorix.txt
pm2 ecosystem 2>/dev/null; cat ~/.pm2/dump.pm2 > ~/migration-snapshot/pm2-dump.pm2 2>/dev/null
cp /var/www/fuorix/.env ~/migration-snapshot/fuorix-com.env
cp /opt/fuorix/app/backend/.env ~/migration-snapshot/agency-ops-backend.env
node -v > ~/migration-snapshot/versions.txt
python3 -V >> ~/migration-snapshot/versions.txt
psql --version >> ~/migration-snapshot/versions.txt
nginx -v 2>> ~/migration-snapshot/versions.txt

tar czf ~/migration-snapshot.tar.gz -C ~ migration-snapshot
```

Download it to your machine:
```bash
scp root@159.223.44.3:~/migration-snapshot.tar.gz .
```

This gives you the exact nginx server blocks, the exact env vars (with real
secret values), and the exact process-manager setup — so the new box is a
faithful copy, not a reconstruction from memory.

---

## 1. Launch the AWS EC2 instance

1. AWS Console → EC2 → Launch Instance.
2. **Region**: `ap-south-1` (Mumbai) — already decided, closest to Pakistan/UAE of AWS's options.
3. **AMI**: Ubuntu Server 24.04 LTS (matches what the droplet almost certainly runs).
4. **Instance type**: `t3a.small` (2 vCPU, 2 GB RAM, x86 — avoids any ARM/`t4g` compatibility surprises with native Node/Python packages).
5. **Key pair**: create a new one, download the `.pem`, keep it safe — this is your only SSH access.
6. **Storage**: 20-30 GB gp3 (covers OS + both apps + Postgres + headroom; adjust if your current droplet's `df -h /` from the snapshot shows more in use).
7. **Security group** — open only what's needed:
   - 22 (SSH) — restrict to your IP if possible
   - 80 (HTTP)
   - 443 (HTTPS)
8. Launch, then **allocate and associate an Elastic IP** (EC2 → Elastic IPs → Allocate → Associate with the instance). Without this, a stop/start cycle changes your IP and breaks DNS.

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<ELASTIC_IP>
```

---

## 2. System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git postgresql postgresql-contrib nginx certbot python3-certbot-nginx
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 2 GB RAM is tight for `npm run build` on a 50+ page Next.js app + Postgres
# running at the same time. Add swap as insurance (same guidance as the
# original droplet doc for low-RAM boxes):
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 3. Postgres

```bash
sudo -u postgres psql <<'SQL'
CREATE USER fuorix WITH PASSWORD 'SAME_PASSWORD_AS_OLD_SERVER_OR_NEW';
CREATE DATABASE fuorix OWNER fuorix;
SQL
```
(Use the real password from `agency-ops-backend.env`'s `DATABASE_URL` if you want
a drop-in restore without touching the connection string; otherwise generate a
new one and update the new server's `.env` accordingly.)

---

## 4. Dump and restore the database

**On the old droplet** (dump while it's still live — this is read-only, zero impact on the running app):
```bash
ssh root@159.223.44.3 "sudo -u postgres pg_dump fuorix | gzip" > fuorix-db-dump.sql.gz
```

**Copy to the new server and restore:**
```bash
scp -i your-key.pem fuorix-db-dump.sql.gz ubuntu@<ELASTIC_IP>:~/
ssh -i your-key.pem ubuntu@<ELASTIC_IP>
gunzip -c fuorix-db-dump.sql.gz | sudo -u postgres psql fuorix
```

You'll repeat the dump/restore **one more time right before final DNS cutover**
(step 9) to capture any data written between now and then — bookings, leads,
blog posts published via the CMS, etc.

---

## 5. App user + both codebases

```bash
sudo adduser --system --group --home /opt/fuorix fuorix
sudo mkdir -p /opt/fuorix /var/www
sudo chown fuorix:fuorix /opt/fuorix

# agency-ops (backend + portal frontend)
cd /opt/fuorix
sudo -u fuorix git clone https://github.com/ahmadshahzadl/agency-ops.git app
cd app/backend
sudo -u fuorix python3 -m venv .venv
sudo -u fuorix .venv/bin/pip install -r requirements.txt

# fuorix.com (Next.js)
sudo mkdir -p /var/www/fuorix
sudo chown fuorix:fuorix /var/www/fuorix
sudo -u fuorix git clone https://github.com/Fuorix/fuorix.com.git /var/www/fuorix
cd /var/www/fuorix
sudo -u fuorix npm ci
```

---

## 6. Environment variables

Copy the **exact** `.env` files you pulled in step 0 — don't retype them by
hand, that's how a secret gets a typo.

```bash
scp -i your-key.pem migration-snapshot/agency-ops-backend.env ubuntu@<ELASTIC_IP>:/tmp/
scp -i your-key.pem migration-snapshot/fuorix-com.env ubuntu@<ELASTIC_IP>:/tmp/

ssh -i your-key.pem ubuntu@<ELASTIC_IP>
sudo mv /tmp/agency-ops-backend.env /opt/fuorix/app/backend/.env
sudo mv /tmp/fuorix-com.env /var/www/fuorix/.env
sudo chown fuorix:fuorix /opt/fuorix/app/backend/.env /var/www/fuorix/.env
sudo chmod 600 /opt/fuorix/app/backend/.env /var/www/fuorix/.env
```

Update only what actually needs to change for the new box:
- `DATABASE_URL` — if you used a new Postgres password in step 3
- Nothing else should need to change — `FRONTEND_URL`, `PORTAL_API_URL` (still `http://127.0.0.1:8000`, same-box proxy pattern), `RESEND_API_KEY`, `CAREERS_EMAIL`, `CONTACT_EMAIL`, `NEXT_PUBLIC_GA_ID`, `SITE_REVALIDATE_SECRET`, and the new `TURNSTILE_SITE_KEY`/`TURNSTILE_SECRET_KEY` (if configured) all carry over verbatim, since they're tied to the domain and external services, not the server.

Also copy the uploads directory (portal file attachments):
```bash
ssh root@159.223.44.3 "tar czf - -C /opt/fuorix uploads" > uploads.tar.gz
scp -i your-key.pem uploads.tar.gz ubuntu@<ELASTIC_IP>:~/
ssh -i your-key.pem ubuntu@<ELASTIC_IP>
sudo -u fuorix tar xzf ~/uploads.tar.gz -C /opt/fuorix
```

---

## 7. Migrate and build both apps

```bash
# Backend
cd /opt/fuorix/app/backend
sudo -u fuorix .venv/bin/alembic upgrade head   # should be a no-op if the DB dump is already current

# Portal frontend
cd /opt/fuorix/app/frontend
sudo -u fuorix bash -c 'VITE_API_URL=https://app.fuorix.com npm ci && VITE_API_URL=https://app.fuorix.com npm run build'

# fuorix.com
cd /var/www/fuorix
sudo -u fuorix npm run build
```

---

## 8. Process managers

**FastAPI — systemd** (copy the exact unit file from the snapshot, or recreate it):
```bash
sudo cp ~/migration-snapshot/fuorix.service /etc/systemd/system/fuorix.service
sudo systemctl daemon-reload
sudo systemctl enable --now fuorix
curl -s http://127.0.0.1:8000/health   # expect {"status":"ok"}
```

**Next.js — pm2:**
```bash
cd /var/www/fuorix
sudo -u fuorix pm2 start npm --name fuorix -- start
sudo -u fuorix pm2 save
sudo pm2 startup systemd -u fuorix --hp /opt/fuorix   # follow the printed command to enable on boot
```

---

## 9. nginx + TLS — build it, but don't cut over yet

Recreate the server blocks from `~/migration-snapshot/nginx-sites-available/`
on the new box (adjust only if you changed ports). You need two server blocks:
one for `fuorix.com` (proxy to the Next.js pm2 process, typically port 3000)
and one for `app.fuorix.com` (static `dist/` + `/api/` proxy to `127.0.0.1:8000`,
same pattern as `deployment-droplet.md`).

```bash
sudo nginx -t
sudo systemctl reload nginx
```

For TLS, you can't `certbot --nginx -d fuorix.com` yet — Let's Encrypt validates
by checking that the domain's DNS already points at this server, which it
doesn't until step 11. **Don't skip ahead; this is exactly why step 10 exists.**

---

## 10. Smoke-test the new server before any DNS change

This is the step that makes the whole migration effectively zero-downtime and
zero-SEO-risk: verify everything works on the new box while the live domain
still points at the old droplet, using your own machine's `/etc/hosts` (or
Windows' `C:\Windows\System32\drivers\etc\hosts`) to fake the DNS locally:

```
<ELASTIC_IP>  fuorix.com
<ELASTIC_IP>  app.fuorix.com
```

Then browse `http://fuorix.com` and `http://app.fuorix.com` normally (HTTP
only at this point, since there's no cert yet). Check:
- Homepage, `/careers`, `/contact`, `/blog` all load
- The portal login at `app.fuorix.com` works and shows real migrated data
- Submit a real test contact form inquiry and confirm the email arrives
- `curl -H "Host: fuorix.com" http://localhost/llms.txt` and `/robots.txt` on the server itself return the right content

Remove the `/etc/hosts` entries when done testing.

---

## 11. DNS cutover

**The day before**, lower the TTL on your existing `fuorix.com` and
`app.fuorix.com` A records (e.g., to 300 seconds) in whatever DNS provider you
use (Cloudflare, your registrar, etc.) — this makes the eventual real cutover
propagate in minutes instead of hours.

**On cutover day:**
1. Re-run the Postgres dump/restore from step 4 to capture the last few hours
   of data (bookings, leads, any blog edits).
2. Re-run `npm run build` / `alembic upgrade head` on the new server if anything changed.
3. Update the A records for `fuorix.com` and `app.fuorix.com` to point at the new Elastic IP.
4. Immediately issue TLS certs now that DNS resolves to the new server:
   ```bash
   sudo certbot --nginx -d fuorix.com -d app.fuorix.com
   ```
5. Watch propagation: `dig fuorix.com +short` from a few different networks/online dig tools until it consistently shows the new IP.

---

## 12. Post-cutover verification

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://fuorix.com/
curl -s -o /dev/null -w "%{http_code}\n" https://fuorix.com/llms.txt
curl -s -o /dev/null -w "%{http_code}\n" https://fuorix.com/robots.txt
curl -s -o /dev/null -w "%{http_code}\n" https://app.fuorix.com/health
```
All should be `200`. Also: submit one more real test lead through `/contact`
and confirm it lands in `hello@fuorix.com`, and check Search Console's **URL
Inspection** tool on `fuorix.com` a day later to confirm Google is still
reaching the site cleanly (it will show the same content either way — this is
just a sanity check, not a required action).

---

## 13. Decommission the DigitalOcean droplet

Don't rush this. Keep the old droplet running (but not receiving traffic,
since DNS has moved) for at least a week as a rollback option — if DNS can be
pointed back at it in minutes, you have a safety net for free. After a week of
clean operation on AWS:

```bash
ssh root@159.223.44.3 "sudo -u postgres pg_dump fuorix | gzip" > final-do-backup.sql.gz   # belt and suspenders
```
Then cancel/destroy the droplet from the DigitalOcean dashboard.

---

## Rollback plan (if something breaks after cutover)

Because the Elastic IP and old droplet are both still live during the overlap
window, rollback is just: point the A records back at `159.223.44.3`. TTL is
already low from step 11, so this takes minutes, not hours. This is why you
should **not** decommission the droplet immediately after cutover — it's your
rollback insurance for the first week.
