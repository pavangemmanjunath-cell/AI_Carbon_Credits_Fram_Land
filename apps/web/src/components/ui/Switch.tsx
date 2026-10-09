import { useId, type ReactNode } from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: ReactNode;
  hint?: ReactNode;
  /** Rendered after the label (for example an InfoButton). */
  extra?: ReactNode;
  disabled?: boolean;
}

/** On/off toggle (`role="switch"`), label on the left like Trimble's import options. */
export function Switch({ checked, onChange, label, hint, extra, disabled }: SwitchProps) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="flex items-center gap-2 text-sm text-ink">
          <label htmlFor={id} className="cursor-pointer">
            {label}
          </label>
          {extra}
        </span>
        {hint && <span className="text-[12px] text-muted">{hint}</span>}
      </span>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${checked ? 'bg-forest' : 'bg-line'}`}
      >
        <span
          aria-hidden="true"
          className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-[22px]' : 'translate-x-[2px]'}`}
        />
      </button>
    </div>
  );
}
