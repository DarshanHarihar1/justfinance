import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { cn } from "@/lib/cn";

const MAX_BYTES = 10 * 1024 * 1024;

type Props = {
  onFile: (file: File) => void;
  disabled?: boolean;
  compact?: boolean;
};

export function Dropzone({ onFile, disabled, compact }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function validate(file: File): string | null {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      return "Please choose a PDF file.";
    }
    if (file.size > MAX_BYTES) return "File must be 10 MB or smaller.";
    return null;
  }

  function handle(file: File) {
    const err = validate(file);
    if (err) {
      alert(err);
      return;
    }
    onFile(file);
  }

  if (compact) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-muted] px-4 py-3 text-sm">
        <span className="truncate text-[--color-text-muted]">Processing statement…</span>
        <button
          type="button"
          className="text-[--color-accent] hover:underline"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          Change file
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handle(f);
          }}
        />
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f) handle(f);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-[--radius-lg] border border-dashed border-[--color-border-strong] bg-[--color-bg-elevated] px-6 py-16 text-center transition-colors duration-150",
        dragOver && "border-[--color-accent] bg-[--color-accent-soft]",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <Upload className="mb-4 h-8 w-8 text-[--color-text-subtle]" strokeWidth={1.5} />
      <p className="text-sm font-medium">Drop your PhonePe statement PDF here</p>
      <p className="mt-1 text-sm text-[--color-text-muted]">or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handle(f);
        }}
      />
    </div>
  );
}
