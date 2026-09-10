"""Starting-point body text for each letter type. Placeholders in
[square brackets] are meant to be replaced in the editor; the recipient
name is filled in when known."""
from app.config import get_settings

LETTER_TYPES = ("general", "offer_letter", "experience_letter", "noc", "completion_certificate")

TYPE_LABELS = {
    "general": "General letter",
    "offer_letter": "Offer letter",
    "experience_letter": "Experience letter",
    "noc": "No Objection Certificate",
    "completion_certificate": "Project completion certificate",
}


def _company() -> str:
    return get_settings().app_name.replace(" API", "")


def template_for(letter_type: str, recipient_name: str | None = None) -> dict:
    company = _company()
    who = recipient_name or "[Recipient name]"
    subjects = {
        "general": "",
        "offer_letter": f"Offer of Employment - [Position]",
        "experience_letter": "Experience Letter",
        "noc": "No Objection Certificate",
        "completion_certificate": "Certificate of Project Completion",
    }
    bodies = {
        "general": (
            f"Dear {who},\n\n"
            "[Write your letter here.]\n\n"
            "Sincerely,"
        ),
        "offer_letter": (
            f"Dear {who},\n\n"
            f"We are pleased to offer you the position of [Position] at {company}, starting on "
            "[Start date]. Your monthly compensation will be [Salary], subject to applicable "
            "taxes and deductions.\n\n"
            "Your employment will be governed by the company's policies as shared with you, "
            "including a probation period of [3 months]. During your employment you will be "
            "expected to devote your working time to the company and to keep its business and "
            "client information confidential.\n\n"
            "Please confirm your acceptance of this offer by signing and returning a copy of "
            "this letter by [Reply-by date]. We look forward to having you on the team.\n\n"
            "Sincerely,"
        ),
        "experience_letter": (
            "TO WHOM IT MAY CONCERN\n\n"
            f"This is to certify that {who} was employed with {company} as [Position] from "
            "[Start date] to [End date].\n\n"
            "During their tenure, they carried out their responsibilities with diligence and "
            "professionalism, and their conduct was found to be excellent. Key responsibilities "
            "included [main responsibilities].\n\n"
            "We wish them every success in their future endeavours.\n\n"
            "This letter is issued upon request and carries no financial or legal obligation "
            f"on {company}."
        ),
        "noc": (
            "TO WHOM IT MAY CONCERN\n\n"
            f"This is to certify that {company} has no objection to {who} "
            "[purpose - e.g. pursuing part-time studies / travelling to ... / joining ... ].\n\n"
            "This certificate is issued upon request of the concerned person for "
            "[intended use], and does not constitute any commitment or liability on the part "
            f"of {company}.\n\n"
            "For any verification, please contact us through the details below."
        ),
        "completion_certificate": (
            "TO WHOM IT MAY CONCERN\n\n"
            f"This is to certify that {company} has successfully completed the project "
            f"[Project name] for {who}, delivered on [Delivery date].\n\n"
            "The scope of the engagement included [brief scope summary]. All agreed "
            "deliverables have been completed and handed over, and the engagement stands "
            "concluded to the client's satisfaction.\n\n"
            "We thank them for the opportunity and look forward to working together again."
        ),
    }
    return {
        "letter_type": letter_type,
        "subject": subjects.get(letter_type, ""),
        "body": bodies.get(letter_type, bodies["general"]),
    }
