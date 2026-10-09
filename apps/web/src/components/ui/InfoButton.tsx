import { useEffect, useId, useRef, useState } from 'react';

interface InfoButtonProps {
  label: string;
  text: string;
}

/** Small (i) button that toggles an accessible explanation popover. */
export function InfoButton({ label, text }: InfoButtonProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <span ref={ref} className="relative inline-flex">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="flex h-6 w-6 items-center justify-center rounded-full border border-line bg-ground font-mono text-[11px] text-ink-2 hover:bg-mint"
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute right-0 top-8 z-30 w-64 rounded-[10px] border border-line bg-surface p-3 text-left text-[12px] leading-relaxed text-ink-2 shadow-float"
        >
          {text}
        </span>
      )}
    </span>
  );
}
