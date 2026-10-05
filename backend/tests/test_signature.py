"""Saved signature image: upload, normalise, serve, remove; placed on agreements when sending and on letters."""
import io
import uuid

from PIL import Image, ImageDraw

from tests.test_portal import _make_client_record


def _png(transparent: bool) -> bytes:
    img = Image.new("RGBA" if transparent else "RGB", (400, 120), (0, 0, 0, 0) if transparent else (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.line([(20, 90), (120, 20), (200, 100), (380, 30)], fill=(10, 20, 60, 255) if transparent else (10, 20, 60), width=6)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _upload(client, headers, data: bytes, name="sig.png", ctype="image/png"):
    return client.post("/api/v1/auth/me/signature", headers=headers, files={"file": (name, data, ctype)})


def test_upload_serve_and_remove(client, auth_headers):
    r = _upload(client, auth_headers, _png(transparent=True))
    assert r.status_code == 200, r.text
    assert r.json()["has_signature"] is True
    assert client.get("/api/v1/auth/me", headers=auth_headers).json()["has_signature"] is True

    r = client.get("/api/v1/auth/me/signature", headers=auth_headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/png")
    img = Image.open(io.BytesIO(r.content))
    assert img.mode == "RGBA"

    assert client.delete("/api/v1/auth/me/signature", headers=auth_headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=auth_headers).json()["has_signature"] is False
    assert client.get("/api/v1/auth/me/signature", headers=auth_headers).status_code == 404


def test_white_background_is_knocked_out(client, auth_headers):
    r = _upload(client, auth_headers, _png(transparent=False), name="scan.png")
    assert r.status_code == 200, r.text
    img = Image.open(io.BytesIO(client.get("/api/v1/auth/me/signature", headers=auth_headers).content))
    alpha = img.getchannel("A")
    assert alpha.getextrema()[0] == 0  # some pixels fully transparent (the paper)
    assert alpha.getextrema()[1] == 255  # the strokes stay opaque
    client.delete("/api/v1/auth/me/signature", headers=auth_headers)


def test_rejects_non_images_and_blank(client, auth_headers):
    assert _upload(client, auth_headers, b"%PDF-1.4 not an image", name="x.pdf", ctype="application/pdf").status_code == 400
    assert _upload(client, auth_headers, b"garbage", name="x.png").status_code == 400
    blank = Image.new("RGB", (300, 100), (255, 255, 255))
    out = io.BytesIO()
    blank.save(out, format="PNG")
    assert _upload(client, auth_headers, out.getvalue()).status_code == 400


def test_agreement_is_presigned_on_send_and_pdf_renders(client, auth_headers):
    assert _upload(client, auth_headers, _png(transparent=True)).status_code == 200
    cid = _make_client_record(client, auth_headers, email="p@example.com")
    tpl = client.get("/api/v1/agreements/template?agreement_type=nda", headers=auth_headers).json()
    a = client.post("/api/v1/agreements", headers=auth_headers, json={"title": "NDA " + uuid.uuid4().hex[:5], "client_id": cid, "agreement_type": "nda", "clauses": tpl["clauses"]}).json()

    # Default: sign for the company with the saved signature when sending
    r = client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    assert r.json()["countersigned_at"] and r.json()["countersigned_by_name"]
    assert client.get(f"/api/v1/agreements/{a['id']}/pdf", headers=auth_headers).content[:5] == b"%PDF-"
    token = r.json()["sign_url"].rsplit("/", 1)[1]
    assert client.get(f"/api/v1/public/agreements/{token}/pdf").status_code == 200

    # Client signs: still works, record keeps the company signature, countersign is now refused (already signed)
    r = client.post(f"/api/v1/public/agreements/{token}/accept", json={"signer_name": "Jane Doe", "agreed": True})
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/agreements/{a['id']}/countersign", headers=auth_headers, json={}).status_code == 400
    assert client.get(f"/api/v1/agreements/{a['id']}/pdf", headers=auth_headers).content[:5] == b"%PDF-"

    # Opt out: sign_for_company false leaves it for a later countersign
    b = client.post("/api/v1/agreements", headers=auth_headers, json={"title": "NDA2 " + uuid.uuid4().hex[:5], "client_id": cid, "agreement_type": "nda", "clauses": tpl["clauses"]}).json()
    r = client.post(f"/api/v1/agreements/{b['id']}/send", headers=auth_headers, json={"sign_for_company": False})
    assert r.status_code == 200 and r.json()["countersigned_at"] is None
    client.delete("/api/v1/auth/me/signature", headers=auth_headers)


def test_letter_pdf_with_signature(client, auth_headers):
    assert _upload(client, auth_headers, _png(transparent=True)).status_code == 200
    r = client.post("/api/v1/letters", headers=auth_headers, json={
        "letter_type": "general", "subject": "Test letter", "body": "Dear Sir,\n\nHello.\n\nSincerely,",
        "recipient_name": "Someone", "signatory_name": "Ahmad Shahzad", "signatory_title": "Director",
    })
    assert r.status_code == 201, r.text
    pdf = client.get(f"/api/v1/letters/{r.json()['id']}/pdf", headers=auth_headers)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    client.delete("/api/v1/auth/me/signature", headers=auth_headers)
