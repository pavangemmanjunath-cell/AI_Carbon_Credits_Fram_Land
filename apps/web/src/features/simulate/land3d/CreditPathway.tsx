import { Award, BadgeCheck, ClipboardList, ExternalLink, Ruler, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { SimulationProgramme } from '@/types/api';
import { CREDIT_STEPS, type CreditStep } from './landScene';
import './i18n';

const ICONS: Record<CreditStep, typeof Award> = {
  design: ClipboardList,
  validation: ShieldCheck,
  monitoring: Ruler,
  verification: BadgeCheck,
  issuance: Award,
};

/**
 * The generic project cycle a recognised programme requires before any credit
 * exists. Deliberately shows no progress: this tool cannot know (or do) any
 * of these steps, so it never marks one as done.
 */
export function CreditPathway({
  programmes,
  regionName,
}: {
  programmes: SimulationProgramme[];
  regionName: string;
}) {
  const { t } = useTranslation();
  return (
    <section className="card flex flex-col gap-3 p-5" aria-labelledby="credit-pathway-title">
      <div className="flex flex-col gap-1">
        <h2 id="credit-pathway-title" className="m-0 text-[15px]">
          {t('land3d.pathwayTitle')}
        </h2>
        <p className="m-0 text-[12.5px] leading-relaxed text-ink-2">{t('land3d.pathwayNote')}</p>
      </div>
      <ol className="m-0 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2 lg:grid-cols-5">
        {CREDIT_STEPS.map((step, i) => {
          const Icon = ICONS[step];
          return (
            <li
              key={step}
              className="relative flex flex-col gap-1.5 rounded-[12px] border border-line bg-surface p-3"
            >
              <span className="flex items-center gap-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mint text-forest-deep">
                  <Icon size={16} aria-hidden="true" />
                </span>
                <span className="text-[13px] font-semibold text-ink">
                  {i + 1}. {t(`land3d.steps.${step}.title`)}
                </span>
              </span>
              <span className="text-[12px] leading-relaxed text-ink-2">
                {t(`land3d.steps.${step}.body`)}
              </span>
            </li>
          );
        })}
      </ol>
      {programmes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
          <span className="text-muted">
            {t('land3d.pathwayProgrammes', { region: regionName })}:
          </span>
          {programmes.map((p) =>
            p.url ? (
              <a
                key={p.id}
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-full border border-line px-2.5 py-1 font-semibold text-forest no-underline hover:bg-ground"
              >
                {p.name} <ExternalLink size={12} aria-hidden="true" />
              </a>
            ) : (
              <span key={p.id} className="rounded-full border border-line px-2.5 py-1 text-ink-2">
                {p.name}
              </span>
            ),
          )}
        </div>
      )}
    </section>
  );
}
