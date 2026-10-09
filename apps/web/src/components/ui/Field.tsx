import type { ReactNode } from 'react';

interface FieldProps {
  id: string;
  label: ReactNode;
  icon?: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
  inline?: boolean;
}

/** Label + control pair. `inline` renders the label in a fixed left column (plot panel). */
export function Field({ id, label, icon, hint, children, inline = false }: FieldProps) {
  if (inline) {
    return (
      <label htmlFor={id} className="grid grid-cols-[132px_minmax(0,1fr)] items-center gap-2.5 text-sm text-ink-2">
        <span className="flex items-center gap-2">
          {icon}
          {label}
        </span>
        <span className="min-w-0">{children}</span>
        {hint && <span className="col-span-2 text-[12px] text-muted">{hint}</span>}
      </label>
    );
  }
  return (
    <label htmlFor={id} className="flex flex-col gap-1.5 text-[12px] text-ink-2">
      <span className="flex items-center gap-2">
        {icon}
        {label}
      </span>
      {children}
      {hint && <span className="text-[12px] text-muted">{hint}</span>}
    </label>
  );
}

export function UnitInput({ unit, children }: { unit: string; children: ReactNode }) {
  return (
    <span className="flex overflow-hidden rounded-[10px] border border-line bg-surface focus-within:border-forest focus-within:shadow-[0_0_0_3px_var(--mint)]">
      {children}
      <span className="flex items-center border-l border-line px-3 text-[13px] text-muted">{unit}</span>
    </span>
  );
}
