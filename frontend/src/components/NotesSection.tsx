import { useEffect, useState } from "react";
import {
  listNotes,
  createNote,
  updateNote,
  deleteNote,
  type Note,
  type NoteEntityType,
} from "@/api/notes";
import { useAuth } from "@/store/auth";

interface NotesSectionProps {
  entityType: NoteEntityType;
  entityId: string | undefined;
  className?: string;
}

export function NotesSection({ entityType, entityId, className = "" }: NotesSectionProps) {
  const { user, hasPermission } = useAuth();
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState("");
  const [isPrivate, setIsPrivate] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editPrivate, setEditPrivate] = useState(true);

  const canRead = hasPermission("notes:read");
  const canWrite = hasPermission("notes:write");

  const loadNotes = () => {
    if (!entityId || !canRead) return;
    setLoading(true);
    listNotes(entityType as NoteEntityType, entityId)
      .then(setNotes)
      .catch(() => setNotes([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadNotes();
  }, [entityId, entityType, canRead]);

  if (!canRead) return null;
  if (!entityId) {
    return (
      <div className={`text-sm text-gray-500 ${className}`}>
        Save this item first to add notes.
      </div>
    );
  }

  const handleAdd = async () => {
    if (!content.trim() || !canWrite) return;
    try {
      await createNote({
        entity_type: entityType as NoteEntityType,
        entity_id: entityId,
        content: content.trim(),
        is_private: isPrivate,
      });
      setContent("");
      loadNotes();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to add note");
    }
  };

  const startEdit = (n: Note) => {
    setEditingId(n.id);
    setEditContent(n.content);
    setEditPrivate(n.is_private);
  };

  const handleUpdate = async () => {
    if (editingId == null || !canWrite) return;
    try {
      await updateNote(editingId, { content: editContent.trim(), is_private: editPrivate });
      setEditingId(null);
      loadNotes();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to update note");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this note?") || !canWrite) return;
    try {
      await deleteNote(id);
      setEditingId(null);
      loadNotes();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete note");
    }
  };

  const isAuthor = (n: Note) => user?.id === n.created_by;

  return (
    <div className={`border-t border-gray-200 pt-4 mt-4 ${className}`}>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Notes</h3>
      {loading ? (
        <p className="text-sm text-gray-500">Loading notes…</p>
      ) : (
        <ul className="space-y-3 mb-4">
          {notes.length === 0 ? (
            <li className="text-sm text-gray-500">No notes yet.</li>
          ) : (
            notes.map((n) => (
              <li key={n.id} className="rounded-lg bg-gray-50 dark:bg-gray-700/50 p-3 text-sm">
                {editingId === n.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border border-gray-300 text-gray-900 dark:bg-gray-800 dark:border-gray-600 dark:text-white text-sm min-h-[60px]"
                      rows={2}
                    />
                    <label className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <input
                        type="checkbox"
                        checked={editPrivate}
                        onChange={(e) => setEditPrivate(e.target.checked)}
                      />
                      Only me (private)
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={handleUpdate}
                        className="px-2 py-1 rounded bg-primary text-white text-xs font-medium"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="px-2 py-1 rounded border border-gray-300 text-gray-700 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-gray-900 dark:text-white whitespace-pre-wrap">{n.content}</p>
                    <div className="flex items-center justify-between mt-2 flex-wrap gap-1">
                      <span className="text-gray-500 dark:text-gray-400 text-xs">
                        {n.created_by_name ?? "—"} · {new Date(n.created_at).toLocaleString()}
                        {n.is_private && (
                          <span className="ml-1 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200 px-1">
                            Private
                          </span>
                        )}
                      </span>
                      {canWrite && isAuthor(n) && (
                        <div className="flex gap-1">
                          <button
                            type="button"
                            onClick={() => startEdit(n)}
                            className="text-xs text-primary hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(n.id)}
                            className="text-xs text-red-600 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </li>
            ))
          )}
        </ul>
      )}

      {canWrite && (
        <div className="space-y-2">
          <textarea
            placeholder="Add a note…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 dark:bg-gray-800 dark:border-gray-600 dark:text-white text-sm min-h-[70px]"
            rows={2}
          />
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
            />
            Only me (private) — uncheck to let others see this note
          </label>
          <button
            type="button"
            onClick={handleAdd}
            disabled={!content.trim()}
            className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add note
          </button>
        </div>
      )}
    </div>
  );
}
