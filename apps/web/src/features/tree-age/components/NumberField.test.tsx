import '../i18n';
import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { checkWholeNumber } from '../logic/treeAgeLogic';
import type { DraftParse } from '../useNumberDraft';
import { NumberField } from './NumberField';

const parse = (text: string): DraftParse => {
  const checked = checkWholeNumber(text, 1, 100);
  return checked.ok ? checked : { ok: false, message: `Problem: ${checked.problem}` };
};

/** The page owns the value; the box reports valid numbers and the page passes them back down. */
function Harness({
  initial = 25,
  onCommit,
  disabled = false,
}: {
  initial?: number | null;
  onCommit: (value: number | null) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState<number | null>(initial);
  return (
    <>
      <NumberField
        id="count"
        label="Number of things"
        value={value}
        unit="things"
        hint="Count them."
        parse={parse}
        disabled={disabled}
        onCommit={(next) => {
          onCommit(next);
          setValue(next);
        }}
      />
      <button type="button" onClick={() => setValue(77)}>
        Set from outside
      </button>
    </>
  );
}

describe('NumberField', () => {
  it('shows the value, its unit and its hint, and ties the hint to the box', () => {
    render(<Harness onCommit={vi.fn()} />);
    const input = screen.getByLabelText('Number of things');
    expect(input).toHaveValue('25');
    expect(screen.getByText('things')).toBeVisible();
    expect(screen.getByText('Count them.')).toBeVisible();
    expect(input).toHaveAccessibleDescription(/^Count them\.\s*$/);
  });

  it('sends every valid number on at once while someone types', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness onCommit={onCommit} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    await user.type(input, '42');
    expect(onCommit.mock.calls.map((c) => c[0])).toEqual([4, 42]);
    expect(input).toHaveValue('42');
  });

  it('lets someone clear the box and type again without a fight', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness onCommit={onCommit} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    // Empty is not a number yet: the box stays empty and says why, and nothing is sent.
    expect(input).toHaveValue('');
    expect(screen.getByText('Problem: empty')).toBeVisible();
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(onCommit).not.toHaveBeenCalled();
  });

  it('keeps what was typed and explains a mistake, without sending it', async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<Harness onCommit={onCommit} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    await user.type(input, '1x');
    expect(input).toHaveValue('1x');
    expect(screen.getByText('Problem: not-a-number')).toBeVisible();
    // The "1" before the "x" was a good number and was sent.
    expect(onCommit).toHaveBeenCalledExactlyOnceWith(1);
  });

  it('puts the value in use back in the box when it loses focus', async () => {
    const user = userEvent.setup();
    render(<Harness onCommit={vi.fn()} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    await user.type(input, '1x');
    await user.tab();
    expect(input).toHaveValue('1');
    expect(screen.queryByText(/^Problem:/)).not.toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-invalid');
  });

  it('forgets a half-typed draft when the value changes for another reason', async () => {
    const user = userEvent.setup();
    render(<Harness onCommit={vi.fn()} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    await user.type(input, '9z');
    expect(input).toHaveValue('9z');
    // A plain click event, so the box keeps its focus (and its draft) until the value moves on.
    fireEvent.click(screen.getByRole('button', { name: 'Set from outside' }));
    expect(input).toHaveFocus();
    expect(input).toHaveValue('77');
    expect(screen.queryByText(/^Problem:/)).not.toBeInTheDocument();
  });

  it('reads out a problem politely, next to the box', async () => {
    const user = userEvent.setup();
    render(<Harness onCommit={vi.fn()} />);
    const input = screen.getByLabelText('Number of things');
    await user.clear(input);
    await user.type(input, '500');
    const message = screen.getByText('Problem: too-big');
    expect(message).toHaveAttribute('aria-live', 'polite');
    expect(input).toHaveAccessibleDescription(/Count them\.\s+Problem: too-big/);
  });

  it('is empty and switched off when it does not apply', () => {
    render(<Harness onCommit={vi.fn()} disabled />);
    const input = screen.getByLabelText('Number of things');
    expect(input).toBeDisabled();
    expect(input).toHaveValue('');
  });

  it('shows an empty box for "no value"', () => {
    render(<Harness onCommit={vi.fn()} initial={null} />);
    expect(screen.getByLabelText('Number of things')).toHaveValue('');
  });
});
