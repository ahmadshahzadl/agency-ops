export interface BulkActionsBarProps {
  selectedCount: number;
  entityName: string;
  onClear: () => void;
  onDelete: () => void;
  loading?: boolean;
}

export function BulkActionsBar({
  selectedCount,
  entityName,
  onClear,
  onDelete,
  loading = false,
}: BulkActionsBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 mb-4">
      <span className="text-sm font-medium text-gray-700">
        {selectedCount} {entityName} selected
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onClear}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-60"
        >
          Clear selection
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-60"
        >
          {loading ? "Deleting…" : "Delete selected"}
        </button>
      </div>
    </div>
  );
}
