import type { ReactNode } from 'react';
import type { BadgeTone } from '../logic/agentsLogic';

const TONES: Record<BadgeTone, string> = {
  blue: 'bg-blue-tint text-blue-text',
  mint: 'bg-mint text-forest-deep',
  amber: 'bg-amber-tint text-amber-text',
  grey: 'bg-ground text-ink-2',
  forest: 'bg-forest text-white',
  dark: 'bg-panel-dark text-white',
  rose: 'bg-rose-50 text-rose-800',
};

interface BadgeProps {
  tone: BadgeTone;
  children: ReactNode;
  size?: 'sm' | 'md';
  className?: string;
}

/** Small rounded label. Always paired with an icon or a word, so colour is never the only signal. */
export function Badge({ tone, children, size = 'sm', className = '' }: BadgeProps) {
  const sizing = size === 'md' ? 'px-3 py-1.5 text-[12px]' : 'px-2.5 py-1 text-[11px]';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold leading-none ${sizing} ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
