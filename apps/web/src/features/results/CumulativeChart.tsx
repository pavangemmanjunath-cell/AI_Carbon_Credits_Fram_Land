import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import type { AnnualPoint } from '@/types/api';

interface Props {
  series: AnnualPoint[];
  locale: string;
}

export function CumulativeChart({ series, locale }: Props) {
  const { t } = useTranslation();
  const data = series.map((p) => ({ year: p.year, band: [p.cum_low, p.cum_high] as [number, number], central: p.cum_central }));
  const thisYear = new Date().getFullYear();
  const fmt = (v: number) => new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(v);
  return (
    <figure className="card m-0 flex flex-col gap-2 p-5">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[15px] font-semibold">{t('results.cumulativeTitle')}</span>
        <span className="text-[12px] text-muted">{t('results.cumulativeSubtitle')}</span>
      </figcaption>
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#EEF2EF" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#5E6E65', fontFamily: 'IBM Plex Mono' }} tickLine={false} axisLine={{ stroke: '#D8E0DA' }} />
            <YAxis tick={{ fontSize: 11, fill: '#5E6E65', fontFamily: 'IBM Plex Mono' }} tickLine={false} axisLine={false} tickFormatter={fmt} width={48} />
            <Tooltip
              formatter={(value, name) => {
                if (Array.isArray(value)) return [`${fmt(Number(value[0]))} – ${fmt(Number(value[1]))} tCO₂e`, t('cards.range')];
                return [`${fmt(Number(value))} tCO₂e`, name === 'central' ? t('results.central') : String(name)];
              }}
              labelFormatter={(label) => String(label)}
              contentStyle={{ borderRadius: 10, border: '1px solid #D8E0DA', fontSize: 12 }}
            />
            <Area type="monotone" dataKey="band" stroke="none" fill="#CFE6D6" fillOpacity={1} isAnimationActive={false} />
            <Line type="monotone" dataKey="central" stroke="#1E6B41" strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <ReferenceLine x={thisYear} stroke="#B7791F" strokeDasharray="4 4" label={{ value: `${t('results.today')} · ${thisYear}`, position: 'insideTopLeft', fontSize: 11, fill: '#8A4B08' }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
