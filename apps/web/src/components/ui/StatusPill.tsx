import { useTranslation } from 'react-i18next';
import type { PolicyStatus } from '@/types/api';

const TONES: Record<string, string> = {
  potentially_applicable: 'bg-mint text-forest-deep',
  requires_assessment: 'bg-amber-tint text-amber-text',
  requires_methodology_assessment: 'bg-amber-tint text-amber-text',
  requires_certification: 'bg-blue-tint text-blue-text',
  not_applicable: 'bg-ground text-muted',
  unknown: 'bg-ground text-muted',
};

export function StatusPill({ status }: { status: PolicyStatus | string }) {
  const { t } = useTranslation();
  const tone = TONES[status] ?? TONES.unknown;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold ${tone}`}
    >
      {t(`policyStatus.${status}`, { defaultValue: status.replace(/_/g, ' ') })}
    </span>
  );
}

export function Pill({
  children,
  tone = 'mint',
}: {
  children: React.ReactNode;
  tone?: 'mint' | 'amber' | 'blue' | 'grey' | 'dark';
}) {
  const cls = {
    mint: 'bg-mint text-forest-deep',
    amber: 'bg-amber-tint text-amber-text',
    blue: 'bg-blue-tint text-blue-text',
    grey: 'bg-ground text-ink-2',
    dark: 'bg-panel-dark text-white',
  }[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${cls}`}
    >
      {children}
    </span>
  );
}
