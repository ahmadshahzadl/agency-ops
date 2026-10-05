"""Pre-saved clause sets, one per agreement type.

Returned by GET /agreements/template?agreement_type=... as the starting point for a new
agreement; every clause is fully editable there. Each agreement stores its own snapshot, so
changes here never touch existing contracts. Text in [square brackets] is meant to be
replaced in the editor before sending.

Types: nda (mutual NDA, used before a client is accepted), service (project engagement),
retainer (monthly hours), maintenance (support and hosting SLA)."""
from app.config import get_settings

AGREEMENT_TYPES = ("nda", "service", "retainer", "maintenance")

TYPE_LABELS = {
    "nda": "Mutual Non-Disclosure Agreement",
    "service": "Service Agreement",
    "retainer": "Retainer Agreement",
    "maintenance": "Maintenance & Support Agreement",
}

TYPE_SHORT = {
    "nda": "NDA",
    "service": "Service agreement",
    "retainer": "Retainer",
    "maintenance": "Maintenance & support",
}

TYPE_DESCRIPTIONS = {
    "nda": "Sign this first, before scope, pricing or data are shared. Mutual, 12-month disclosure period, 3-year survival.",
    "service": "A fixed-scope engagement: scope, timeline, fees, revisions, IP, warranty and termination.",
    "retainer": "Ongoing work against a monthly block of hours, with rollover, priority and billing rules.",
    "maintenance": "Hosting, updates, backups and support for a delivered product, with response-time targets.",
}

NUMBER_PREFIX = {"nda": "NDA", "service": "AGR", "retainer": "RET", "maintenance": "SLA"}

# Which types carry a money value and which are signed before a client is accepted
HAS_VALUE = {"service", "retainer", "maintenance"}


def _company_name() -> str:
    return get_settings().app_name.replace(" API", "")


def label_for(agreement_type: str | None) -> str:
    return TYPE_LABELS.get(agreement_type or "service", TYPE_LABELS["service"])


def prefix_for(agreement_type: str | None) -> str:
    return NUMBER_PREFIX.get(agreement_type or "service", "AGR")


def title_for(agreement_type: str | None, client_name: str | None) -> str:
    who = client_name or "[Client]"
    return f"{label_for(agreement_type)} - {who}"


def _bullets(lines: list[str] | None, fallback: str) -> str:
    return "\n".join(f"- {s}" for s in lines) if lines else fallback


# ---------------------------------------------------------------------------
# NDA
# ---------------------------------------------------------------------------

def nda_clauses(client_name: str | None = None) -> list[dict]:
    company = _company_name()
    client = client_name or "[Client legal name]"
    return [
        {
            "heading": "Parties",
            "body": f"This Mutual Non-Disclosure Agreement is entered into between {company} of Lahore, Pakistan, "
                    f"and {client} of [Client's city and country] (the \"Client\"), effective as of the effective date "
                    "stated above. Each party may disclose Confidential Information (the \"Disclosing Party\") to the "
                    "other (the \"Receiving Party\"). Together they are the \"Parties\".",
        },
        {
            "heading": "Purpose",
            "body": f"The Parties wish to explore a possible collaboration under which {company} may provide technical, "
                    f"design and development services for [describe the Client's product or project] (the \"Purpose\"). "
                    "Nothing in this Agreement obliges either party to share information, enter a further agreement or "
                    "proceed with an engagement. Any future engagement, including scope, fees and ownership of work "
                    "product, will be set out in a separate written agreement.",
        },
        {
            "heading": "Confidential Information",
            "body": "\"Confidential Information\" means all non-public information disclosed by or on behalf of a "
                    "Disclosing Party, in any form and whether or not marked confidential, that a reasonable person "
                    "would understand to be confidential. For the Client this includes its business plans, methodology, "
                    "algorithms, data, customer and investor information, roadmap, processes and pricing. For "
                    f"{company} it includes its proposals, pricing, technical approaches, architecture, source code, "
                    "tools and know-how. Information is excluded if it is public through no breach of this Agreement, "
                    "was lawfully known to the Receiving Party before disclosure, is lawfully received from a third "
                    "party without restriction, or is independently developed without use of the Confidential Information.",
        },
        {
            "heading": "Obligations of the Receiving Party",
            "body": "The Receiving Party will: use Confidential Information only for the Purpose; keep it confidential "
                    "with at least reasonable care; disclose it only to personnel who need to know it and are bound by "
                    "equivalent written confidentiality duties, remaining responsible for them; and not copy it beyond "
                    "what the Purpose reasonably requires. The Receiving Party will not reverse engineer or attempt to "
                    "infer the Disclosing Party's methodology or source material from any outputs, samples, test results "
                    "or interfaces, and will not use them to build or train a competing product, methodology or model. "
                    "The Receiving Party will not enter the Disclosing Party's Confidential Information into any "
                    "third-party AI or machine-learning service unless that service cannot retain or train on the data "
                    "and the Disclosing Party has approved it in writing. The Receiving Party will notify the Disclosing "
                    "Party within 48 hours of becoming aware of any unauthorised access, use or disclosure.",
        },
        {
            "heading": "Compelled Disclosure",
            "body": "If the Receiving Party is legally required to disclose Confidential Information, it will, where "
                    "lawful, give prompt written notice so the Disclosing Party can seek protection, disclose only what "
                    "is legally required, and cooperate with reasonable efforts to protect the information.",
        },
        {
            "heading": "Ownership & No Licence",
            "body": "All Confidential Information remains the property of the Disclosing Party, and no licence or right "
                    "is granted except to use it for the Purpose. The Client retains all rights in its own materials "
                    f"and data. {company} retains all rights in its pre-existing tools, code libraries and know-how. "
                    "Ownership of any work product in a future engagement will be set out in a separate written agreement.",
        },
        {
            "heading": "Data Protection & Deletion",
            "body": "The Parties will not share Personal Data unless necessary for the Purpose, and will use anonymised "
                    "or dummy data wherever possible. Any data shared will be limited to the minimum necessary, "
                    "protected with access controls and encryption in transit and at rest, and accessible only to named "
                    "individuals with a need to know. Data will be deleted on request and on termination as set out in "
                    "the Return & Deletion clause. Each party will comply with the data protection laws that apply to it.",
        },
        {
            "heading": "Term & Survival",
            "body": "The Parties may exchange Confidential Information for 12 months from the effective date (the "
                    "\"Disclosure Period\"), unless ended earlier by written notice from either party. The Receiving "
                    "Party's obligations continue for three (3) years after the end of the Disclosure Period. For trade "
                    "secrets and for Personal Data, they continue for as long as the information remains a trade secret "
                    "or Personal Data under applicable law.",
        },
        {
            "heading": "Return & Deletion",
            "body": "On written request or when the Disclosure Period ends, the Receiving Party will within 14 days "
                    "return or securely delete all Confidential Information, including copies, notes and derivatives, "
                    "and confirm this in writing. Copies may be kept only where required by law or in inaccessible "
                    "routine backups, which remain subject to this Agreement while held.",
        },
        {
            "heading": "Non-Solicitation & Remedies",
            "body": "During the Disclosure Period and for 12 months afterwards, neither party will directly solicit for "
                    "employment or engagement any employee or contractor of the other who was involved in the Purpose, "
                    "other than through general advertisements. Each party acknowledges that unauthorised use or "
                    "disclosure may cause irreparable harm for which damages alone are inadequate, and the Disclosing "
                    "Party may seek injunctive or other equitable relief in addition to any other remedy.",
        },
        {
            "heading": "General & Governing Law",
            "body": "This Agreement is the entire agreement between the parties on its subject matter and supersedes "
                    "prior informal understandings, and can only be changed in writing signed by both parties. Neither "
                    "party may assign it without the other's written consent. If a provision is unenforceable, the rest "
                    "remains in effect. Confidential Information is provided without warranty. This Agreement is governed "
                    "by the laws of Pakistan [or: the laws of the Client's jurisdiction, as agreed]. Disputes will first "
                    "be negotiated in good faith, then submitted to the courts of that jurisdiction. Acceptance may be "
                    "given electronically, and an electronic acceptance recorded through a signing link or the client "
                    "portal, together with the signer's name, email, time and network address, has the same effect as "
                    "a handwritten signature.",
        },
    ]


# ---------------------------------------------------------------------------
# Service agreement (the original minimal set)
# ---------------------------------------------------------------------------

def default_clauses(
    client_name: str | None = None,
    scope_lines: list[str] | None = None,
    payment_summary: str | None = None,
    timeline_lines: list[str] | None = None,
) -> list[dict]:
    company = _company_name()
    client = client_name or "the Client"
    scope = _bullets(scope_lines, "Describe the services and deliverables here (features, pages, integrations, support...).")
    timeline = _bullets(timeline_lines, "Deliverables and target dates as agreed in writing between the parties.")
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
                    "least reasonable care. Where the parties have signed a separate Non-Disclosure Agreement, "
                    "that agreement continues to apply. This obligation survives the end of this Agreement.",
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
                    "electronic acceptance recorded through a signing link or the client portal has the same "
                    "effect as a handwritten signature.",
        },
    ]


# ---------------------------------------------------------------------------
# Retainer
# ---------------------------------------------------------------------------

def retainer_clauses(client_name: str | None = None) -> list[dict]:
    company = _company_name()
    client = client_name or "the Client"
    return [
        {
            "heading": "Parties & Term",
            "body": f"This Retainer Agreement is entered into between {company} (the \"Provider\") and {client} "
                    "(the \"Client\"), effective as of the effective date stated above. It runs month to month "
                    "until either party ends it with 30 days' written notice.",
        },
        {
            "heading": "Monthly Allocation",
            "body": "The Provider reserves [number] hours per calendar month for the Client's work across design, "
                    "development, maintenance and consulting, scheduled by agreement. Unused hours roll over for one "
                    "month only and then lapse. Hours beyond the allocation are billed at [rate] per hour, agreed in "
                    "writing before they are worked.",
        },
        {
            "heading": "How Work Is Requested",
            "body": "The Client raises requests in writing (email, portal or board). The Provider confirms an estimate "
                    "in hours before starting anything expected to take more than [4] hours. Retainer work is "
                    "prioritised ahead of non-retainer clients and started within [2] working days of confirmation.",
        },
        {
            "heading": "Fees & Payment",
            "body": "The monthly retainer fee is the contract value stated above, invoiced on the first working day of "
                    "each month and payable within 7 days. Work pauses if an invoice is more than 14 days overdue. "
                    "All fees are exclusive of applicable taxes.",
        },
        {
            "heading": "Reporting",
            "body": "The Provider sends a monthly summary of hours used, work completed and hours remaining. Time is "
                    "tracked in 15-minute increments and is available to the Client on request.",
        },
        {
            "heading": "Intellectual Property",
            "body": "Deliverables produced under this retainer are assigned to the Client on payment of the month in "
                    "which they were produced. The Provider retains ownership of pre-existing tools, libraries and "
                    "know-how, and grants the Client a perpetual licence to use them as embedded in the deliverables.",
        },
        {
            "heading": "Confidentiality",
            "body": "Each party will keep the other's non-public information confidential, use it only for this "
                    "engagement and protect it with at least reasonable care. Where the parties have signed a separate "
                    "Non-Disclosure Agreement, that agreement continues to apply.",
        },
        {
            "heading": "Liability",
            "body": "The Provider will fix defects in its own work at no charge when reported within 30 days. Neither "
                    "party is liable for indirect or consequential damages; each party's total liability under this "
                    "Agreement is limited to the fees paid in the three months before the claim.",
        },
        {
            "heading": "General",
            "body": "This Agreement is the entire agreement between the parties on its subject and can only be changed "
                    "in writing signed by both parties. It is governed by the laws of the Provider's place of business. "
                    "Acceptance may be given electronically; an electronic acceptance recorded through a signing link "
                    "or the client portal has the same effect as a handwritten signature.",
        },
    ]


# ---------------------------------------------------------------------------
# Maintenance & support
# ---------------------------------------------------------------------------

def maintenance_clauses(client_name: str | None = None) -> list[dict]:
    company = _company_name()
    client = client_name or "the Client"
    return [
        {
            "heading": "Parties & Covered System",
            "body": f"This Maintenance & Support Agreement is entered into between {company} (the \"Provider\") and "
                    f"{client} (the \"Client\") for the system described as [name and URL of the website or "
                    "application] (the \"System\"), effective as of the effective date stated above.",
        },
        {
            "heading": "What Is Included",
            "body": "- Hosting and infrastructure management on [provider/region]\n"
                    "- Security patches and dependency updates applied within 7 days of release, critical fixes within 48 hours\n"
                    "- Daily backups retained for 30 days, with a quarterly restore test\n"
                    "- Uptime monitoring with alerting, and a monthly performance check\n"
                    "- Up to [number] hours per month of small changes, content updates and bug fixes\n\n"
                    "Work beyond this scope (new features, redesigns, integrations) is quoted separately.",
        },
        {
            "heading": "Support Hours & Response Times",
            "body": "Support is available Monday to Friday, 09:00 to 18:00 Pakistan time, by email and the client portal. "
                    "Target response and resolution times by severity: Critical (site down, data loss): response "
                    "within 2 hours, work begins immediately. High (major function broken): response within 4 hours, "
                    "fix within 2 working days. Normal (minor issue or change): response within 1 working day, "
                    "scheduled within 5 working days. Out-of-hours work for critical issues is included; other "
                    "out-of-hours requests are billed at [rate] per hour.",
        },
        {
            "heading": "Fees & Payment",
            "body": "The monthly fee is the contract value stated above, invoiced monthly in advance and payable within "
                    "7 days. Third-party costs (hosting, domains, licences, email sending) are passed through at cost "
                    "unless stated as included. Fees are reviewed annually with 30 days' notice. All fees are "
                    "exclusive of applicable taxes.",
        },
        {
            "heading": "Client Responsibilities",
            "body": "The Client provides timely access, credentials and content, keeps its own accounts (domain, "
                    "payment, third-party services) in good standing, and reports issues through the agreed channels. "
                    "Changes made by the Client or third parties outside this Agreement are supported on a best-effort, "
                    "billable basis.",
        },
        {
            "heading": "Availability",
            "body": "The Provider targets 99.5% monthly availability for the System, excluding scheduled maintenance "
                    "announced at least 24 hours in advance and outages caused by third-party providers or the Client. "
                    "If availability falls below the target in a month, the Client receives a credit of 5% of that "
                    "month's fee for each full percentage point below target, capped at 25%.",
        },
        {
            "heading": "Term & Termination",
            "body": "This Agreement runs for an initial [12]-month term and then month to month. Either party may end "
                    "it with 30 days' written notice after the initial term. On termination the Provider hands over "
                    "all credentials, code, data and backups within 14 days and assists with migration at the hourly rate.",
        },
        {
            "heading": "Confidentiality & Data",
            "body": "Each party keeps the other's non-public information confidential. The Provider processes the "
                    "Client's data only to deliver the services, keeps it within the agreed hosting region, and "
                    "deletes its copies within 30 days of termination except where retention is required by law.",
        },
        {
            "heading": "Liability",
            "body": "Neither party is liable for indirect or consequential damages. The Provider's total liability "
                    "under this Agreement is limited to the fees paid in the twelve months before the claim.",
        },
        {
            "heading": "General",
            "body": "This Agreement is the entire agreement between the parties on its subject and can only be changed "
                    "in writing signed by both parties. It is governed by the laws of the Provider's place of business. "
                    "Acceptance may be given electronically; an electronic acceptance recorded through a signing link "
                    "or the client portal has the same effect as a handwritten signature.",
        },
    ]


def clauses_for(
    agreement_type: str | None,
    client_name: str | None = None,
    scope_lines: list[str] | None = None,
    payment_summary: str | None = None,
    timeline_lines: list[str] | None = None,
) -> list[dict]:
    t = agreement_type or "service"
    if t == "nda":
        return nda_clauses(client_name)
    if t == "retainer":
        return retainer_clauses(client_name)
    if t == "maintenance":
        return maintenance_clauses(client_name)
    return default_clauses(client_name, scope_lines, payment_summary, timeline_lines)


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
