# Deployment on DigitalOcean

This guide walks you through deploying the **Software House Management System** so that:

- **PostgreSQL** runs on DigitalOcean Managed Database.
- **Backend (FastAPI)** runs on DigitalOcean (App Platform or Droplet).
- **Desktop/Electron** and web clients on other devices connect to your deployed API.

---

## Overview

| Component   | Where it runs              | Purpose |
|------------|----------------------------|---------|
| PostgreSQL | DigitalOcean Managed DB   | Database (data, users, migrations) |
| Backend    | DigitalOcean App Platform or Droplet | REST API (`/api/v1/*`) |
| Frontend   | Your machines (Electron or browser) | UI; points to backend URL via `VITE_API_URL` |

After deployment you will:

1. Build the frontend (or Electron installer) with `VITE_API_URL` set to your backend URL.
2. Install that build on other devices; they will all use the same backend and database.

---

## Prerequisites

- A [DigitalOcean](https://www.digitalocean.com/) account.
- This repo (or a copy) connected to GitHub/GitLab if you use App Platform.
- A domain (optional) for a friendly API URL and HTTPS.

---

## Part 1: PostgreSQL on DigitalOcean

### 1.1 Create a Managed Database

1. In DigitalOcean: **Databases** → **Create Database Cluster**.
2. Choose **PostgreSQL** (recommended: PostgreSQL 15 or 16).
3. Select a region close to where you will run the backend (e.g. same as your App/Droplet).
4. Choose a plan (e.g. **Basic** with 1 node to start).
5. Set a **cluster name** (e.g. `office-software-db`).
6. Create the cluster and wait until it is **Online**.

### 1.2 Get the connection string

1. Open your database cluster → **Connection Details**.
2. Use the **Connection string** (URI) or note:
   - **Host**
   - **Port** (usually `25060` for managed DB; TLS required)
   - **Database** (default `defaultdb` or create one)
   - **User** (default `doadmin`)
   - **Password** (from the cluster creation or reset in the UI)

**Connection string format:**

```text
postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

Example (replace with your values):

```text
postgresql://doadmin:yourpassword@db-postgresql-xxx-xxx.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

### 1.3 Create a dedicated database (optional)

The default database is often `defaultdb`. To use a dedicated DB:

1. In the cluster, open **Users & Databases**.
2. Add a database, e.g. `office_software`.
3. Use it in the connection string: `.../office_software?sslmode=require`.

### 1.4 Allow the backend to connect

- **Trusted Sources**: In the database cluster, under **Settings** → **Trusted Sources**, add:
  - Your **App Platform** outbound IPs (or “All” if you use App Platform and it’s in the same region), or
  - The **Droplet IP** if you deploy the backend on a Droplet.

Keep the database private (no 0.0.0.0/0) in production if possible.

---

## Part 2: Backend on DigitalOcean

You can run the backend either on **App Platform** (simplest) or on a **Droplet**.

---

### Option A: App Platform (recommended)

App Platform runs the app from your repo and manages HTTPS and scaling.

#### A.1 Prepare the repo

The backend includes a **Procfile** so App Platform knows how to start the app:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

App Platform sets `PORT`; the Procfile is in the **backend** directory (see **A.3**).

#### A.2 Create the App

1. **Apps** → **Create App**.
2. Connect your **GitHub/GitLab** and select this repository.
3. Choose the branch to deploy (e.g. `main`).

#### A.3 Configure the component

1. **Resource Type**: Web Service.
2. **Source**:
   - **Repository** and **Branch**: your repo and branch.
   - **Build Command** (run from repo root, then backend):
     ```bash
     cd backend && pip install -r requirements.txt
     ```
   - **Run Command** (if you don’t use a Procfile):
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Source Directory**: leave empty (root), or if you want to set **Root Directory** to `backend`, then:
     - Build: `pip install -r requirements.txt`
     - Run: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

   If the **Root Directory** is set to `backend`, put the **Procfile** in the repo at `backend/Procfile` with:
   ```text
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   and use **Procfile** as the run type if the UI offers it.

3. **Environment Variables** (required):

   | Name           | Value / notes |
  |----------------|----------------|
   | `DATABASE_URL` | Your PostgreSQL URI from Part 1 (with `?sslmode=require`). |
   | `JWT_SECRET`   | A long random string (e.g. 32+ chars). Generate with `openssl rand -hex 32`. |
   | `CORS_ORIGINS` | Allowed origins. For Electron + web: `https://your-frontend-domain.com,app://.` or `*` for testing only. |
   | `DEBUG`        | `false` in production. |

   Optional:

   | Name                | Value |
   |---------------------|--------|
   | `APP_VERSION`       | e.g. `0.0.1` (for `/api/v1/version`). |
   | `SUPER_ADMIN_EMAIL` | One user email with full access and no activity/audit logs (ghost/god-mode). Leave empty to disable. |

4. Save and deploy. Note the **Live URL** (e.g. `https://your-app-xxxxx.ondigitalocean.app`).

#### A.4 Run migrations and seed

App Platform does not run migrations automatically. Use a **one-off job** or **console**:

1. **One-off job** (recommended):
   - Add a **Job** component to the same app.
   - **Source**: same repo, **Root Directory**: `backend`.
   - **Run Command**:
     ```bash
     pip install -r requirements.txt && alembic upgrade head && python scripts/seed_db.py
     ```
   - **Environment**: same as the web service (`DATABASE_URL`, etc.).
   - Run the job once after first deploy (and after any migration change).

2. Or use **Console** (if available) in the web service, with the same env:
   ```bash
   alembic upgrade head
   python scripts/seed_db.py
   ```

Default admin after seed: **admin@example.com** / **admin123**. Change the password after first login.

---

### Option B: Droplet (VPS)

You get a Linux server and run the backend yourself.

#### B.1 Create a Droplet

1. **Droplets** → **Create Droplet**.
2. Image: **Ubuntu 22.04**.
3. Plan: Basic, size as needed (e.g. 1 GB RAM).
4. Add SSH key; create the Droplet.

#### B.2 SSH and install dependencies

```bash
ssh root@YOUR_DROPLET_IP
```

```bash
apt update && apt install -y python3 python3-pip python3-venv git
```

#### B.3 Clone and set up the backend

```bash
cd /opt
git clone https://github.com/YOUR_ORG/office-software.git
cd office-software/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### B.4 Environment file

```bash
nano .env
```

Contents (replace with your values):

```env
DATABASE_URL=postgresql://doadmin:PASSWORD@db-xxx.db.ondigitalocean.com:25060/defaultdb?sslmode=require
JWT_SECRET=your-long-random-secret-from-openssl-rand-hex-32
CORS_ORIGINS=*
DEBUG=false
APP_VERSION=0.0.1
```

#### B.5 Run migrations and seed

```bash
source .venv/bin/activate
alembic upgrade head
python scripts/seed_db.py
```

#### B.6 Run with Gunicorn (production)

```bash
pip install gunicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

Use a process manager (systemd) so it restarts on reboot. Example unit `/etc/systemd/system/office-backend.service`:

```ini
[Unit]
Description=Office Software API
After=network.target

[Service]
User=root
WorkingDirectory=/opt/office-software/backend
Environment="PATH=/opt/office-software/backend/.venv/bin"
ExecStart=/opt/office-software/backend/.venv/bin/gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable office-backend
systemctl start office-backend
```

#### B.7 HTTPS (Nginx + Let’s Encrypt)

Install Nginx and Certbot, then proxy to `http://127.0.0.1:8000` and terminate SSL. Your API URL will be `https://api.yourdomain.com` (or the Droplet IP if you don’t use a domain).

---

## Part 3: Connect clients (other devices)

All clients (browser or Electron) must call your **deployed backend URL**.

### 3.1 Backend URL

- **App Platform**: `https://your-app-xxxxx.ondigitalocean.app` (or your custom domain).
- **Droplet**: `https://api.yourdomain.com` or `http://YOUR_DROPLET_IP:8000` (HTTP only if no SSL).

No trailing slash. Example: `https://api.mycompany.com`.

### 3.2 Web frontend (browser)

Build with the API URL:

```bash
cd frontend
VITE_API_URL=https://your-backend-url.com npm run build
```

Serve the `dist/` folder with any static host (e.g. DigitalOcean Spaces + CDN, Netlify, or Nginx on the same Droplet). Users open the site in the browser; the app will use `VITE_API_URL` baked into the build.

### 3.3 Electron desktop (install on other devices)

1. Set the API URL when building the installer:
   ```bash
   cd frontend
   VITE_API_URL=https://your-backend-url.com npm run electron:build
   ```
2. Installers are in `frontend/dist/` (e.g. `.exe` on Windows).
3. Copy the installer to other laptops and run it. Those devices will use your deployed backend and PostgreSQL.

### 3.4 CORS

Backend must allow the origins clients use:

- **Web**: `https://your-frontend-domain.com`
- **Electron**: `app://.` (common for Electron)

Set in backend env:

```env
CORS_ORIGINS=https://your-frontend-domain.com,app://.
```

For quick testing you can use `*`; restrict origins in production.

---

## Part 4: Checklist and security

- [ ] PostgreSQL: connection string uses `?sslmode=require`; trusted sources limited to backend only.
- [ ] Backend: `JWT_SECRET` is strong and unique; never commit it.
- [ ] Backend: `DEBUG=false` in production.
- [ ] Backend: `CORS_ORIGINS` set to real frontend origins (no `*` in production if possible).
- [ ] Migrations: run `alembic upgrade head` after each deploy that includes migration files.
- [ ] Admin user: seed run once (`python scripts/seed_db.py`); change default password after first login.
- [ ] HTTPS: use HTTPS for the backend URL in production (App Platform provides it; on Droplet use Nginx + Certbot).

---

## Part 5: Updating the deployment

1. **Code changes**: Push to the connected branch; App Platform will redeploy. On a Droplet, `git pull` in `/opt/office-software`, then restart the service.
2. **New migrations**: Run `alembic upgrade head` (via one-off job on App Platform or SSH on Droplet).
3. **Env changes**: Update environment variables in App Platform or in `.env` on the Droplet and restart.
4. **Desktop clients**: Rebuild the Electron app with the same `VITE_API_URL`, bump version, and redistribute the new installer so users can “check for updates” and install the new build (see main README / update flow).

---

## Quick reference: environment variables

| Variable       | Required | Description |
|----------------|----------|-------------|
| `DATABASE_URL`| Yes      | PostgreSQL URI with `?sslmode=require` for Managed DB. |
| `JWT_SECRET`  | Yes      | Secret for signing JWTs (e.g. `openssl rand -hex 32`). |
| `CORS_ORIGINS`| Yes      | Comma-separated origins (e.g. `https://app.example.com,app://.`). |
| `DEBUG`             | No       | `false` in production. |
| `APP_VERSION`       | No       | Returned by `GET /api/v1/version` for update checks. |
| `SUPER_ADMIN_EMAIL` | No       | One user email with full access and no activity logs (ghost user). Empty = disabled. |

---

For local development and run instructions, see the main [README](../README.md).
