export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'dark';
export type ButtonSize = 'sm' | 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-2 rounded-[10px] font-semibold transition-colors disabled:opacity-50 whitespace-nowrap';
const variants: Record<ButtonVariant, string> = {
  primary: 'bg-forest text-white hover:bg-forest-deep',
  secondary: 'bg-surface text-ink border border-line hover:bg-ground',
  ghost: 'bg-transparent text-ink-2 hover:bg-mint hover:text-forest-deep',
  dark: 'bg-panel-dark text-white hover:bg-panel-dark-2',
};
const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-[13px]',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-5 text-[15px]',
};

/** Shared button classes, usable on <button>, <a> and router <Link>. */
export function buttonClass(
  variant: ButtonVariant = 'primary',
  size: ButtonSize = 'md',
  extra = '',
) {
  return `${base} ${variants[variant]} ${sizes[size]} ${extra}`.trim();
}
