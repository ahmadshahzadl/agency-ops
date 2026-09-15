import { useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import {
  listPosts, createPost, updatePost, deletePost,
  listCaseStudies, createCaseStudy, updateCaseStudy, deleteCaseStudy,
  listMedia, uploadMedia, deleteMedia, mediaSrc,
  type BlogPost, type BlogPostInput, type CaseStudy, type CaseStudyInput, type Media,
} from "@/api/content";
import { useModal } from "@/contexts/ModalContext";

const SITE = ((import.meta.env.VITE_BOOKING_PUBLIC_URL as string | undefined) || "").replace(/\/$/, "");
const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
const labelClass = "block text-xs font-semibold text-gray-600 mb-1";

function slugify(s: string): string {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 160);
}
function lines(v: string): string[] {
  return v.split("\n").map((x) => x.trim()).filter(Boolean);
}
function fmtDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "—";
}
function StatusBadge({ status }: { status: string }) {
  return status === "published" ? (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">Published</span>
  ) : (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">Draft</span>
  );
}

const emptyPost = (): Partial<BlogPostInput> => ({
  slug: "", title: "", excerpt: "", category: "", body_md: "", cover_url: "", cover_alt: "", related_slugs: [], seo_title: "", seo_description: "", author_name: "Fuorix", status: "draft", published_at: null,
});
const emptyCase = (): Partial<CaseStudyInput> => ({
  slug: "", title: "", tagline: "", category: "", tags: [], year: String(new Date().getFullYear()), overview: "", challenge: "", solution: "", highlights: [], results: [], stack: [], related_slugs: [], image_url: "", logo_url: "", gradient: "", featured: false, sort_order: 0, seo_title: "", seo_description: "", status: "draft", published_at: null,
});

export default function ContentPage() {
  const { showConfirm, showAlert } = useModal();
  const [tab, setTab] = useState<"posts" | "cases" | "media">("posts");
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [cases, setCases] = useState<CaseStudy[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const [postModal, setPostModal] = useState<"new" | BlogPost | null>(null);
  const [post, setPost] = useState<Partial<BlogPostInput>>(emptyPost());
  const [caseModal, setCaseModal] = useState<"new" | CaseStudy | null>(null);
  const [cs, setCs] = useState<Partial<CaseStudyInput>>(emptyCase());
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);
  const [slugTouched, setSlugTouched] = useState(false);
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadTarget = useRef<"body" | "cover" | "cs-image" | "cs-logo" | "library">("body");

  const load = () => {
    setLoading(true);
    Promise.all([listPosts().catch(() => []), listCaseStudies().catch(() => []), listMedia().catch(() => [])])
      .then(([p, c, m]) => { setPosts(p); setCases(c); setMedia(m); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  // ---------- posts ----------
  const openNewPost = () => { setPost(emptyPost()); setSlugTouched(false); setPreview(false); setPostModal("new"); };
  const openPost = (p: BlogPost) => {
    setPost({ slug: p.slug, title: p.title, excerpt: p.excerpt ?? "", category: p.category ?? "", body_md: p.body_md, cover_url: p.cover_url ?? "", cover_alt: p.cover_alt ?? "", related_slugs: p.related_slugs ?? [], seo_title: p.seo_title ?? "", seo_description: p.seo_description ?? "", author_name: p.author_name ?? "", status: p.status, published_at: p.published_at });
    setSlugTouched(true); setPreview(false); setPostModal(p);
  };
  const savePost = async (statusOverride?: "draft" | "published") => {
    if (!post.title?.trim()) return showAlert({ title: "Missing title", message: "Give the post a title." });
    setSaving(true);
    try {
      const payload: Partial<BlogPostInput> = {
        ...post,
        slug: post.slug || slugify(post.title || ""),
        status: statusOverride ?? (post.status as "draft" | "published"),
        excerpt: post.excerpt || null, category: post.category || null, cover_url: post.cover_url || null, cover_alt: post.cover_alt || null,
        seo_title: post.seo_title || null, seo_description: post.seo_description || null, author_name: post.author_name || null,
        published_at: post.published_at || null,
      };
      const saved = postModal === "new" ? await createPost(payload) : await updatePost((postModal as BlogPost).id, payload);
      setPostModal(saved);
      setPost((f) => ({ ...f, status: saved.status, published_at: saved.published_at, slug: saved.slug }));
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    } finally {
      setSaving(false);
    }
  };
  const removePost = (p: BlogPost) => showConfirm({
    title: "Delete post", message: `Delete "${p.title}"? The page disappears from the website.`, confirmLabel: "Delete", variant: "danger",
    onConfirm: async () => { await deletePost(p.id); setPostModal(null); load(); },
  });

  // ---------- case studies ----------
  const openNewCase = () => { setCs(emptyCase()); setSlugTouched(false); setCaseModal("new"); };
  const openCase = (c: CaseStudy) => {
    setCs({ slug: c.slug, title: c.title, tagline: c.tagline ?? "", category: c.category ?? "", tags: c.tags, year: c.year ?? "", overview: c.overview ?? "", challenge: c.challenge ?? "", solution: c.solution ?? "", highlights: c.highlights, results: c.results, stack: c.stack, related_slugs: c.related_slugs, image_url: c.image_url ?? "", logo_url: c.logo_url ?? "", gradient: c.gradient ?? "", featured: c.featured, sort_order: c.sort_order, seo_title: c.seo_title ?? "", seo_description: c.seo_description ?? "", status: c.status, published_at: c.published_at });
    setSlugTouched(true); setCaseModal(c);
  };
  const saveCase = async (statusOverride?: "draft" | "published") => {
    if (!cs.title?.trim()) return showAlert({ title: "Missing title", message: "Give the case study a title." });
    setSaving(true);
    try {
      const payload: Partial<CaseStudyInput> = {
        ...cs,
        slug: cs.slug || slugify(cs.title || ""),
        status: statusOverride ?? (cs.status as "draft" | "published"),
        results: (cs.results ?? []).filter((r) => r.label.trim() && r.value.trim()),
        tagline: cs.tagline || null, category: cs.category || null, year: cs.year || null, overview: cs.overview || null, challenge: cs.challenge || null, solution: cs.solution || null,
        image_url: cs.image_url || null, logo_url: cs.logo_url || null, gradient: cs.gradient || null, seo_title: cs.seo_title || null, seo_description: cs.seo_description || null,
        published_at: cs.published_at || null,
      };
      const saved = caseModal === "new" ? await createCaseStudy(payload) : await updateCaseStudy((caseModal as CaseStudy).id, payload);
      setCaseModal(saved);
      setCs((f) => ({ ...f, status: saved.status, published_at: saved.published_at, slug: saved.slug }));
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    } finally {
      setSaving(false);
    }
  };
  const removeCase = (c: CaseStudy) => showConfirm({
    title: "Delete case study", message: `Delete "${c.title}"?`, confirmLabel: "Delete", variant: "danger",
    onConfirm: async () => { await deleteCaseStudy(c.id); setCaseModal(null); load(); },
  });

  // ---------- media ----------
  const pickFile = (target: typeof uploadTarget.current) => { uploadTarget.current = target; fileRef.current?.click(); };
  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const m = await uploadMedia(file, file.name.replace(/\.[a-z0-9]+$/i, "").replace(/[-_]+/g, " "));
      const t = uploadTarget.current;
      if (t === "body") insertAtCursor(`\n\n![${m.alt || ""}](${m.url})\n\n`);
      else if (t === "cover") setPost((f) => ({ ...f, cover_url: m.url, cover_alt: f.cover_alt || m.alt || "" }));
      else if (t === "cs-image") setCs((f) => ({ ...f, image_url: m.url }));
      else if (t === "cs-logo") setCs((f) => ({ ...f, logo_url: m.url }));
      setMedia((list) => [m, ...list]);
    } catch (err: unknown) {
      showAlert({ title: "Upload failed", message: err instanceof Error ? err.message : "Failed" });
    }
  };
  const insertAtCursor = (text: string) => {
    const el = bodyRef.current;
    const body = post.body_md ?? "";
    if (!el) return setPost((f) => ({ ...f, body_md: body + text }));
    const start = el.selectionStart ?? body.length;
    const end = el.selectionEnd ?? body.length;
    const next = body.slice(0, start) + text + body.slice(end);
    setPost((f) => ({ ...f, body_md: next }));
    requestAnimationFrame(() => { el.focus(); el.selectionStart = el.selectionEnd = start + text.length; });
  };
  const wrapSelection = (before: string, after = "") => {
    const el = bodyRef.current;
    const body = post.body_md ?? "";
    if (!el) return;
    const start = el.selectionStart, end = el.selectionEnd;
    const sel = body.slice(start, end) || "text";
    const next = body.slice(0, start) + before + sel + after + body.slice(end);
    setPost((f) => ({ ...f, body_md: next }));
    requestAnimationFrame(() => { el.focus(); el.selectionStart = start + before.length; el.selectionEnd = start + before.length + sel.length; });
  };
  const removeMedia = (m: Media) => showConfirm({
    title: "Delete image", message: `Delete ${m.filename}? Any post still using it will show a broken image.`, confirmLabel: "Delete", variant: "danger",
    onConfirm: async () => { await deleteMedia(m.id); setMedia((l) => l.filter((x) => x.id !== m.id)); },
  });

  const previewHtml = useMemo(() => {
    if (!preview) return "";
    const md = (post.body_md ?? "").replace(/\]\(\/cms\/media\//g, `](${mediaSrc("/cms/media/")}`);
    return marked.parse(md, { async: false }) as string;
  }, [preview, post.body_md]);

  const ql = q.trim().toLowerCase();
  const filteredPosts = ql ? posts.filter((p) => `${p.title} ${p.slug} ${p.category ?? ""}`.toLowerCase().includes(ql)) : posts;
  const filteredCases = ql ? cases.filter((c) => `${c.title} ${c.slug} ${c.category ?? ""}`.toLowerCase().includes(ql)) : cases;

  const tabBtn = (key: typeof tab, label: string, count: number) => (
    <button type="button" onClick={() => setTab(key)} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${tab === key ? "bg-primary text-white" : "text-gray-600 hover:bg-gray-100"}`}>
      {label} <span className={`ml-1 text-xs ${tab === key ? "text-white/70" : "text-gray-400"}`}>{count}</span>
    </button>
  );

  return (
    <div className="space-y-4">
      <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif,image/avif" className="hidden" onChange={onFile} />
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1 flex-wrap">
          {tabBtn("posts", "Blog posts", posts.length)}
          {tabBtn("cases", "Case studies", cases.length)}
          {tabBtn("media", "Images", media.length)}
          <input type="search" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} className="ml-2 px-3 py-1.5 rounded-lg border border-gray-300 text-sm bg-white min-w-[180px]" />
        </div>
        {tab === "posts" && <button onClick={openNewPost} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">New post</button>}
        {tab === "cases" && <button onClick={openNewCase} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">New case study</button>}
        {tab === "media" && <button onClick={() => pickFile("library")} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Upload image</button>}
      </div>

      {loading ? <p className="text-gray-500">Loading...</p> : tab === "posts" ? (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600"><tr>
              <th className="px-4 py-3">Title</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Category</th><th className="px-4 py-3">Published</th><th className="px-4 py-3">Length</th><th className="px-4 py-3 w-40 text-right">Actions</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {filteredPosts.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3"><div className="font-medium text-gray-900">{p.title}</div><div className="text-xs text-gray-500">/blog/{p.slug}</div></td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-gray-600">{p.category || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{fmtDate(p.published_at)}</td>
                  <td className="px-4 py-3 text-gray-600">{p.read_time}</td>
                  <td className="px-4 py-3 text-right"><div className="flex items-center justify-end gap-1">
                    {p.status === "published" && SITE && <a href={`${SITE}/blog/${p.slug}`} target="_blank" rel="noreferrer" className="px-2 py-1 text-xs rounded-lg text-gray-600 hover:bg-gray-100">View</a>}
                    <button onClick={() => openPost(p)} className="px-2 py-1 text-xs rounded-lg text-primary hover:bg-gray-100">Edit</button>
                    <button onClick={() => removePost(p)} className="px-2 py-1 text-xs rounded-lg text-red-600 hover:bg-gray-100">Delete</button>
                  </div></td>
                </tr>
              ))}
              {filteredPosts.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No posts yet.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : tab === "cases" ? (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600"><tr>
              <th className="px-4 py-3">Case study</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Category</th><th className="px-4 py-3">Home page</th><th className="px-4 py-3">Order</th><th className="px-4 py-3 w-40 text-right">Actions</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {filteredCases.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3"><div className="font-medium text-gray-900">{c.title}</div><div className="text-xs text-gray-500">/portfolio/{c.slug}</div></td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-gray-600">{c.category || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.featured ? "Featured" : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.sort_order}</td>
                  <td className="px-4 py-3 text-right"><div className="flex items-center justify-end gap-1">
                    {c.status === "published" && SITE && <a href={`${SITE}/portfolio/${c.slug}`} target="_blank" rel="noreferrer" className="px-2 py-1 text-xs rounded-lg text-gray-600 hover:bg-gray-100">View</a>}
                    <button onClick={() => openCase(c)} className="px-2 py-1 text-xs rounded-lg text-primary hover:bg-gray-100">Edit</button>
                    <button onClick={() => removeCase(c)} className="px-2 py-1 text-xs rounded-lg text-red-600 hover:bg-gray-100">Delete</button>
                  </div></td>
                </tr>
              ))}
              {filteredCases.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No case studies yet.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {media.map((m) => (
            <div key={m.id} className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
              <div className="aspect-video bg-gray-50 flex items-center justify-center overflow-hidden"><img src={mediaSrc(m.url)} alt={m.alt ?? ""} className="object-cover w-full h-full" /></div>
              <div className="p-2 text-xs">
                <div className="truncate text-gray-800" title={m.filename}>{m.filename}</div>
                <div className="text-gray-400">{Math.round(m.size_bytes / 1024)} KB</div>
                <div className="flex gap-2 mt-1">
                  <button type="button" onClick={() => navigator.clipboard?.writeText(m.url)} className="text-primary hover:underline">Copy path</button>
                  <button type="button" onClick={() => removeMedia(m)} className="text-red-600 hover:underline">Delete</button>
                </div>
              </div>
            </div>
          ))}
          {media.length === 0 && <p className="col-span-full text-gray-500 text-sm">No images uploaded yet.</p>}
        </div>
      )}

      {/* ---------------- post editor ---------------- */}
      {postModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-10 overflow-y-auto py-6" onClick={() => setPostModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg w-full max-w-5xl p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
              <h2 className="text-lg font-semibold text-gray-900">{postModal === "new" ? "New post" : "Edit post"} {postModal !== "new" && <StatusBadge status={post.status as string} />}</h2>
              <div className="flex items-center gap-2">
                {postModal !== "new" && post.status === "published" && SITE && <a href={`${SITE}/blog/${post.slug}`} target="_blank" rel="noreferrer" className="text-sm text-gray-600 hover:underline">View on site</a>}
                <button onClick={() => setPostModal(null)} className="px-3 py-1.5 text-gray-600 hover:text-gray-900 font-medium">Close</button>
                <button onClick={() => savePost("draft")} disabled={saving} className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50">{post.status === "published" ? "Unpublish (save as draft)" : "Save draft"}</button>
                <button onClick={() => savePost("published")} disabled={saving} className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">{saving ? "Saving…" : post.status === "published" ? "Save & publish" : "Publish"}</button>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-3">
                <div><label className={labelClass}>Title</label><input className={inputClass} value={post.title ?? ""} onChange={(e) => { const title = e.target.value; setPost((f) => ({ ...f, title, slug: slugTouched ? f.slug : slugify(title) })); }} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className={labelClass}>URL slug</label><input className={inputClass} value={post.slug ?? ""} onChange={(e) => { setSlugTouched(true); setPost((f) => ({ ...f, slug: slugify(e.target.value) })); }} /></div>
                  <div><label className={labelClass}>Category</label><input className={inputClass} value={post.category ?? ""} onChange={(e) => setPost((f) => ({ ...f, category: e.target.value }))} placeholder="Web Development" /></div>
                </div>
                <div><label className={labelClass}>Excerpt (shown on cards and in search results)</label><textarea className={inputClass} rows={2} value={post.excerpt ?? ""} onChange={(e) => setPost((f) => ({ ...f, excerpt: e.target.value }))} /></div>
                <div>
                  <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
                    <label className={labelClass}>Body (Markdown)</label>
                    <div className="flex items-center gap-1 flex-wrap">
                      {[["H2", () => wrapSelection("\n## ", "\n")], ["H3", () => wrapSelection("\n### ", "\n")], ["B", () => wrapSelection("**", "**")], ["I", () => wrapSelection("*", "*")], ["Link", () => wrapSelection("[", "](https://)")], ["List", () => wrapSelection("\n- ", "\n")], ["Quote", () => wrapSelection("\n> ", "\n")], ["Code", () => wrapSelection("`", "`")]].map(([label, fn]) => (
                        <button key={label as string} type="button" onClick={fn as () => void} className="px-2 py-0.5 rounded border border-gray-300 text-xs text-gray-700 hover:bg-gray-50">{label as string}</button>
                      ))}
                      <button type="button" onClick={() => pickFile("body")} className="px-2 py-0.5 rounded border border-gray-300 text-xs text-gray-700 hover:bg-gray-50">Insert image</button>
                      <button type="button" onClick={() => setPreview((v) => !v)} className={`px-2 py-0.5 rounded border text-xs ${preview ? "bg-primary text-white border-primary" : "border-gray-300 text-gray-700 hover:bg-gray-50"}`}>{preview ? "Editing" : "Preview"}</button>
                    </div>
                  </div>
                  {preview ? (
                    <div className="prose prose-sm max-w-none rounded-lg border border-gray-200 p-4 min-h-[420px] overflow-auto" dangerouslySetInnerHTML={{ __html: previewHtml }} />
                  ) : (
                    <textarea ref={bodyRef} className={`${inputClass} font-mono text-xs leading-relaxed`} rows={22} value={post.body_md ?? ""} onChange={(e) => setPost((f) => ({ ...f, body_md: e.target.value }))} placeholder={"## First heading\n\nWrite the post here. Use **bold**, lists, links and Insert image."} />
                  )}
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <label className={labelClass}>Cover image</label>
                  {post.cover_url ? <img src={mediaSrc(post.cover_url)} alt="" className="w-full rounded-lg border border-gray-200 mb-2 aspect-video object-cover" /> : null}
                  <div className="flex gap-2">
                    <input className={inputClass} value={post.cover_url ?? ""} onChange={(e) => setPost((f) => ({ ...f, cover_url: e.target.value }))} placeholder="/cms/media/… or /blog/…" />
                    <button type="button" onClick={() => pickFile("cover")} className="px-3 py-2 rounded-lg border border-gray-300 text-xs text-gray-700 hover:bg-gray-50 whitespace-nowrap">Upload</button>
                  </div>
                  <input className={`${inputClass} mt-2`} value={post.cover_alt ?? ""} onChange={(e) => setPost((f) => ({ ...f, cover_alt: e.target.value }))} placeholder="Cover alt text (for SEO/accessibility)" />
                </div>
                <div><label className={labelClass}>Author name</label><input className={inputClass} value={post.author_name ?? ""} onChange={(e) => setPost((f) => ({ ...f, author_name: e.target.value }))} /></div>
                <div><label className={labelClass}>Publish date</label><input type="date" className={inputClass} value={(post.published_at ?? "").slice(0, 10)} onChange={(e) => setPost((f) => ({ ...f, published_at: e.target.value ? `${e.target.value}T09:00:00Z` : null }))} /><p className="text-xs text-gray-400 mt-1">Leave empty to use the moment you publish.</p></div>
                <div><label className={labelClass}>Related post slugs (one per line)</label><textarea className={inputClass} rows={3} value={(post.related_slugs ?? []).join("\n")} onChange={(e) => setPost((f) => ({ ...f, related_slugs: lines(e.target.value) }))} /></div>
                <div className="rounded-lg border border-gray-200 p-3 space-y-2">
                  <div className="text-xs font-semibold text-gray-700">SEO (optional)</div>
                  <input className={inputClass} value={post.seo_title ?? ""} onChange={(e) => setPost((f) => ({ ...f, seo_title: e.target.value }))} placeholder="Title tag (defaults to the title)" maxLength={255} />
                  <textarea className={inputClass} rows={2} value={post.seo_description ?? ""} onChange={(e) => setPost((f) => ({ ...f, seo_description: e.target.value }))} placeholder="Meta description (defaults to the excerpt)" maxLength={500} />
                </div>
                {postModal !== "new" && <button type="button" onClick={() => removePost(postModal as BlogPost)} className="text-sm text-red-600 hover:underline">Delete post</button>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- case study editor ---------------- */}
      {caseModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-10 overflow-y-auto py-6" onClick={() => setCaseModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg w-full max-w-4xl p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
              <h2 className="text-lg font-semibold text-gray-900">{caseModal === "new" ? "New case study" : "Edit case study"} {caseModal !== "new" && <StatusBadge status={cs.status as string} />}</h2>
              <div className="flex items-center gap-2">
                {caseModal !== "new" && cs.status === "published" && SITE && <a href={`${SITE}/portfolio/${cs.slug}`} target="_blank" rel="noreferrer" className="text-sm text-gray-600 hover:underline">View on site</a>}
                <button onClick={() => setCaseModal(null)} className="px-3 py-1.5 text-gray-600 hover:text-gray-900 font-medium">Close</button>
                <button onClick={() => saveCase("draft")} disabled={saving} className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-50">{cs.status === "published" ? "Unpublish" : "Save draft"}</button>
                <button onClick={() => saveCase("published")} disabled={saving} className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">{saving ? "Saving…" : cs.status === "published" ? "Save & publish" : "Publish"}</button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2"><label className={labelClass}>Title</label><input className={inputClass} value={cs.title ?? ""} onChange={(e) => { const title = e.target.value; setCs((f) => ({ ...f, title, slug: slugTouched ? f.slug : slugify(title) })); }} placeholder="Ashlar." /></div>
              <div><label className={labelClass}>URL slug</label><input className={inputClass} value={cs.slug ?? ""} onChange={(e) => { setSlugTouched(true); setCs((f) => ({ ...f, slug: slugify(e.target.value) })); }} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className={labelClass}>Category</label><input className={inputClass} value={cs.category ?? ""} onChange={(e) => setCs((f) => ({ ...f, category: e.target.value }))} /></div>
                <div><label className={labelClass}>Year</label><input className={inputClass} value={cs.year ?? ""} onChange={(e) => setCs((f) => ({ ...f, year: e.target.value }))} /></div>
              </div>
              <div className="md:col-span-2"><label className={labelClass}>Tagline</label><input className={inputClass} value={cs.tagline ?? ""} onChange={(e) => setCs((f) => ({ ...f, tagline: e.target.value }))} /></div>
              <div className="md:col-span-2"><label className={labelClass}>Overview</label><textarea className={inputClass} rows={3} value={cs.overview ?? ""} onChange={(e) => setCs((f) => ({ ...f, overview: e.target.value }))} /></div>
              <div><label className={labelClass}>Challenge</label><textarea className={inputClass} rows={4} value={cs.challenge ?? ""} onChange={(e) => setCs((f) => ({ ...f, challenge: e.target.value }))} /></div>
              <div><label className={labelClass}>Solution</label><textarea className={inputClass} rows={4} value={cs.solution ?? ""} onChange={(e) => setCs((f) => ({ ...f, solution: e.target.value }))} /></div>
              <div><label className={labelClass}>Highlights (one per line)</label><textarea className={inputClass} rows={4} value={(cs.highlights ?? []).join("\n")} onChange={(e) => setCs((f) => ({ ...f, highlights: lines(e.target.value) }))} /></div>
              <div>
                <label className={labelClass}>Results</label>
                <div className="space-y-1.5">
                  {(cs.results ?? []).map((r, i) => (
                    <div key={i} className="flex gap-2">
                      <input className={inputClass} placeholder="Label (e.g. Organic traffic)" value={r.label} onChange={(e) => setCs((f) => ({ ...f, results: (f.results ?? []).map((x, j) => (j === i ? { ...x, label: e.target.value } : x)) }))} />
                      <input className={`${inputClass} w-32`} placeholder="Value" value={r.value} onChange={(e) => setCs((f) => ({ ...f, results: (f.results ?? []).map((x, j) => (j === i ? { ...x, value: e.target.value } : x)) }))} />
                      <button type="button" onClick={() => setCs((f) => ({ ...f, results: (f.results ?? []).filter((_, j) => j !== i) }))} className="text-gray-400 hover:text-red-600 px-1">×</button>
                    </div>
                  ))}
                  <button type="button" onClick={() => setCs((f) => ({ ...f, results: [...(f.results ?? []), { label: "", value: "" }] }))} className="text-xs text-primary hover:underline">+ Add result</button>
                </div>
              </div>
              <div><label className={labelClass}>Tech stack (one per line)</label><textarea className={inputClass} rows={3} value={(cs.stack ?? []).join("\n")} onChange={(e) => setCs((f) => ({ ...f, stack: lines(e.target.value) }))} /></div>
              <div><label className={labelClass}>Tags (one per line)</label><textarea className={inputClass} rows={3} value={(cs.tags ?? []).join("\n")} onChange={(e) => setCs((f) => ({ ...f, tags: lines(e.target.value) }))} /></div>
              <div>
                <label className={labelClass}>Screenshot / cover image</label>
                {cs.image_url ? <img src={mediaSrc(cs.image_url)} alt="" className="w-full rounded-lg border border-gray-200 mb-2 aspect-video object-cover" /> : null}
                <div className="flex gap-2"><input className={inputClass} value={cs.image_url ?? ""} onChange={(e) => setCs((f) => ({ ...f, image_url: e.target.value }))} placeholder="/cms/media/… or /portfolio/…" /><button type="button" onClick={() => pickFile("cs-image")} className="px-3 py-2 rounded-lg border border-gray-300 text-xs text-gray-700 hover:bg-gray-50 whitespace-nowrap">Upload</button></div>
              </div>
              <div>
                <label className={labelClass}>Logo (shown when there is no screenshot)</label>
                <div className="flex gap-2"><input className={inputClass} value={cs.logo_url ?? ""} onChange={(e) => setCs((f) => ({ ...f, logo_url: e.target.value }))} placeholder="/logos/… or /cms/media/…" /><button type="button" onClick={() => pickFile("cs-logo")} className="px-3 py-2 rounded-lg border border-gray-300 text-xs text-gray-700 hover:bg-gray-50 whitespace-nowrap">Upload</button></div>
                <input className={`${inputClass} mt-2`} value={cs.gradient ?? ""} onChange={(e) => setCs((f) => ({ ...f, gradient: e.target.value }))} placeholder="Background gradient CSS, e.g. linear-gradient(135deg, #001639, #3d6a9e)" />
              </div>
              <div><label className={labelClass}>Related case study slugs (one per line)</label><textarea className={inputClass} rows={2} value={(cs.related_slugs ?? []).join("\n")} onChange={(e) => setCs((f) => ({ ...f, related_slugs: lines(e.target.value) }))} /></div>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={!!cs.featured} onChange={(e) => setCs((f) => ({ ...f, featured: e.target.checked }))} className="rounded border-gray-300 text-primary" /> Show on the home page (first 4 featured, by order)</label>
                <div><label className={labelClass}>Order (lower first)</label><input type="number" className={inputClass} value={cs.sort_order ?? 0} onChange={(e) => setCs((f) => ({ ...f, sort_order: parseInt(e.target.value, 10) || 0 }))} /></div>
              </div>
              <div className="md:col-span-2 rounded-lg border border-gray-200 p-3 space-y-2">
                <div className="text-xs font-semibold text-gray-700">SEO (optional)</div>
                <input className={inputClass} value={cs.seo_title ?? ""} onChange={(e) => setCs((f) => ({ ...f, seo_title: e.target.value }))} placeholder="Title tag (defaults to 'Title | Category Case Study')" />
                <textarea className={inputClass} rows={2} value={cs.seo_description ?? ""} onChange={(e) => setCs((f) => ({ ...f, seo_description: e.target.value }))} placeholder="Meta description (defaults to the tagline)" />
              </div>
              {caseModal !== "new" && <button type="button" onClick={() => removeCase(caseModal as CaseStudy)} className="text-sm text-red-600 hover:underline">Delete case study</button>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
