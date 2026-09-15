"""Register (or list/delete) the Calendly webhook subscription that feeds Meetings.

Usage:
    CALENDLY_API_TOKEN=<personal access token> python scripts/register_calendly_webhook.py https://app.yourdomain.com
    CALENDLY_API_TOKEN=... python scripts/register_calendly_webhook.py --list
    CALENDLY_API_TOKEN=... python scripts/register_calendly_webhook.py --delete <subscription uri>

Creates an organization-scoped subscription for invitee.created / invitee.canceled pointing at
<base url>/api/v1/webhooks/calendly and prints the signing key. Calendly shows the signing key
ONLY in this response: put it in backend/.env as CALENDLY_WEBHOOK_SIGNING_KEY.

Personal access token: Calendly -> Integrations -> API & Webhooks -> Personal access tokens.
Webhook subscriptions require a Calendly Standard plan or higher.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.calendly.com"


def _req(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"Calendly API {e.code} on {method} {path}: {e.read().decode()}")


def main(argv: list[str]) -> None:
    token = os.environ.get("CALENDLY_API_TOKEN", "").strip()
    if not token:
        sys.exit("Set CALENDLY_API_TOKEN (Calendly -> Integrations -> API & Webhooks).")
    if not argv:
        sys.exit(__doc__)

    me = _req("GET", "/users/me", token)["resource"]
    org = me["current_organization"]

    if argv[0] == "--list":
        subs = _req("GET", f"/webhook_subscriptions?organization={org}&scope=organization", token)
        for s in subs.get("collection", []):
            print(f"{s['uri']}\n  url={s['callback_url']}\n  events={s['events']}\n  state={s['state']}")
        if not subs.get("collection"):
            print("No organization-scoped subscriptions.")
        return

    if argv[0] == "--delete":
        if len(argv) < 2:
            sys.exit("--delete needs the subscription uri (see --list)")
        uuid = argv[1].rstrip("/").split("/")[-1]
        _req("DELETE", f"/webhook_subscriptions/{uuid}", token)
        print("Deleted.")
        return

    base = argv[0].rstrip("/")
    callback = f"{base}/api/v1/webhooks/calendly"
    created = _req(
        "POST",
        "/webhook_subscriptions",
        token,
        {
            "url": callback,
            "events": ["invitee.created", "invitee.canceled"],
            "organization": org,
            "scope": "organization",
        },
    )["resource"]
    print("Webhook subscription created:")
    print(f"  uri:      {created['uri']}")
    print(f"  callback: {created['callback_url']}")
    print()
    print("Add this to backend/.env and restart the API:")
    print(f"  CALENDLY_WEBHOOK_SIGNING_KEY={created.get('signing_key', '<not returned>')}")


if __name__ == "__main__":
    main(sys.argv[1:])
