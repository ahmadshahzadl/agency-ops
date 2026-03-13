export interface AlertModalProps {
  open: boolean;
  title?: string;
  message: string;
  onClose: () => void;
}

export default function AlertModal({
  open,
  title = "Message",
  message,
  onClose,
}: AlertModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="alert-title"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="alert-title" className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {title}
        </h2>
        <p className="text-gray-600 dark:text-gray-300 mb-6">{message}</p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
