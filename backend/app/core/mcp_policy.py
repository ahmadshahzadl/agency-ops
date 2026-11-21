"""What a Claude-connector token may call. Default closed.

Connector access tokens carry the claim ``"via": "mcp"``. ``get_current_user`` refuses them on any
route not listed here, before the route's own permission check runs. So:

- a route added later is unreachable from Claude until someone lists it here;
- the usual RBAC and row-level scoping still apply on top (an allowlisted route is not a grant);
- even a leaked connector token can only do what is listed, never delete, send, sign or reveal.

Keys are (HTTP method, route template) exactly as FastAPI registers them.

Deliberately NOT listed (keep it that way unless the owner decides otherwise):
  * every DELETE
  * sending email: /quotes|letters|agreements|invoices/{id}/send
  * issuing / signing / terminating: letters/{id}/issue, agreements/{id}/countersign|mark-signed|
    terminate|sign-link, quotes/{id}/accept|reject (that is the client's decision)
  * credentials vault (incl. reveal), expenses, payroll, recurring expenses (salaries)
  * invoice and payment writes: POST/PATCH /invoices, /payments, /invoices/from-time, /quotes/{id}/invoice
  * users, roles, teams admin; /auth/* except GET /auth/me; integrations; webhooks; attendance
  * messages (private DMs); website content writes (they publish to the public site)
  * PDFs and attachment downloads (binary, not useful to the model)
"""

P = "/api/v1"

READ: set[tuple[str, str]] = {
    ("GET", f"{P}/auth/me"),
    ("GET", f"{P}/oauth/connector/whoami"),
    # Leads / CRM
    ("GET", f"{P}/leads"),
    ("GET", f"{P}/leads/{{lead_id}}"),
    ("GET", f"{P}/leads/{{lead_id}}/interactions"),
    ("GET", f"{P}/leads/{{lead_id}}/timeline"),
    ("GET", f"{P}/clients"),
    ("GET", f"{P}/clients/{{client_id}}"),
    # Delivery
    ("GET", f"{P}/projects"),
    ("GET", f"{P}/projects/names"),
    ("GET", f"{P}/projects/{{project_id}}"),
    ("GET", f"{P}/projects/{{project_id}}/milestones"),
    ("GET", f"{P}/boards"),
    ("GET", f"{P}/boards/{{board_id}}"),
    ("GET", f"{P}/boards/{{board_id}}/tasks"),
    ("GET", f"{P}/tasks"),
    ("GET", f"{P}/tasks/{{task_id}}"),
    ("GET", f"{P}/notes"),
    ("GET", f"{P}/time-entries"),
    ("GET", f"{P}/time-entries/summary"),
    ("GET", f"{P}/meetings"),
    ("GET", f"{P}/meetings/{{meeting_id}}"),
    # Sales documents
    ("GET", f"{P}/quotes"),
    ("GET", f"{P}/quotes/{{quote_id}}"),
    ("GET", f"{P}/agreements"),
    ("GET", f"{P}/agreements/types"),
    ("GET", f"{P}/agreements/template"),
    ("GET", f"{P}/agreements/{{agreement_id}}"),
    ("GET", f"{P}/letters"),
    ("GET", f"{P}/letters/types"),
    ("GET", f"{P}/letters/template"),
    ("GET", f"{P}/letters/{{letter_id}}"),
    # Invoices and payments: read only (owner decision 2026-11-19)
    ("GET", f"{P}/invoices"),
    ("GET", f"{P}/invoices/{{invoice_id}}"),
    ("GET", f"{P}/invoices/{{invoice_id}}/payments"),
    ("GET", f"{P}/invoices/{{invoice_id}}/time-entries"),
    # Overview
    ("GET", f"{P}/analytics/dashboard"),
    ("GET", f"{P}/analytics/overview"),
    ("GET", f"{P}/team-activity/activity"),
    ("GET", f"{P}/team-activity/my-reports"),
    ("GET", f"{P}/announcements"),
    ("GET", f"{P}/announcements/{{announcement_id}}"),
    ("GET", f"{P}/notifications"),
    ("GET", f"{P}/notifications/unread-count"),
    ("GET", f"{P}/users/assignable"),
    ("GET", f"{P}/teams/my"),
    # Website content: read only
    ("GET", f"{P}/content/posts"),
    ("GET", f"{P}/content/posts/{{post_id}}"),
    ("GET", f"{P}/content/case-studies"),
    ("GET", f"{P}/content/case-studies/{{case_id}}"),
}

WRITE: set[tuple[str, str]] = {
    # Leads
    ("POST", f"{P}/leads"),
    ("PATCH", f"{P}/leads/{{lead_id}}"),
    ("POST", f"{P}/leads/{{lead_id}}/convert"),
    ("POST", f"{P}/leads/{{lead_id}}/interactions"),
    # Quotes (drafts; PATCH cannot change status)
    ("POST", f"{P}/quotes"),
    ("PATCH", f"{P}/quotes/{{quote_id}}"),
    ("POST", f"{P}/quotes/{{quote_id}}/convert"),
    # Projects, milestones, boards, tasks
    ("POST", f"{P}/projects"),
    ("PATCH", f"{P}/projects/{{project_id}}"),
    ("POST", f"{P}/projects/{{project_id}}/milestones"),
    ("PATCH", f"{P}/milestones/{{milestone_id}}"),
    ("POST", f"{P}/milestones/{{milestone_id}}/complete"),
    ("POST", f"{P}/milestones/{{milestone_id}}/reopen"),
    ("POST", f"{P}/boards"),
    ("PATCH", f"{P}/boards/{{board_id}}"),
    ("POST", f"{P}/boards/{{board_id}}/members"),
    ("POST", f"{P}/tasks"),
    ("PATCH", f"{P}/tasks/{{task_id}}"),  # QA gate still enforced by the route
    ("POST", f"{P}/notes"),
    ("POST", f"{P}/time-entries"),
    # Agreements and letters: drafts only (PATCH cannot change status; signed/issued are immutable)
    ("POST", f"{P}/agreements"),
    ("PATCH", f"{P}/agreements/{{agreement_id}}"),
    ("POST", f"{P}/agreements/{{agreement_id}}/duplicate"),
    ("POST", f"{P}/letters"),
    ("PATCH", f"{P}/letters/{{letter_id}}"),
}

ALLOWED: frozenset[tuple[str, str]] = frozenset(READ | WRITE)


def is_allowed(method: str, route_path: str | None) -> bool:
    if not route_path:
        return False
    return (method.upper(), route_path) in ALLOWED
