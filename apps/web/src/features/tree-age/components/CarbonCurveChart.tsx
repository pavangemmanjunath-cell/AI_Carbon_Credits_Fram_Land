import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { unitLabel } from '@/lib/format';
import {
  curveToChartData,
  formatAxisNumber,
  formatCarbon,
  niceTicks,
  pointAtAge,
  sampleCurve,
  type ChartPoint,
} from '../logic/treeAgeLogic';
import type { CarbonRange, CurvePoint } from '../types';

// Same colours as the other charts in the app (tokens.css: forest, amber, line).
const COLOURS = {
  band: '#CFE6D6',
  line: '#1E6B41',
  today: '#B7791F',
  todayText: '#8A4B08',
  grid: '#EEF2EF',
  axis: '#5E6E65',
  frame: '#D8E0DA',
};
const TICK = { fontSize: 11, fill: COLOURS.axis, fontFamily: 'IBM Plex Mono' };

interface CarbonCurveChartProps {
  curve: CurvePoint[];
  /** The trees' age today: where the dashed line stands. */
  age: number;
  /** The headline value, drawn as the dot on the dashed line. */
  storedNow: CarbonRange;
  /** `tier2-girth` when the person measured a trunk. */
  method: string;
  locale: string;
  updating?: boolean;
}

interface TipProps {
  active?: boolean;
  point: ChartPoint | undefined;
  locale: string;
}

export function CurveTip({ active, point, locale }: TipProps) {
  const { t } = useTranslation();
  if (!active || !point) return null;
  return (
    <div
      className="rounded-[10px] border bg-surface p-3 text-[12px] leading-relaxed shadow-float"
      style={{ borderColor: COLOURS.frame }}
    >
      <p className="m-0 font-semibold text-ink">{t('treeAge.chartAge', { count: point.age })}</p>
      <p className="m-0 text-ink-2">
        {t('treeAge.chartStored')}:{' '}
        <strong className="font-mono text-ink">{formatCarbon(point.stored, locale)}</strong> tCO₂e
        <span className="text-muted">
          {' '}
          ({formatCarbon(point.low, locale)} – {formatCarbon(point.high, locale)})
        </span>
      </p>
      <p className="m-0 text-ink-2">
        {t('treeAge.chartAnnual')}:{' '}
        <strong className="font-mono text-ink">{formatCarbon(point.annual, locale)}</strong>{' '}
        tCO₂e/yr
      </p>
    </div>
  );
}

/**
 * The one chart: carbon stored as the trees age, with the low–high band and a dashed line at the
 * trees' age today. Hovering shows the stored carbon and the yearly removal at that age; a
 * hidden table gives screen-reader users the same numbers.
 */
export function CarbonCurveChart({
  curve,
  age,
  storedNow,
  method,
  locale,
  updating = false,
}: CarbonCurveChartProps) {
  const { t } = useTranslation();
  const data = curveToChartData(curve);
  const here = pointAtAge(data, age);
  const markerY = storedNow.central;
  const measured = method === 'tier2-girth';

  // Round axis labels (0, 50, 100, 150), and the "Today" label on the side with room for it.
  const maxAge = data.length > 0 ? data[data.length - 1].age : 0;
  const yScale = niceTicks(
    Math.max(markerY, storedNow.high, ...data.map((point) => point.high)),
    4,
  );
  const xTicks = niceTicks(maxAge, 5, true).ticks.filter((tick) => tick <= maxAge);
  const todayPosition = age <= maxAge * 0.15 ? 'insideTopLeft' : 'insideTopRight';

  const summary = t('treeAge.chartLabel', {
    age,
    central: formatCarbon(storedNow.central, locale),
    low: formatCarbon(storedNow.low, locale),
    high: formatCarbon(storedNow.high, locale),
  });

  return (
    <figure
      aria-busy={updating}
      className={`card m-0 flex flex-col gap-3 p-4 transition-opacity md:p-5 ${updating ? 'opacity-60' : ''}`}
    >
      <figcaption className="flex flex-col gap-1">
        <span className="font-heading text-[17px] font-semibold text-ink">
          {t('treeAge.chartTitle')}
        </span>
        <span className="text-[13px] leading-snug text-muted">{t('treeAge.chartHelp')}</span>
      </figcaption>

      {data.length > 1 ? (
        <>
          <div role="img" aria-label={summary} className="h-[250px] w-full md:h-[290px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 16, right: 20, bottom: 18, left: 4 }}>
                <CartesianGrid stroke={COLOURS.grid} vertical={false} />
                <XAxis
                  type="number"
                  dataKey="age"
                  domain={[0, maxAge]}
                  ticks={xTicks}
                  allowDecimals={false}
                  tick={TICK}
                  tickLine={false}
                  axisLine={{ stroke: COLOURS.frame }}
                  label={{
                    value: t('treeAge.chartAxisAge'),
                    position: 'insideBottom',
                    offset: -10,
                    fontSize: 11,
                    fill: COLOURS.axis,
                  }}
                />
                <YAxis
                  domain={[0, yScale.top]}
                  ticks={yScale.ticks}
                  tick={TICK}
                  tickLine={false}
                  axisLine={false}
                  width={52}
                  tickFormatter={(value: number) =>
                    formatAxisNumber(value, locale, yScale.decimals)
                  }
                />
                <Tooltip
                  cursor={{ stroke: COLOURS.today, strokeDasharray: '3 3' }}
                  content={(props) => (
                    <CurveTip
                      active={props.active}
                      locale={locale}
                      point={(props.payload?.[0]?.payload as ChartPoint | undefined) ?? undefined}
                    />
                  )}
                />
                <Area
                  type="monotone"
                  dataKey="band"
                  stroke="none"
                  fill={COLOURS.band}
                  fillOpacity={1}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="stored"
                  stroke={COLOURS.line}
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 4 }}
                  isAnimationActive={false}
                />
                <ReferenceLine
                  x={age}
                  stroke={COLOURS.today}
                  strokeDasharray="4 4"
                  label={{
                    value: t('treeAge.chartToday'),
                    position: todayPosition,
                    fontSize: 11,
                    fill: COLOURS.todayText,
                  }}
                />
                <ReferenceDot
                  x={age}
                  y={markerY}
                  r={5}
                  fill={COLOURS.line}
                  stroke="#FFFFFF"
                  strokeWidth={2}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <ul className="m-0 flex list-none flex-wrap items-center gap-x-5 gap-y-1.5 p-0 text-[12px] text-ink-2">
            <li className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="h-[3px] w-5 rounded-full"
                style={{ background: COLOURS.line }}
              />
              {t('treeAge.legendCentral')}
            </li>
            <li className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="h-3 w-5 rounded-[3px]"
                style={{ background: COLOURS.band }}
              />
              {t('treeAge.legendBand')}
            </li>
            <li className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="h-0 w-5 border-t-2 border-dashed"
                style={{ borderColor: COLOURS.today }}
              />
              {t('treeAge.legendToday')}
            </li>
            <li className="text-muted">{t('treeAge.legendUnit')}</li>
          </ul>

          {measured && (
            <p className="m-0 rounded-[10px] bg-blue-tint px-3 py-2 text-[12.5px] leading-snug text-blue-text">
              {t('treeAge.chartGirthNote')}
            </p>
          )}

          <div className="sr-only">
            <table>
              <caption>{t('treeAge.chartTable')}</caption>
              <thead>
                <tr>
                  <th scope="col">{t('treeAge.tableAge')}</th>
                  <th scope="col">
                    {t('treeAge.tableStored')} ({unitLabel(storedNow.unit)})
                  </th>
                  <th scope="col">{t('treeAge.tableRange')}</th>
                  <th scope="col">{t('treeAge.tableAnnual')}</th>
                </tr>
              </thead>
              <tbody>
                {sampleCurve(data, here?.age ?? age).map((point) => (
                  <tr key={point.age}>
                    <th scope="row">{point.age}</th>
                    <td>{formatCarbon(point.stored, locale)}</td>
                    <td>
                      {formatCarbon(point.low, locale)} – {formatCarbon(point.high, locale)}
                    </td>
                    <td>{formatCarbon(point.annual, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="m-0 py-10 text-center text-[13.5px] text-muted">{t('treeAge.chartEmpty')}</p>
      )}
    </figure>
  );
}
