import { useQuery } from '@tanstack/react-query';
import { Lightbulb } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatNumber } from '@/lib/format';
import { request } from '@/services/api';
import type { SimulateBody } from '@/types/api';
import './i18n';

/** `POST /simulate/drivers` — engine reruns (one-at-a-time sensitivity) and the cited factors. */
export interface DriversResponse {
  method: string;
  step_pct: number;
  baseline: { low: number; central: number; high: number; unit: string };
  drivers: {
    input: 'tree_count' | 'survival_rate' | 'area_hectares';
    value: number;
    value_low: number;
    value_high: number;
    central_low: number;
    central_high: number;
    change_pct_low: number | null;
    change_pct_high: number | null;
  }[];
  factors: {
    name: string;
    value: unknown;
    unit: string | null;
    source: string | null;
    verification_status: string | null;
  }[];
  weakest_evidence: string[];
  notes: string[];
  certified: false;
}

const STATUS_TONE: Record<string, string> = {
  verified: 'bg-mint text-forest-deep',
  assumption: 'bg-blue-tint text-blue-text',
  pending: 'bg-amber-tint text-amber-text',
  unverified: 'bg-amber-tint text-amber-text',
};

function shortValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(' – ');
  if (typeof value === 'number') return String(Number(value.toFixed(4)));
  return String(value ?? '—');
}

/**
 * "Why this number?" — explainable AI without an AI model: what moves the
 * estimate (engine reruns) and every factor it is built from, with source and
 * verification status. Nothing here is computed in the browser.
 */
export function ExplainPanel({ body, locale }: { body: SimulateBody | null; locale: string }) {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ['simulate-drivers', body],
    queryFn: ({ signal }) =>
      request<DriversResponse>('/simulate/drivers', { method: 'POST', body, signal }),
    enabled: Boolean(body && body.tree_count > 0),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const data = query.data;
  const span = Math.max(
    1,
    ...(data?.drivers ?? []).flatMap((d) => [
      Math.abs(d.change_pct_low ?? 0),
      Math.abs(d.change_pct_high ?? 0),
    ]),
  );
  const fmtPct = (v: number | null) =>
    v === null
      ? '—'
      : `${v > 0 ? '+' : ''}${formatNumber(v, locale, { maximumFractionDigits: 1 })} %`;
  const fmtInput = (input: string, v: number) =>
    input === 'survival_rate'
      ? `${formatNumber(v * 100, locale, { maximumFractionDigits: 1 })} %`
      : input === 'area_hectares'
        ? `${formatNumber(v, locale, { maximumFractionDigits: 2 })} ha`
        : formatNumber(v, locale, { maximumFractionDigits: 0 });

  return (
    <section className="card flex flex-col gap-4 p-5" aria-labelledby="xai-title">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mint text-forest-deep">
          <Lightbulb size={17} aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1">
          <h2 id="xai-title" className="m-0 text-[15px]">
            {t('land3d.xaiTitle')}
          </h2>
          <p className="m-0 text-[12.5px] leading-relaxed text-ink-2">
            {t('land3d.xaiMethod', { step: data?.step_pct ?? 10 })}
          </p>
        </div>
      </div>

      {query.isError && (
        <p className="m-0 text-[12.5px] text-amber-text">{t('land3d.xaiOffline')}</p>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="m-0 text-[13px]">{t('land3d.xaiDrivers')}</h3>
              <span className="font-mono text-[12px] text-ink-2">
                {t('land3d.xaiBaseline', {
                  value: formatNumber(data.baseline.central, locale, { maximumFractionDigits: 2 }),
                })}
              </span>
            </div>
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {data.drivers.map((d) => {
                const low = d.change_pct_low ?? 0;
                const high = d.change_pct_high ?? 0;
                return (
                  <li key={d.input} className="flex flex-col gap-1">
                    <span className="flex justify-between text-[12.5px]">
                      <span className="font-semibold text-ink">
                        {t(`land3d.xaiInputs.${d.input}`)}
                      </span>
                      <span className="font-mono text-[11.5px] text-muted">
                        {fmtInput(d.input, d.value_low)} → {fmtInput(d.input, d.value_high)}
                      </span>
                    </span>
                    {/* Tornado bar: centre line = today's estimate */}
                    <div className="relative h-5 rounded-[6px] bg-ground" aria-hidden="true">
                      <span className="absolute inset-y-0 left-1/2 w-px bg-line" />
                      <span
                        className="absolute inset-y-1 rounded-l-[4px] bg-amber/70"
                        style={{
                          right: '50%',
                          width: `${(Math.abs(Math.min(low, high, 0)) / span) * 50}%`,
                        }}
                      />
                      <span
                        className="absolute inset-y-1 rounded-r-[4px] bg-forest/70"
                        style={{ left: '50%', width: `${(Math.max(low, high, 0) / span) * 50}%` }}
                      />
                    </div>
                    <span className="flex justify-between font-mono text-[11.5px] text-ink-2">
                      <span>{fmtPct(d.change_pct_low)}</span>
                      <span>{fmtPct(d.change_pct_high)}</span>
                    </span>
                  </li>
                );
              })}
            </ul>
            {data.weakest_evidence.length > 0 && (
              <p className="m-0 rounded-[10px] bg-amber-tint px-3 py-2 text-[12px] leading-relaxed text-amber-text">
                {t('land3d.xaiWeakest', { list: data.weakest_evidence.join(', ') })}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <h3 className="m-0 text-[13px]">{t('land3d.xaiFactors')}</h3>
            <div className="max-h-[300px] overflow-auto rounded-[10px] border border-line">
              <table className="w-full border-collapse text-[12px]">
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-left text-[11px] text-muted">
                    <th className="border-b border-line px-2.5 py-1.5 font-medium">
                      {t('land3d.xaiCols.name')}
                    </th>
                    <th className="border-b border-line px-2.5 py-1.5 text-right font-medium">
                      {t('land3d.xaiCols.value')}
                    </th>
                    <th className="border-b border-line px-2.5 py-1.5 font-medium">
                      {t('land3d.xaiCols.status')}
                    </th>
                    <th className="border-b border-line px-2.5 py-1.5 font-medium">
                      {t('land3d.xaiCols.source')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.factors.map((f, i) => (
                    <tr
                      key={`${f.name}-${i}`}
                      className="border-b border-line last:border-0 align-top"
                    >
                      <td className="px-2.5 py-1.5 font-mono text-[11.5px] text-ink">{f.name}</td>
                      <td className="whitespace-nowrap px-2.5 py-1.5 text-right font-mono">
                        {shortValue(f.value)}{' '}
                        <span className="text-muted">
                          {f.unit && f.unit.length < 14 ? f.unit : ''}
                        </span>
                      </td>
                      <td className="px-2.5 py-1.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${STATUS_TONE[f.verification_status ?? ''] ?? 'bg-ground text-ink-2'}`}
                        >
                          {t(`land3d.xaiStatus.${f.verification_status}`, {
                            defaultValue: f.verification_status ?? '—',
                          })}
                        </span>
                      </td>
                      <td className="px-2.5 py-1.5 text-[11.5px] leading-snug text-ink-2">
                        {f.source}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
