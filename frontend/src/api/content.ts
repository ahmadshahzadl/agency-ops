import { apiFetch } from "./client";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type ContentStatus = "draft" | "published";

export interface BlogPost {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  category: string | null;
  body_md: string;
  cover_url: string | null;
  cover_alt: string | null;
  related_slugs: string[];
  seo_title: string | null;
  seo_description: string | null;
  author_name: string | null;
  status: ContentStatus | string;
  published_at: string | null;
  read_time: string;
  word_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export type BlogPostInput = Omit<BlogPost, "id" | "read_time" | "word_count" | "created_at" | "updated_at">;

export interface ResultItem {
  label: string;
  value: string;
}

export interface CaseStudy {
  id: string;
  slug: string;
  title: string;
  tagline: string | null;
  category: string | null;
  tags: string[];
  year: string | null;
  overview: string | null;
  challenge: string | null;
  solution: string | null;
  highlights: string[];
  results: ResultItem[];
  stack: string[];
  related_slugs: string[];
  image_url: string | null;
  logo_url: string | null;
  gradient: string | null;
  featured: boolean;
  sort_order: number;
  seo_title: string | null;
  seo_description: string | null;
  status: ContentStatus | string;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type CaseStudyInput = Omit<CaseStudy, "id" | "created_at" | "updated_at">;

export interface Media {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  alt: string | null;
  url: string;
  created_at: string | null;
}

/** Absolute URL for a CMS media path (the website serves it at /cms/media/..., the API at /api/v1/public/content/media/...). */
export function mediaSrc(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/cms/media/")) return `${API_BASE}/api/v1/public/content/media/${url.slice("/cms/media/".length)}`;
  if (url.startsWith("/")) {
    const site = (import.meta.env.VITE_BOOKING_PUBLIC_URL as string | undefined)?.replace(/\/$/, "");
    return site ? `${site}${url}` : url;
  }
  return url;
}

// ---- posts ----
export const listPosts = (q?: string) => apiFetch<BlogPost[]>(`/api/v1/content/posts${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const createPost = (data: Partial<BlogPostInput>) => apiFetch<BlogPost>("/api/v1/content/posts", { method: "POST", body: JSON.stringify(data) });
export const updatePost = (id: string, data: Partial<BlogPostInput>) => apiFetch<BlogPost>(`/api/v1/content/posts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const deletePost = (id: string) => apiFetch<void>(`/api/v1/content/posts/${id}`, { method: "DELETE" });

// ---- case studies ----
export const listCaseStudies = (q?: string) => apiFetch<CaseStudy[]>(`/api/v1/content/case-studies${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const createCaseStudy = (data: Partial<CaseStudyInput>) => apiFetch<CaseStudy>("/api/v1/content/case-studies", { method: "POST", body: JSON.stringify(data) });
export const updateCaseStudy = (id: string, data: Partial<CaseStudyInput>) => apiFetch<CaseStudy>(`/api/v1/content/case-studies/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteCaseStudy = (id: string) => apiFetch<void>(`/api/v1/content/case-studies/${id}`, { method: "DELETE" });

// ---- media ----
export const listMedia = () => apiFetch<Media[]>("/api/v1/content/media");
export const deleteMedia = (id: string) => apiFetch<void>(`/api/v1/content/media/${id}`, { method: "DELETE" });

export async function uploadMedia(file: File, alt?: string): Promise<Media> {
  const fd = new FormData();
  fd.append("file", file);
  if (alt) fd.append("alt", alt);
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/api/v1/content/media`, { method: "POST", body: fd, headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}
