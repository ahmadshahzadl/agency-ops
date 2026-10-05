"""A saved signature image per user, dropped onto agreements and letters.

Uploads are normalised to a transparent PNG: EXIF rotation applied, size capped, and if the
image has no transparency (a photo or scan of a signature on paper) near-white pixels are
made transparent so the strokes sit cleanly on the page."""
import io
import os
import uuid

from PIL import Image, ImageOps

from app.config import get_settings

SUBDIR = "signatures"
MAX_BYTES = 2 * 1024 * 1024
MAX_WIDTH = 1200
ALLOWED = {"image/png", "image/jpeg", "image/webp"}


class SignatureError(Exception):
    pass


def _dir() -> str:
    d = os.path.join(get_settings().upload_dir, SUBDIR)
    os.makedirs(d, exist_ok=True)
    return d


def path_for(filename: str | None) -> str | None:
    if not filename:
        return None
    p = os.path.join(_dir(), os.path.basename(filename))
    return p if os.path.isfile(p) else None


def normalise(raw: bytes) -> bytes:
    if len(raw) > MAX_BYTES:
        raise SignatureError("The image must be under 2 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise SignatureError("That file is not an image we can read. Use a PNG, JPG or WebP.")
    img = ImageOps.exif_transpose(img)
    had_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA")
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, max(1, round(img.height * MAX_WIDTH / img.width))), Image.LANCZOS)
    if not had_alpha:
        # Knock out the paper: pixels close to white become transparent, with a soft edge.
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                lum = (r + g + b) / 3
                if lum > 235:
                    px[x, y] = (r, g, b, 0)
                elif lum > 200:
                    px[x, y] = (r, g, b, int(255 * (235 - lum) / 35))
    # Trim transparent margins so the signature fills its box on the page
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        raise SignatureError("The image is blank after removing the background")
    img = img.crop(bbox)
    if img.width < 40 or img.height < 10:
        raise SignatureError("The signature is too small or blank after removing the background")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def save(user, raw: bytes, content_type: str | None) -> str:
    if content_type and content_type.split(";")[0].strip() not in ALLOWED:
        raise SignatureError("Upload a PNG, JPG or WebP image")
    data = normalise(raw)
    name = f"{user.id}-{uuid.uuid4().hex[:8]}.png"
    with open(os.path.join(_dir(), name), "wb") as f:
        f.write(data)
    remove(user)
    user.signature_file = name
    return name


def remove(user) -> None:
    p = path_for(user.signature_file)
    if p:
        try:
            os.remove(p)
        except OSError:
            pass
    user.signature_file = None


def signature_path_for_user_id(session, user_id) -> str | None:
    """Resolve a user's signature file from any ORM object's session (used by the PDF builders)."""
    if not user_id or session is None:
        return None
    from app.models import User
    u = session.get(User, user_id)
    return path_for(u.signature_file) if u else None
