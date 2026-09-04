# Deploying Fuorix on a DigitalOcean droplet (alongside an existing site)

Target: one droplet already running nginx for another site (e.g. company
portfolio). Fuorix gets its own subdomain, its own Postgres database on
localhost, a systemd service for the API, and nginx serves the built
frontend. Nothing about the existing site is touched except adding one
nginx server block.

Replace throughout: `app.example.com` (your Fuorix domain), `YOURDOMAIN`.

---

## 0. DNS first

Create an **A record**: `app.example.com -> <droplet IP>`.
If you use Cloudflare, set it to **DNS only (grey cloud)** until TLS is
issued in step 7, then you may enable the proxy (orange cloud).

## 1. Inspect the box

```bash
ssh root@<droplet-ip>
lsb_release -a          # expect Ubuntu 22.04/24.04
free -h                 # RAM; if 1GB total, add swap (below)
df -h /                 # disk
nginx -v                # confirm nginx serves the existing site
sudo ufw status         # note existing firewall rules
```

**If RAM is 1GB**, add swap so the frontend build and Postgres coexist:

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 2. System packages

```bash
apt update
apt install -y python3 python3-venv python3-pip git postgresql postgresql-contrib nginx certbot python3-certbot-nginx
# Node 20 for building the frontend:
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
```

## 3. Postgres (localhost only — the default)

```bash
sudo -u postgres psql <<'SQL'
CREATE USER fuorix WITH PASSWORD 'CHANGE_ME_DB_PASSWORD';
CREATE DATABASE fuorix OWNER fuorix;
SQL
```

Postgres listens on localhost by default; leave it that way.

## 4. App user + code

```bash
adduser --system --group --home /opt/fuorix fuorix
cd /opt/fuorix
sudo -u fuorix git clone https://github.com/ahmadshahzadl/agency-ops.git app
cd app/backend
sudo -u fuorix python3 -m venv .venv
sudo -u fuorix .venv/bin/pip install -r requirements.txt
```

## 5. Environment

```bash
sudo -u fuorix cp .env.example .env
sudo -u fuorix nano .env
```

Required values:

```env
DATABASE_URL=postgresql://fuorix:CHANGE_ME_DB_PASSWORD@localhost:5432/fuorix
JWT_SECRET=<output of: openssl rand -hex 32>
CORS_ORIGINS=https://app.example.com,app://.
DEBUG=false
FRONTEND_URL=https://app.example.com
UPLOAD_DIR=/opt/fuorix/uploads
ADMIN_EMAIL=you@yourdomain.com
ADMIN_PASSWORD=<strong password for first login>
# SMTP_* + COMPANY_DETAILS when ready (email + PDF footer)
```

```bash
mkdir -p /opt/fuorix/uploads && chown fuorix:fuorix /opt/fuorix/uploads
chmod 600 /opt/fuorix/app/backend/.env
```

Migrate and seed:

```bash
cd /opt/fuorix/app/backend
sudo -u fuorix .venv/bin/alembic upgrade head
sudo -u fuorix .venv/bin/python scripts/seed_db.py
```

## 6. systemd service (single worker — required by the in-memory websockets)

`/etc/systemd/system/fuorix.service`:

```ini
[Unit]
Description=Fuorix API
After=network.target postgresql.service

[Service]
User=fuorix
Group=fuorix
WorkingDirectory=/opt/fuorix/app/backend
ExecStart=/opt/fuorix/app/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now fuorix
curl -s http://127.0.0.1:8000/health   # {"status":"ok"}
```

## 7. Frontend build

The API URL is baked in at build time:

```bash
cd /opt/fuorix/app/frontend
sudo -u fuorix bash -c 'VITE_API_URL=https://app.example.com npm ci && VITE_API_URL=https://app.example.com npm run build'
```

Output lands in `/opt/fuorix/app/frontend/dist`.

## 8. Nginx + TLS

`/etc/nginx/sites-available/fuorix`:

```nginx
server {
    listen 80;
    server_name app.example.com;

    root /opt/fuorix/app/frontend/dist;
    index index.html;
    client_max_body_size 20M;

    # Don't log query strings (websocket auth tokens travel there)
    access_log /var/log/nginx/fuorix.access.log combined;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/fuorix /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d app.example.com     # issues TLS, sets up renewal
ufw allow 'Nginx Full'                 # if ufw is active
```

## 9. Backups (non-negotiable)

`/opt/fuorix/backup.sh`:

```bash
#!/bin/bash
set -e
STAMP=$(date +%F)
DIR=/opt/fuorix/backups
mkdir -p "$DIR"
sudo -u postgres pg_dump fuorix | gzip > "$DIR/db-$STAMP.sql.gz"
tar czf "$DIR/uploads-$STAMP.tar.gz" -C /opt/fuorix uploads
find "$DIR" -mtime +14 -delete
```

```bash
chmod +x /opt/fuorix/backup.sh
crontab -e   # add:
# 30 2 * * * /opt/fuorix/backup.sh
```

Strongly recommended additionally: enable DigitalOcean droplet **Backups**
in the control panel (~20% of droplet cost), and/or rclone the backup dir
to object storage. A backup that lives only on the same disk is half a backup.

## 10. First login

Open `https://app.example.com`, sign in with `ADMIN_EMAIL` /
`ADMIN_PASSWORD`, change the password in Profile, then create your team
users and roles (qa for QA, client role + client link for portal users).

## Updating a deployment

```bash
cd /opt/fuorix/app
sudo -u fuorix git pull
cd backend
sudo -u fuorix .venv/bin/pip install -r requirements.txt
sudo -u fuorix .venv/bin/alembic upgrade head
cd ../frontend
sudo -u fuorix bash -c 'VITE_API_URL=https://app.example.com npm ci && VITE_API_URL=https://app.example.com npm run build'
systemctl restart fuorix
```

## Migrating to another server later (e.g. office mini PC)

All state lives in three places:

1. Postgres: `pg_dump fuorix` on the old box, `psql fuorix < dump.sql` on the new
2. `/opt/fuorix/uploads/` — copy the directory
3. `backend/.env` — copy (same `JWT_SECRET` keeps sessions valid)

Run the same steps 2-9 on the new machine, restore the three items,
flip the DNS A record. Done.
