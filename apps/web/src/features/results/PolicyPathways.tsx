import { ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { StatusPill } from '@/components/ui/StatusPill';
import type { PolicyEligibility } from '@/types/api';

export function PolicyPathways({ policy }: { policy: PolicyEligibility }) {
  const { t } = useTranslation();
  const isIndia = policy.country === 'IN';
  return (
    <section className="card flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="m-0 text-[15px]">
          {t('results.policyTitle', {
            country: t(`country.${policy.country}`, { defaultValue: policy.country }),
          })}
        </h2>
        <span className="text-[12px] font-semibold text-amber-text">
          {isIndia ? t('results.separateMechanisms') : policy.disclaimer}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {policy.programmes.map((p) => (
          <article
            key={p.id}
            className="flex flex-col gap-2 rounded-[10px] border border-line bg-ground p-3.5"
          >
            <StatusPill status={p.status} />
            <h3 className="m-0 text-sm font-semibold">{p.name}</h3>
            <span className="text-[12px] text-muted">{p.authority}</span>
            {(p.reason || p.notes?.length) && (
              <div className="flex flex-col gap-1 text-[12px] leading-relaxed text-ink-2">
                {p.reason && <p className="m-0">{p.reason}</p>}
                {p.notes?.map((note) => (
                  <p key={note} className="m-0">
                    {note}
                  </p>
                ))}
              </div>
            )}
            {p.requirements.length > 0 && (
              <details className="text-[12px] text-ink-2">
                <summary className="cursor-pointer font-semibold text-ink">
                  {t('results.requirements')}
                </summary>
                <ul className="mb-0 mt-1 pl-4">
                  {p.requirements.map((req) => (
                    <li key={req}>{req}</li>
                  ))}
                </ul>
              </details>
            )}
            {p.references[0] && (
              <a
                href={p.references[0].url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[12px] font-semibold text-forest"
              >
                {p.references[0].title} <ExternalLink size={12} aria-hidden="true" />
              </a>
            )}
          </article>
        ))}
      </div>
      <p className="m-0 text-[12px] text-muted">{t('results.policyDisclaimer')}</p>
    </section>
  );
}
