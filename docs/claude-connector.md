# Claude connector (remote MCP)

Use the ops app from Claude: ask it "what's in the QA queue?", "draft a quote for the Saakht lead",
"create a board for the new project and put these tasks on it". Claude works **as you**, with your
role's access, through the same API the web app uses.

Design and decisions: [mcp-connector-plan.md](mcp-connector-plan.md).

## What it can and cannot do

| Claude can | Claude cannot |
|---|---|
| Read leads, clients, projects, milestones, boards, tasks, notes, quotes, agreements, letters, meetings, hours, dashboard, team activity, announcements, website content, **invoices and payments** (all limited by your role) | Send any email (quotes, letters, agreements, invoices). **People press Send in the app** |
| Create/edit leads, log lead interactions, convert leads | Issue letters, sign/countersign/terminate agreements, accept/reject quotes |
| Draft/edit quotes, convert accepted quotes to projects | Delete anything |
| Create/edit projects, milestones, boards (and members), tasks/bugs, notes, own time entries | Write invoices or payments |
| Draft/edit agreements (template clauses by default) and letters | See the credentials vault, expenses, payroll, private messages |
| | Change users, roles, teams, attendance, integrations, or publish website content |

The source of truth is the allowlist in `backend/app/core/mcp_policy.py`. Connector tokens are
refused (403) on every route not listed there, before the route's own permission check runs, so a
route added later stays closed to Claude until someone adds it. The normal RBAC, team scoping and
QA gate apply on top. `backend/tests/test_connector.py` fails if the allowlist ever contains a
DELETE or a send/issue/sign/credentials/expenses/payroll route.

Every change Claude makes is in the activity log with **"· via Claude"** appended.

## How it fits together

```
claude.ai ──HTTPS──> nginx (app.fuorix.com)
                       /mcp, /.well-known/oauth-protected-resource  -> 127.0.0.1:8001  fuorix-mcp
                       /.well-known/oauth-authorization-server      -> 127.0.0.1:8000  API
                       /api/  (incl. /api/v1/oauth/*)                -> 127.0.0.1:8000  API
                       /oauth/consent                                -> SPA (approve page)
fuorix-mcp ──HTTP──> 127.0.0.1:8000/api/v1   (forwards the user's connector token)
```

- `mcp/server.py` is a thin client with no database access. It has its own venv because `mcp` 2.x
  needs Starlette 1.x and the API's FastAPI pin needs Starlette below 0.47. **Never install `mcp` into
  `backend/.venv`: it upgrades Starlette and the API stops starting.**
- OAuth 2.1 (authorization code + PKCE, dynamic client registration) is served by the API.
  Access tokens last 60 min, refresh tokens 30 days (rotated on every use).
- A connection is cut off by: Settings → Connected apps → Disconnect, **Sign out everywhere**,
  a password change, deactivating the user, removing them from `MCP_ALLOWED_EMAILS`, or
  `MCP_ENABLED=false`. Reconnecting replaces the previous connection.

## One-time server setup (droplet)

1. **Deploy the code** (push to `main`; migration `042` creates `oauth_clients` / `oauth_grants`).

2. **API settings** in `/opt/fuorix/app/backend/.env`, then `systemctl restart fuorix`:

   ```bash
   MCP_ENABLED=true
   MCP_PUBLIC_URL=https://app.fuorix.com
   # Only these accounts may connect. Empty = any active staff account (portal users never).
   MCP_ALLOWED_EMAILS=ahmad.shahzad@fuorix.com
   ```

3. **MCP service**:

   ```bash
   cd /opt/fuorix/app/mcp
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```

   `/etc/systemd/system/fuorix-mcp.service`:

   ```ini
   [Unit]
   Description=Fuorix MCP (Claude connector)
   After=network.target fuorix.service

   [Service]
   User=fuorix
   Group=fuorix
   WorkingDirectory=/opt/fuorix/app/mcp
   Environment=FUORIX_API_URL=http://127.0.0.1:8000
   Environment=MCP_PUBLIC_URL=https://app.fuorix.com
   ExecStart=/opt/fuorix/app/mcp/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --proxy-headers
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   systemctl daemon-reload && systemctl enable --now fuorix-mcp
   ```

   From then on `deploy.yml` updates and restarts it on every push. It skips this step while the
   unit file doesn't exist.

4. **nginx**: add to the `app.fuorix.com` server block, above `location /`:

   ```nginx
   # Claude connector (remote MCP)
   location = /mcp {
       proxy_pass http://127.0.0.1:8001;
       proxy_http_version 1.1;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_buffering off;
       proxy_read_timeout 300s;
   }
   location /.well-known/oauth-protected-resource {
       proxy_pass http://127.0.0.1:8001;
       proxy_set_header Host $host;
   }
   location = /.well-known/oauth-authorization-server {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
   }
   ```

   `/oauth/consent` is a SPA route, so the existing `location /` fallback serves it.
   Then `nginx -t && systemctl reload nginx`.

5. **Check**:

   ```bash
   curl -s https://app.fuorix.com/.well-known/oauth-authorization-server | head -c 200   # JSON
   curl -s https://app.fuorix.com/.well-known/oauth-protected-resource/mcp | head -c 200  # JSON
   curl -si -X POST https://app.fuorix.com/mcp | grep -i www-authenticate                # 401 + resource_metadata
   ```

## Connecting Claude

1. In Claude: **Settings → Connectors → Add custom connector**. Name it `Fuorix` and set the URL to
   `https://app.fuorix.com/mcp` (also shown, with a Copy button, in the app under Settings → Connected apps).
2. Claude opens the Fuorix sign-in. Sign in, read the approve page, then press **Allow**.
3. In a chat, enable the Fuorix connector. Write tools are marked as such, so Claude asks before
   using them unless you change that in the connector's tool settings.

To let more people connect later, add their emails to `MCP_ALLOWED_EMAILS` (comma-separated), or
empty it to allow every active staff account. Each person connects their own Claude with their own
login and gets exactly their role's access.

## Local development

```bash
# API with the connector on
cd backend && MCP_ENABLED=true MCP_PUBLIC_URL=http://127.0.0.1:8001 uvicorn app.main:app --port 8000
# MCP server (separate venv)
cd mcp && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
FUORIX_API_URL=http://127.0.0.1:8000 MCP_PUBLIC_URL=http://127.0.0.1:8001 .venv/Scripts/uvicorn server:app --port 8001
```

Tests: `cd backend && pytest tests/test_connector.py tests/test_money_visibility.py`.
