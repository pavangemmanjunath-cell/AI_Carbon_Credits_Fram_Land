import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { monthLabel } from '@/lib/format';
import type { Cube } from '@/types/api';
import { monthlyMeanSeries, ndviDomain, ndviTicks } from './logic/changeOverTime';

/** Small 2D card: monthly mean NDVI of the plot (one line, no KPI tiles). */
export function ChangeOverTimeCard({
  cube,
  loading,
  locale,
}: {
  cube?: Cube;
  loading?: boolean;
  locale: string;
}) {
  const { t } = useTranslation();
  const points = monthlyMeanSeries(cube);
  const domain = ndviDomain(points);
  return (
    <figure className="card m-0 flex flex-col gap-2 p-5">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[15px] font-semibold">{t('results.changeOverTime')}</span>
        <span className="text-[12px] text-muted">{t('results.changeOverTimeSubtitle')}</span>
      </figcaption>
      {points.length === 0 ? (
        loading ? (
          <span className="skeleton block h-[200px] w-full" />
        ) : (
          <p className="m-0 py-8 text-center text-sm text-muted">
            {t('results.changeOverTimeEmpty')}
          </p>
        )
      ) : (
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 36, bottom: 4, left: 0 }}>
              <CartesianGrid stroke="#EEF2EF" vertical={false} />
              <XAxis
                dataKey="month"
                tickFormatter={(m: string) => monthLabel(m, locale)}
                minTickGap={28}
                tick={{ fontSize: 11, fill: '#5E6E65', fontFamily: 'IBM Plex Mono' }}
                tickLine={false}
                axisLine={{ stroke: '#D8E0DA' }}
              />
              <YAxis
                domain={domain}
                ticks={ndviTicks(domain)}
                tickFormatter={(v: number) => v.toFixed(1)}
                tick={{ fontSize: 11, fill: '#5E6E65', fontFamily: 'IBM Plex Mono' }}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <Tooltip
                formatter={(value) => [Number(value).toFixed(2), t('results.ndviMean')]}
                labelFormatter={(label) => monthLabel(String(label), locale, 'long')}
                contentStyle={{ borderRadius: 10, border: '1px solid #D8E0DA', fontSize: 12 }}
              />
              <Line
                type="monotone"
                dataKey="mean"
                stroke="#1E6B41"
                strokeWidth={2.25}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {cube && (
        <p className="m-0 text-[11px] text-muted">
          {t('results.changeOverTimeSource', {
            source: cube.provenance.source,
            composite: cube.provenance.composite,
          })}
        </p>
      )}
    </figure>
  );
}
