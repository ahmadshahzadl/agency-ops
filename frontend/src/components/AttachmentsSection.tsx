import { useCallback, useEffect, useRef, useState } from "react";
import {
  listAttachments,
  uploadAttachment,
  deleteAttachment,
  downloadAttachment,
  fetchAttachmentBlobUrl,
  isImage,
  formatSize,
  type Attachment,
} from "@/api/attachments";
import { useAuth } from "@/store/auth";

interface AttachmentsSectionProps {
  entityType: "task" | "project" | "client" | "lead" | "meeting" | "invoice" | "expense";
  entityId: string | undefined;
  className?: string;
}

export function AttachmentsSection({ entityType, entityId, className = "" }: AttachmentsSectionProps) {
  const { user } = useAuth();
  const [items, setItems] = useState<Attachment[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ att: Attachment; url: string } | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const canDelete = (a: Attachment) =>
    !!user && (a.uploaded_by === user.id || user.permissions.includes("admin:all") || !!user.can_manage_tasks);

  const refresh = useCallback(async () => {
    if (!entityId) return;
    setItems(await listAttachments(entityType, entityId).catch(() => [] as Attachment[]));
  }, [entityType, entityId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const showError = (msg: string) => {
    setError(msg);
    window.setTimeout(() => setError(null), 4000);
  };

  if (!entityId) return null;

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const f of Array.from(files)) {
        const att = await uploadAttachment(entityType, entityId, f);
        setItems((xs) => [att, ...xs]);
      }
    } catch (e) {
      showError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className={`mt-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Attachments</h4>
        <label className={`text-xs font-medium text-primary hover:underline cursor-pointer ${busy ? "opacity-50 pointer-events-none" : ""}`}>
          {busy ? "Uploading…" : "+ Add file"}
          <input
            ref={fileRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => onFiles(e.target.files)}
          />
        </label>
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      <ul className="mt-2 space-y-1.5">
        {items.map((a) => (
          <li key={a.id} className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-600 px-2.5 py-1.5">
            <span className="text-base leading-none" aria-hidden>
              {isImage(a) ? "🖼️" : a.content_type === "application/pdf" ? "📄" : "📎"}
            </span>
            <button
              onClick={async () => {
                if (isImage(a) || a.content_type === "application/pdf") {
                  try {
                    const url = await fetchAttachmentBlobUrl(a.id);
                    if (isImage(a)) setPreview({ att: a, url });
                    else window.open(url, "_blank");
                  } catch {
                    showError("Could not open file");
                  }
                } else {
                  downloadAttachment(a).catch(() => showError("Download failed"));
                }
              }}
              className="min-w-0 flex-1 text-left text-sm text-gray-700 dark:text-gray-200 hover:text-primary truncate"
              title={a.filename}
            >
              {a.filename}
            </button>
            <span className="text-[11px] text-gray-400 shrink-0">{formatSize(a.size_bytes)}</span>
            {a.uploaded_by_name && <span className="hidden sm:inline text-[11px] text-gray-400 shrink-0">{a.uploaded_by_name}</span>}
            <button
              onClick={() => downloadAttachment(a).catch(() => showError("Download failed"))}
              className="text-xs font-medium text-gray-400 hover:text-primary shrink-0"
              title="Download"
            >
              ↓
            </button>
            {canDelete(a) && (
              <button
                onClick={async () => {
                  try {
                    await deleteAttachment(a.id);
                    setItems((xs) => xs.filter((x) => x.id !== a.id));
                  } catch (e) {
                    showError(e instanceof Error ? e.message : "Delete failed");
                  }
                }}
                className="text-xs font-medium text-red-400 hover:text-red-600 shrink-0"
                title="Delete"
              >
                ✕
              </button>
            )}
          </li>
        ))}
        {items.length === 0 && <li className="text-xs text-gray-400 py-1">No files attached.</li>}
      </ul>

      {/* Image preview overlay */}
      {preview && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-6"
          onClick={() => {
            URL.revokeObjectURL(preview.url);
            setPreview(null);
          }}
        >
          <div className="max-w-4xl max-h-full flex flex-col items-center gap-2">
            <img src={preview.url} alt={preview.att.filename} className="max-h-[80vh] max-w-full rounded-lg shadow-2xl" />
            <p className="text-white/80 text-sm">{preview.att.filename}</p>
          </div>
        </div>
      )}
    </div>
  );
}
