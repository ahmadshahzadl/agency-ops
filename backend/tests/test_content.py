"""Website CMS: posts, case studies, media, public read API, permissions, revalidate hook."""
import io
import uuid

import pytest

from app.services import content_service as cs

ADMIN = "/api/v1/content"
PUB = "/api/v1/public/content"

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0300050001"
    "27c8d0a20000000049454e44ae426082"
)


@pytest.fixture
def revalidations(monkeypatch):
    calls: list[tuple[list, list]] = []
    monkeypatch.setattr(cs, "revalidate_site", lambda paths, tags: calls.append((paths, tags)))
    return calls


def _slug(prefix="t"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_requires_content_permission(client, employee_headers):
    assert client.get(f"{ADMIN}/posts", headers=employee_headers).status_code == 403
    assert client.get(f"{ADMIN}/posts").status_code == 401


def test_post_lifecycle_draft_publish_public(client, auth_headers, revalidations):
    slug = _slug("post")
    body = "## Heading\n\n" + " ".join(["word"] * 440) + "\n\n![alt](/blog/x/01.webp)"
    r = client.post(f"{ADMIN}/posts", headers=auth_headers, json={"slug": slug, "title": "Draft post", "excerpt": "Ex", "category": "Web", "body_md": body})
    assert r.status_code == 201, r.text
    post = r.json()
    assert post["status"] == "draft" and post["read_time"] == "2 min read" and post["word_count"] == 441
    assert revalidations == []  # drafts don't touch the site

    # Drafts are invisible publicly
    assert client.get(f"{PUB}/posts/{slug}").status_code == 404
    assert slug not in {p["slug"] for p in client.get(f"{PUB}/posts", params={"limit": 200}).json()["items"]}

    # Publish
    r = client.patch(f"{ADMIN}/posts/{post['id']}", headers=auth_headers, json={"status": "published"})
    assert r.status_code == 200 and r.json()["published_at"]
    assert revalidations and f"/blog/{slug}" in revalidations[-1][0] and "blog" in revalidations[-1][1]
    pub = client.get(f"{PUB}/posts/{slug}").json()
    assert pub["title"] == "Draft post" and pub["body_md"].startswith("## Heading") and pub["read_time"] == "2 min read"
    assert "id" not in pub  # public shape is slug-based
    assert slug in {p["slug"] for p in client.get(f"{PUB}/posts", params={"limit": 200}).json()["items"]}

    # Slug conflict + rename revalidates the old path too
    dup = client.post(f"{ADMIN}/posts", headers=auth_headers, json={"slug": slug, "title": "Dup"})
    assert dup.status_code == 409
    new_slug = _slug("post")
    client.patch(f"{ADMIN}/posts/{post['id']}", headers=auth_headers, json={"slug": new_slug})
    assert f"/blog/{slug}" in revalidations[-1][0] and f"/blog/{new_slug}" in revalidations[-1][0]

    # Delete
    assert client.delete(f"{ADMIN}/posts/{post['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"{PUB}/posts/{new_slug}").status_code == 404


def test_related_posts_resolve_only_published(client, auth_headers, revalidations):
    a, b = _slug("a"), _slug("b")
    pb = client.post(f"{ADMIN}/posts", headers=auth_headers, json={"slug": b, "title": "B", "status": "draft"}).json()
    r = client.post(f"{ADMIN}/posts", headers=auth_headers, json={"slug": a, "title": "A", "status": "published", "related_slugs": [b, "missing"]})
    assert r.status_code == 201
    try:
        pub = client.get(f"{PUB}/posts/{a}").json()
        assert b not in {x["slug"] for x in pub["related"]}  # draft related post is hidden; falls back to recent posts
    finally:
        client.delete(f"{ADMIN}/posts/{r.json()['id']}", headers=auth_headers)
        client.delete(f"{ADMIN}/posts/{pb['id']}", headers=auth_headers)


def test_case_study_lifecycle(client, auth_headers, revalidations):
    slug = _slug("case")
    r = client.post(
        f"{ADMIN}/case-studies", headers=auth_headers,
        json={"slug": slug, "title": "Acme.", "tagline": "Line", "category": "Fintech", "tags": ["SaaS", " ", "AI"], "year": "2026",
              "results": [{"label": "Users", "value": "1,000+"}], "highlights": ["Fast"], "stack": ["Next.js"], "featured": True, "status": "published"},
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["tags"] == ["SaaS", "AI"] and c["results"][0]["value"] == "1,000+"
    assert f"/portfolio/{slug}" in revalidations[-1][0]
    pub = client.get(f"{PUB}/case-studies/{slug}").json()
    assert pub["featured"] is True and pub["stack"] == ["Next.js"]
    assert slug in {x["slug"] for x in client.get(f"{PUB}/case-studies").json()}
    client.patch(f"{ADMIN}/case-studies/{c['id']}", headers=auth_headers, json={"status": "draft"})
    assert client.get(f"{PUB}/case-studies/{slug}").status_code == 404
    assert client.delete(f"{ADMIN}/case-studies/{c['id']}", headers=auth_headers).status_code == 204


def test_media_upload_and_public_serve(client, auth_headers):
    r = client.post(f"{ADMIN}/media", headers=auth_headers, files={"file": ("pixel.png", io.BytesIO(PNG_1PX), "image/png")}, data={"alt": "A pixel"})
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["url"].startswith("/cms/media/") and m["url"].endswith(".png") and m["alt"] == "A pixel"
    name = m["url"].rsplit("/", 1)[-1]
    served = client.get(f"{PUB}/media/{name}")
    assert served.status_code == 200 and served.headers["content-type"].startswith("image/png") and served.content == PNG_1PX
    assert "immutable" in served.headers.get("cache-control", "")
    assert client.get(f"{PUB}/media/{m['id']}").status_code == 200  # extension optional
    bad = client.post(f"{ADMIN}/media", headers=auth_headers, files={"file": ("x.svg", io.BytesIO(b"<svg/>"), "image/svg+xml")})
    assert bad.status_code == 400
    assert any(x["id"] == m["id"] for x in client.get(f"{ADMIN}/media", headers=auth_headers).json())
    assert client.delete(f"{ADMIN}/media/{m['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"{PUB}/media/{name}").status_code == 404


def test_read_time_helpers():
    assert cs.read_time("") == "1 min read"
    assert cs.read_time(" ".join(["w"] * 660)) == "3 min read"
    assert cs.slugify("Hello, World! 2026") == "hello-world-2026"
