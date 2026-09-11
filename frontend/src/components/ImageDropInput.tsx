import { useEffect, useRef, useState } from "react";

/** Optional image picker: click to browse or drag & drop, with thumbnail
 * previews and per-file remove. Purely local — the parent uploads the
 * files after it creates its entity. */
export function ImageDropInput({
  files,
  onChange,
  max = 5,
  label = "Screenshots (optional)",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max?: number;
  label?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [previews, setPreviews] = useState<string[]>([]);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  const addFiles = (incoming: FileList | File[]) => {
    const images = Array.from(incoming).filter((f) => f.type.startsWith("image/"));
    if (images.length === 0) return;
    onChange([...files, ...images].slice(0, max));
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        className={`rounded-xl border-2 border-dashed px-3 py-4 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-gray-300 dark:border-gray-600 hover:border-primary/50"
        }`}
      >
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium text-primary">{label}</span>
          {" — "}drag & drop images here, or click to browse
          {files.length > 0 && ` (${files.length}/${max})`}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {files.map((f, i) => (
            <div key={i} className="relative group">
              <img
                src={previews[i]}
                alt={f.name}
                title={f.name}
                className="w-16 h-16 object-cover rounded-lg border border-gray-200 dark:border-gray-600"
              />
              <button
                type="button"
                onClick={() => onChange(files.filter((_, j) => j !== i))}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] leading-none flex items-center justify-center shadow opacity-90 hover:opacity-100"
                aria-label={`Remove ${f.name}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
