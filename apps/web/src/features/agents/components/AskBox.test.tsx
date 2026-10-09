import '../i18n';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AskBox } from './AskBox';

describe('AskBox', () => {
  it('offers the four suggested questions and sends one on a single click', async () => {
    const user = userEvent.setup();
    const onAsk = vi.fn();
    render(<AskBox onAsk={onAsk} />);
    const suggestions = screen.getByRole('list', { name: 'Suggested questions' });
    expect(suggestions.querySelectorAll('button')).toHaveLength(4);
    expect(
      screen.getByRole('button', { name: 'How much carbon will my trees store?' }),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Which programmes can I join?' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'What if I plant 200 more trees?' })).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Are my old trees eligible for credits?' }),
    ).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Which programmes can I join?' }));
    expect(onAsk).toHaveBeenCalledExactlyOnceWith('Which programmes can I join?');
  });

  it('sends a typed question trimmed, then clears the box', async () => {
    const user = userEvent.setup();
    const onAsk = vi.fn();
    render(<AskBox onAsk={onAsk} />);
    const input = screen.getByLabelText('Ask the agents');
    await user.type(input, '   How old are my trees?  ');
    await user.click(screen.getByRole('button', { name: 'Ask' }));
    expect(onAsk).toHaveBeenCalledExactlyOnceWith('How old are my trees?');
    expect(input).toHaveValue('');
  });

  it('asks for a question instead of sending an empty one', async () => {
    const user = userEvent.setup();
    const onAsk = vi.fn();
    render(<AskBox onAsk={onAsk} />);
    await user.click(screen.getByRole('button', { name: 'Ask' }));
    expect(onAsk).not.toHaveBeenCalled();
    expect(screen.getByText('Type a question first.')).toBeInTheDocument();
    expect(screen.getByLabelText('Ask the agents')).toHaveAttribute('aria-invalid', 'true');
  });

  it('stops at 500 characters and shows the count', async () => {
    const user = userEvent.setup();
    render(<AskBox onAsk={vi.fn()} />);
    const input = screen.getByLabelText('Ask the agents');
    expect(input).toHaveAttribute('maxlength', '500');
    await user.click(input);
    await user.paste('a'.repeat(620));
    expect(screen.getByText('500/500')).toBeInTheDocument();
  });

  it('tells people the question never carries coordinates', () => {
    render(<AskBox onAsk={vi.fn()} />);
    expect(screen.getByText(/never sent to an AI model/i)).toBeInTheDocument();
  });

  it('is switched off while the agents are working or no plot is picked', async () => {
    const user = userEvent.setup();
    const onAsk = vi.fn();
    const { rerender } = render(<AskBox onAsk={onAsk} busy />);
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Which programmes can I join?' }));
    expect(onAsk).not.toHaveBeenCalled();

    rerender(<AskBox onAsk={onAsk} disabled />);
    expect(screen.getByLabelText('Ask the agents')).toBeDisabled();
    expect(screen.getByText('Pick a plot first.')).toBeInTheDocument();
  });
});
