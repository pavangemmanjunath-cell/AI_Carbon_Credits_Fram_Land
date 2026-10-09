import { useId, useState, type ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';

interface DisclosureProps {
  label: ReactNode;
  /** Small muted text after the label, e.g. "2 tools · 1 source". */
  meta?: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  children: ReactNode;
}

/** A button that shows or hides a region. The content is only rendered while open. */
export function Disclosure({
  label,
  meta,
  defaultOpen = false,
  className = '',
  children,
}: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const regionId = useId();
  return (
    <div className={className}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={open ? regionId : undefined}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex items-center gap-1.5 rounded-md py-1 text-[13px] font-semibold text-forest hover:text-forest-deep"
      >
        <ChevronRight
          size={15}
          aria-hidden="true"
          className={`transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <span>{label}</span>
        {meta && <span className="font-normal text-muted">{meta}</span>}
      </button>
      {open && (
        <div id={regionId} className="mt-2">
          {children}
        </div>
      )}
    </div>
  );
}
