import { useId, useState } from 'react';
import { Check, Minus, X, TriangleAlert, type LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  firstAttentionGuardrail,
  guardrailTone,
  humanizeKey,
  type BadgeTone,
} from '../logic/agentsLogic';
import type { Guardrail } from '../types';

const CHIP_TONES: Record<BadgeTone, string> = {
  mint: 'border-forest/25 bg-mint text-forest-deep',
  amber: 'border-amber-text/35 bg-amber-tint text-amber-text',
  rose: 'border-rose-700/35 bg-rose-50 text-rose-800',
  blue: 'border-line bg-blue-tint text-blue-text',
  grey: 'border-line bg-ground text-ink-2',
  forest: 'border-forest bg-forest text-white',
  dark: 'border-panel-dark bg-panel-dark text-white',
};

const MARK_ICONS: Record<string, LucideIcon> = { '✓': Check, '!': TriangleAlert, '✕': X };

/**
 * Safety checks that ran on the result. Hover, focus or tap a chip to read the detail; a warning
 * or failure is explained straight away so it never hides behind a hover.
 */
export function GuardrailsStrip({ guardrails }: { guardrails: Guardrail[] }) {
  const { t } = useTranslation();
  const baseId = useId();
  const [active, setActive] = useState<string | null>(null);
  if (guardrails.length === 0) return null;

  const attention = firstAttentionGuardrail(guardrails);
  const shown = guardrails.find((g) => g.id === (active ?? attention?.id)) ?? null;
  const labelOf = (g: Guardrail) =>
    t(`agentsPage.guardrails.${g.id}`, { defaultValue: humanizeKey(g.id) });

  return (
    <section
      aria-label={t('agentsPage.guardrailsTitle')}
      className="card flex flex-col gap-2 px-4 py-3"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="eyebrow">{t('agentsPage.guardrailsTitle')}</span>
        <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
          {guardrails.map((g) => {
            const tone = guardrailTone(g.status);
            const Mark = MARK_ICONS[tone.mark] ?? Minus;
            const detailId = `${baseId}-${g.id}`;
            return (
              <li key={g.id}>
                <button
                  type="button"
                  aria-describedby={detailId}
                  onMouseEnter={() => setActive(g.id)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(g.id)}
                  onBlur={() => setActive(null)}
                  onClick={() => setActive(g.id)}
                  className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12.5px] font-semibold ${CHIP_TONES[tone.tone]}`}
                >
                  <Mark size={13} aria-hidden="true" />
                  <span>{labelOf(g)}</span>
                  <span className="sr-only">: {t(`agentsPage.guardrailStatus.${g.status}`)}</span>
                </button>
                <span id={detailId} className="sr-only">
                  {g.detail}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
      <p aria-hidden="true" className="m-0 min-h-[20px] text-[12.5px] leading-snug text-ink-2">
        {shown ? (
          <>
            <strong className="font-semibold text-ink">{labelOf(shown)}:</strong> {shown.detail}
          </>
        ) : (
          t('agentsPage.guardrailsHint')
        )}
      </p>
    </section>
  );
}
