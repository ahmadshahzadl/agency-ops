"""The built-in minimal service-agreement clause set.

Returned by GET /agreements/template as the starting point for a new
agreement; every clause is fully editable there. Each agreement stores
its own snapshot, so changes here never touch existing contracts."""
from decimal import Decimal
from app.config import get_settings


def _company_name() -> str:
    return get_settings().app_name.replace(" API", "")


def default_clauses(
    client_name: str | None = None,
    scope_lines: list[str] | None = None,
    payment_summary: str | None = None,
    timeline_lines: list[str] | None = None,
) -> list[dict]:
    company = _company_name()
    client = client_name or "the Client"
    scope = "\n".join(f"- {s}" for s in scope_lines) if scope_lines else (
        "Describe the services and deliverables here (features, pages, integrations, support...)."
    )
    timeline = "\n".join(f"- {t}" for t in timeline_lines) if timeline_lines else (
        "Deliverables and target dates as agreed in writing between the parties."
    )
    payment = payment_summary or (
        "Fees and payment schedule as stated in the referenced proposal/invoice. "
        "Invoices are payable within 14 days of issue."
    )
    return [
        {
            "heading": "Parties",
            "body": f"This Service Agreement is entered into between {company} (the \"Provider\") "
                    f"and {client} (the \"Client\"), effective as of the effective date stated above.",
        },
        {
            "heading": "Scope of Services",
            "body": f"The Provider will perform the following services for the Client:\n{scope}\n\n"
                    "Work outside this scope will be agreed separately in writing before it begins.",
        },
        {
            "heading": "Timeline & Deliverables",
            "body": f"{timeline}\n\nDates depend on the Client providing timely feedback, content, "
                    "and access; delays on the Client's side extend the timeline accordingly.",
        },
        {
            "heading": "Fees & Payment",
            "body": f"{payment}\n\nLate payments may pause work and accrue reasonable late charges. "
                    "All fees are exclusive of applicable taxes.",
        },
        {
            "heading": "Revisions & Acceptance",
            "body": "Each deliverable includes up to two rounds of reasonable revisions. A deliverable "
                    "is deemed accepted when the Client approves it in writing or uses it in production, "
                    "or if no written objections are raised within 7 days of delivery.",
        },
        {
            "heading": "Intellectual Property",
            "body": "Upon receipt of full payment, all deliverables created specifically for the Client "
                    "under this Agreement are assigned to the Client. The Provider retains ownership of "
                    "pre-existing tools, libraries, and know-how, and grants the Client a perpetual "
                    "license to use them as embedded in the deliverables.",
        },
        {
            "heading": "Confidentiality",
            "body": "Each party will keep the other party's non-public business, technical, and financial "
                    "information confidential, use it only for this engagement, and protect it with at "
                    "least reasonable care. This obligation survives the end of this Agreement.",
        },
        {
            "heading": "Warranties & Liability",
            "body": "The Provider warrants services will be performed in a professional and workmanlike "
                    "manner and will fix defects reported within 30 days of delivery at no charge. "
                    "Neither party is liable for indirect or consequential damages; each party's total "
                    "liability under this Agreement is limited to the fees actually paid under it.",
        },
        {
            "heading": "Termination",
            "body": "Either party may terminate with 14 days' written notice. On termination the Client "
                    "pays for all work performed up to the termination date, and the Provider hands over "
                    "work-in-progress covered by those payments.",
        },
        {
            "heading": "General",
            "body": "This Agreement is the entire agreement between the parties on its subject and can "
                    "only be changed in writing signed by both parties. It is governed by the laws of "
                    "the Provider's place of business. Acceptance may be given electronically; an "
                    "electronic acceptance recorded through the client portal has the same effect as a "
                    "handwritten signature.",
        },
    ]


def scope_from_quote(quote) -> tuple[list[str], str]:
    """Scope bullet list + payment summary derived from a quote's items."""
    lines = [
        f"{i.description} (qty {i.quantity} x {i.unit_price} {quote.currency})"
        for i in quote.items
    ]
    payment = (
        f"Total fee of {quote.total} {quote.currency} as quoted in proposal {quote.number}. "
        "Invoices are payable within 14 days of issue."
    )
    return lines, payment


def timeline_from_milestones(milestones) -> list[str]:
    return [
        f"{m.name}" + (f" - due {m.due_date}" if m.due_date else "")
        for m in milestones
    ]
