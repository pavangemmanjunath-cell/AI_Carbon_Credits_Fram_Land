import { useState, type ChangeEvent } from 'react';

export type DraftParse = { ok: true; value: number | null } | { ok: false; message: string };

interface DraftOptions {
  /** The value the page is using now (from the address bar). */
  value: number | null;
  parse: (text: string) => DraftParse;
  /** Called only with a value that passed `parse`. */
  onCommit: (value: number | null) => void;
}

/**
 * Lets someone type freely into a number box. Every keystroke that makes a valid number is sent
 * on at once; text that is not valid yet ("", "1.", "abc") stays in the box with a message and
 * changes nothing else. When the box loses focus it shows the value the page is really using, so
 * the box and the results never disagree for long.
 */
export function useNumberDraft({ value, parse, onCommit }: DraftOptions) {
  // `base` is the page value the draft was typed against. If the page value moves on for another
  // reason (the slider, the back button), the draft is stale and ignored.
  const [draft, setDraft] = useState<{ text: string; base: number | null } | null>(null);
  const active = draft !== null && draft.base === value;
  const text = active ? draft.text : value === null ? '' : String(value);
  const checked = active ? parse(draft.text) : null;
  const error = checked && !checked.ok ? checked.message : null;

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.value;
    const parsed = parse(next);
    setDraft({ text: next, base: parsed.ok ? parsed.value : value });
    if (parsed.ok && parsed.value !== value) onCommit(parsed.value);
  };
  const onBlur = () => setDraft(null);

  return { text, error, onChange, onBlur };
}
