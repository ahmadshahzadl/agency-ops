"""Branded HTML shell for every outgoing email.

Email clients are not browsers: Outlook renders with Word, Gmail strips <style> blocks. So
everything here is tables, inline styles, web-safe fonts and absolute https URLs. No flexbox,
no grid, no SVG (neither Outlook nor Gmail will render one), no external CSS.

Matches the template the Fuorix website uses, so a client who gets an invoice from the app and
an enquiry reply from the website sees the same company.

Self-hosters: set EMAIL_LOGO_URL to a PNG of your own logo, or leave it empty for a clean
text-only header built from APP_NAME.
"""
from html import escape

from app.config import get_settings

BRAND = "#001639"
BRAND_ACCENT = "#3d6a9e"
BRAND_TINT = "#eaf0f8"
TEXT = "#374151"
MUTED = "#6b7280"
FAINT = "#9ca3af"
LINE = "#e5e7eb"
SURFACE = "#f0f4f9"

FONT = "'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif"


def brand_name() -> str:
    return get_settings().app_name.replace(" API", "").strip() or "Fuorix"


def _header() -> str:
    """Logo mark plus wordmark on white, over a brand rule. Falls back to the wordmark alone."""
    s = get_settings()
    logo = (s.email_logo_url or "").strip()
    name = escape(brand_name())
    mark = (
        f'<td style="vertical-align:middle;padding-right:11px;">'
        f'<img src="{escape(logo, quote=True)}" width="30" height="30" alt="" '
        f'style="display:block;width:30px;height:30px;border:0;"></td>'
        if logo
        else ""
    )
    return f"""
          <tr>
            <td style="padding:26px 34px 22px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>{mark}
                  <td style="vertical-align:middle;font-family:{FONT};font-size:17px;font-weight:700;letter-spacing:0.09em;color:{BRAND};">{name.upper()}</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr><td style="height:3px;background:{BRAND};font-size:0;line-height:0;">&nbsp;</td></tr>"""


def _footer() -> str:
    s = get_settings()
    details = (s.company_details or "").strip()
    extra = f"<br>{escape(details)}" if details else ""
    return f"""
          <tr>
            <td style="padding:0 34px 28px;">
              <div style="border-top:1px solid {LINE};padding-top:18px;font-family:{FONT};font-size:12px;line-height:1.6;color:{FAINT};">
                {escape(brand_name())}{extra}
                <br>This is an automated message &mdash; replies to it are not monitored.
              </div>
            </td>
          </tr>"""


def button(label: str, url: str) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0 26px;">
      <tr>
        <td style="background:{BRAND};border-radius:6px;">
          <a href="{escape(url, quote=True)}" style="display:inline-block;padding:13px 30px;font-family:{FONT};font-size:14px;font-weight:600;letter-spacing:0.03em;color:#ffffff;text-decoration:none;">{escape(label)}</a>
        </td>
      </tr>
    </table>"""


def rows_table(rows: list[tuple[str, str]]) -> str:
    """Label/value table for invoices, letters and bookings. Values are pre-escaped HTML."""
    if not rows:
        return ""
    cells = []
    for i, (label, value) in enumerate(rows):
        border = f"border-top:1px solid {LINE};" if i else ""
        cells.append(
            f'<tr>'
            f'<td style="padding:11px 0;{border}width:150px;vertical-align:top;font-family:{FONT};'
            f'font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:{FAINT};">{escape(label)}</td>'
            f'<td style="padding:11px 0;{border}font-family:{FONT};font-size:15px;line-height:1.55;color:{TEXT};">{value}</td>'
            f'</tr>'
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="border-collapse:collapse;margin:0 0 24px;">{"".join(cells)}</table>'
    )


def panel(heading: str, body_html: str) -> str:
    """Tinted block for a message, note or description."""
    return (
        f'<div style="background:{SURFACE};border-radius:10px;padding:18px 20px;margin:0 0 24px;">'
        f'<div style="font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{FAINT};margin-bottom:8px;">{escape(heading)}</div>'
        f'<div style="font-family:{FONT};font-size:15px;line-height:1.7;color:{TEXT};">{body_html}</div>'
        f'</div>'
    )


def render(
    title: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    preheader: str | None = None,
    note: str | None = None,
) -> str:
    """The full email. ``body_html`` and ``note`` are inserted as HTML, so escape user input."""
    cta = button(cta_label, cta_url) if cta_label and cta_url else ""
    note_html = (
        f'<p style="margin:0 0 26px;font-family:{FONT};font-size:13px;line-height:1.6;color:{MUTED};">{note}</p>'
        if note
        else ""
    )
    preview = escape(preheader or title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:{SURFACE};">
  <div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{preview}</div>

  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{SURFACE};border-collapse:collapse;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="width:600px;max-width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid {LINE};border-collapse:separate;">
{_header()}
          <tr>
            <td style="padding:32px 34px 8px;">
              <h1 style="margin:0 0 16px;font-family:{FONT};font-size:22px;line-height:1.25;font-weight:700;letter-spacing:-0.02em;color:{BRAND};">{escape(title)}</h1>
              <div style="font-family:{FONT};font-size:15px;line-height:1.7;color:{TEXT};">{body_html}</div>
              {cta}
              {note_html}
            </td>
          </tr>
{_footer()}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# Small helpers callers use when building ``body_html``.

def p(text: str) -> str:
    """An escaped paragraph."""
    return f'<p style="margin:0 0 14px;">{escape(text)}</p>'


def strong(text: str) -> str:
    return f'<strong style="color:{BRAND};">{escape(text)}</strong>'


def link(url: str, label: str | None = None) -> str:
    return f'<a href="{escape(url, quote=True)}" style="color:{BRAND_ACCENT};">{escape(label or url)}</a>'
