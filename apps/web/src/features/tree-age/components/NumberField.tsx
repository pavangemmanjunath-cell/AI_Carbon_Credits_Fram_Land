import type { ReactNode } from 'react';
import { useNumberDraft, type DraftParse } from '../useNumberDraft';

interface NumberFieldProps {
  id: string;
  label: ReactNode;
  /** The value the page is using now. */
  value: number | null;
  onCommit: (value: number | null) => void;
  parse: (text: string) => DraftParse;
  unit?: string;
  hint?: ReactNode;
  disabled?: boolean;
  inputMode?: 'numeric' | 'decimal';
  /** Shown inside the box while it is empty or switched off. */
  placeholder?: string;
}

/** A labelled number box with a unit, a hint and a message that is read out when it changes. */
export function NumberField({
  id,
  label,
  value,
  onCommit,
  parse,
  unit,
  hint,
  disabled = false,
  inputMode = 'numeric',
  placeholder,
}: NumberFieldProps) {
  const { text, error, onChange, onBlur } = useNumberDraft({ value, parse, onCommit });
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  return (
    <div className="flex flex-col">
      <label htmlFor={id} className="mb-1.5 text-[12px] font-medium text-ink-2">
        {label}
      </label>
      <span
        className={`flex overflow-hidden rounded-[10px] border bg-surface focus-within:shadow-[0_0_0_3px_var(--mint)] ${
          error ? 'border-rose-600' : 'border-line focus-within:border-forest'
        } ${disabled ? 'bg-ground opacity-70' : ''}`}
      >
        <input
          id={id}
          type="text"
          inputMode={inputMode}
          autoComplete="off"
          value={disabled ? '' : text}
          placeholder={placeholder}
          disabled={disabled}
          onChange={onChange}
          onBlur={onBlur}
          aria-invalid={error ? true : undefined}
          aria-describedby={`${hint ? `${hintId} ` : ''}${errorId}`}
          className="h-10 min-w-0 flex-1 bg-transparent px-3 font-mono text-[15px] outline-none"
        />
        {unit && (
          <span className="flex items-center border-l border-line px-3 text-[13px] text-muted">
            {unit}
          </span>
        )}
      </span>
      {hint && (
        <p id={hintId} className="m-0 mt-1.5 text-[12px] leading-snug text-muted">
          {hint}
        </p>
      )}
      <p
        id={errorId}
        aria-live="polite"
        className="m-0 mt-1 text-[12px] font-medium text-rose-700 empty:mt-0"
      >
        {error}
      </p>
    </div>
  );
}
