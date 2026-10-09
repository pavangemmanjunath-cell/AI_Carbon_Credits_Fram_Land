import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Readiness } from '@/types/api';

const IMPROVE_KEYS = ['dbh', 'baseline', 'management', 'height', 'mortality'];

export function ReadinessCard({ readiness }: { readiness: Readiness }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const r = 38;
  const circumference = 2 * Math.PI * r;
  const dash = (readiness.score / 100) * circumference;
  const color = readiness.grade === 'high' ? '#1E6B41' : readiness.grade === 'medium' ? '#B7791F' : '#B42318';
  return (
    <section className="card flex flex-col gap-3.5 p-5">
      <div className="flex items-center gap-4">
        <svg width="92" height="92" viewBox="0 0 92 92" role="img" aria-label={t('results.readinessScore', { score: readiness.score })}>
          <circle cx="46" cy="46" r={r} fill="none" stroke="#E3E9E4" strokeWidth="10" />
          <circle cx="46" cy="46" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" strokeDasharray={`${dash} ${circumference}`} transform="rotate(-90 46 46)" />
          <text x="46" y="51" textAnchor="middle" fontSize="22" fontWeight="700" fill="#14211A" fontFamily="Space Grotesk, sans-serif">
            {readiness.score}
          </text>
        </svg>
        <div className="flex flex-col gap-0.5">
          <h2 className="m-0 text-[15px]">{t('results.readinessTitle')}</h2>
          <span className="text-[13px] text-ink-2">
            {t(`confidence.${readiness.grade}`)} · {t('results.readinessScore', { score: readiness.score })}
          </span>
        </div>
      </div>
      <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-[13px]">
        {readiness.missing_evidence.map((item) => (
          <li key={item.id} className="flex gap-2 text-amber-text">
            <span className="font-bold">!</span>
            {item.label} <span className="ml-auto font-mono text-[11px] text-muted">{t('results.weight', { weight: item.weight })}</span>
          </li>
        ))}
        <li className="flex gap-2 text-forest">
          <span className="font-bold">✓</span>
          {readiness.present_evidence.map((e) => e.label).join(' · ')}
        </li>
      </ul>
      <Button variant="secondary" onClick={() => setOpen(true)} className="border-forest text-forest-deep">
        {t('results.improveReadiness')}
      </Button>
      <Dialog open={open} title={t('results.improveTitle')} onClose={() => setOpen(false)}>
        <p className="mt-0 text-sm text-ink-2">{t('results.improveIntro')}</p>
        <ol className="m-0 flex flex-col gap-2.5 pl-5 text-sm">
          {readiness.missing_evidence.map((item) => (
            <li key={item.id}>
              <strong>{item.label}.</strong>{' '}
              {t(IMPROVE_KEYS.includes(item.id) ? `results.improve_${item.id}` : 'results.improve_generic')}
            </li>
          ))}
        </ol>
      </Dialog>
    </section>
  );
}
