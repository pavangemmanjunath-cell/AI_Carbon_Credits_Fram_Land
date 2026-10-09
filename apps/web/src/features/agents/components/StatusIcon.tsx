import {
  Circle,
  CircleCheck,
  CircleMinus,
  CircleX,
  LoaderCircle,
  TriangleAlert,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PipelineStatus } from '../types';

const STYLES: Record<PipelineStatus, string> = {
  pending: 'text-muted',
  running: 'text-forest',
  done: 'text-forest',
  warning: 'text-amber-text',
  failed: 'text-rose-700',
  skipped: 'text-muted',
};

/** Status of one agent. The icon shape and a hidden word carry the meaning, not only the colour. */
export function StatusIcon({ status, size = 18 }: { status: PipelineStatus; size?: number }) {
  const { t } = useTranslation();
  const common = { size, 'aria-hidden': true } as const;
  const icon = {
    pending: <Circle {...common} />,
    running: <LoaderCircle {...common} className="animate-spin" />,
    done: <CircleCheck {...common} />,
    warning: <TriangleAlert {...common} />,
    failed: <CircleX {...common} />,
    skipped: <CircleMinus {...common} />,
  }[status];
  return (
    <span className={`inline-flex ${STYLES[status]}`}>
      {icon}
      <span className="sr-only">{t(`agentsPage.status.${status}`)}</span>
    </span>
  );
}
