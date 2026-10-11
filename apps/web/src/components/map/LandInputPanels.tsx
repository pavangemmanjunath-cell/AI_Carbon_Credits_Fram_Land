import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Circle,
  Crosshair,
  Keyboard,
  MapPin,
  PenLine,
  Pentagon,
  Spline,
  Square,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { formatLatLon } from '@/lib/coordinates';
import { errorMessage } from '@/lib/errors';
import { formatArea, formatInteger, formatNumber } from '@/lib/format';
import {
  defaultInputAreaUnit,
  fromLineBody,
  fromPointBody,
  PIN_DEFAULT_SIZE,
  plotRequestFor,
  TREE_LINE_DEFAULTS,
  validatePinSize,
  validateTreeLineSettings,
  type InputAreaUnit,
  type NewPlotRequest,
  type ShapeOption,
} from '@/lib/landInput';
import { useGeometryFromLine, useGeometryFromPoint, useParseCoordinates } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import type { LatLon, LineStringGeometry, PointGeometry, PolygonGeometry } from '@/types/api';

export type PreviewGeometry = PolygonGeometry | PointGeometry | LineStringGeometry;

function PanelFrame({
  title,
  icon: Icon,
  onClose,
  children,
  footer,
}: {
  title: string;
  icon: LucideIcon;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <section aria-label={title} className="float-control flex flex-col gap-3 p-3.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="m-0 flex items-center gap-2 text-[15px]">
          <Icon size={17} className="text-forest" aria-hidden="true" />
          {title}
        </h3>
        <button
          type="button"
          onClick={onClose}
          aria-label={t('app.close')}
          className="flex h-8 w-8 items-center justify-center rounded-full text-ink-2 hover:bg-ground"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>
      {children}
      {footer && <div className="flex flex-wrap justify-end gap-2">{footer}</div>}
    </section>
  );
}

function OfflineNote() {
  const { t } = useTranslation();
  const offline = useUiStore((s) => s.apiStatus === 'offline');
  if (!offline) return null;
  return (
    <p className="m-0 rounded-[8px] bg-blue-tint px-2.5 py-1.5 text-[12px] text-blue-text">
      {t('map.offlineCalc')}
    </p>
  );
}

function Problem({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="m-0 text-[12px] text-amber-text">
      {children}
    </p>
  );
}

/** Number field + "acres | hectares" toggle for "How big is your land?". */
export function AreaSizeInput({
  id,
  value,
  onValue,
  unit,
  onUnit,
}: {
  id: string;
  value: string;
  onValue: (v: string) => void;
  unit: InputAreaUnit;
  onUnit: (u: InputAreaUnit) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-ink">
        {t('map.howBig')}
      </label>
      <div className="flex gap-2">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={0}
          step="any"
          value={value}
          onChange={(e) => onValue(e.target.value)}
          className="field-input h-10 w-24 flex-none text-[15px] font-semibold"
        />
        <div
          role="radiogroup"
          aria-label={t('map.areaUnit')}
          className="flex flex-1 gap-0.5 rounded-[10px] border border-line bg-ground p-0.5"
        >
          {(['acre', 'hectare'] as const).map((u) => (
            <button
              key={u}
              type="button"
              role="radio"
              aria-checked={unit === u}
              onClick={() => onUnit(u)}
              className={`h-[34px] flex-1 rounded-[8px] text-[13px] font-semibold ${unit === u ? 'bg-surface text-forest-deep shadow-sm' : 'text-ink-2'}`}
            >
              {t(u === 'acre' ? 'units.acres' : 'units.hectares')}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function sizeProblemText(
  problem: ReturnType<typeof validatePinSize>,
  t: (k: string) => string,
): string | null {
  return problem ? t(`map.size_${problem}`) : null;
}

/** Shared state for a size field whose default unit follows the region (acres IN/US, hectares EU). */
function useAreaSize(country: string) {
  const preference = useUiStore((s) => s.areaUnit);
  const [unit, setUnit] = useState<InputAreaUnit>(() => defaultInputAreaUnit(country, preference));
  const [text, setText] = useState(String(PIN_DEFAULT_SIZE));
  const value = text.trim() === '' ? NaN : Number(text);
  return { unit, setUnit, text, setText, value, problem: validatePinSize(value, unit) };
}

// ─── Boundary / Edit ─────────────────────────────────────────────────────────

const DRAW_ICONS = {
  boundary: Pentagon,
  edit: Pentagon,
  pen: PenLine,
  rectangle: Square,
  circle: Circle,
} as const;

export function DrawHintPanel({
  mode,
  onApply,
  onCancel,
}: {
  mode: 'boundary' | 'edit' | ShapeOption;
  onApply?: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const hint =
    mode === 'edit'
      ? t('map.editingHint')
      : mode === 'boundary'
        ? t('map.finishDrawing')
        : t(`map.finish_${mode}`);
  return (
    <PanelFrame
      title={t(`map.tool_${mode}`)}
      icon={DRAW_ICONS[mode]}
      onClose={onCancel}
      footer={
        <>
          <Button size="sm" variant="secondary" onClick={onCancel}>
            {t('app.cancel')}
          </Button>
          {mode === 'edit' && onApply && (
            <Button size="sm" onClick={onApply}>
              {t('app.apply')}
            </Button>
          )}
        </>
      }
    >
      <p className="m-0 text-[13px] leading-relaxed text-ink-2">{hint}</p>
    </PanelFrame>
  );
}

// ─── Tree line ───────────────────────────────────────────────────────────────

interface TreeLineProps {
  line: LineStringGeometry | null;
  locale: string;
  onCreate: (request: NewPlotRequest) => void;
  onRedraw: () => void;
  onCancel: () => void;
  onPreview: (geometry: PreviewGeometry | null) => void;
}

export function TreeLinePanel({
  line,
  locale,
  onCreate,
  onRedraw,
  onCancel,
  onPreview,
}: TreeLineProps) {
  const { t } = useTranslation();
  const [spacing, setSpacing] = useState<string>(String(TREE_LINE_DEFAULTS.spacing_m));
  const [width, setWidth] = useState<string>(String(TREE_LINE_DEFAULTS.width_m));
  const problem = validateTreeLineSettings(Number(spacing), Number(width));
  const body = useMemo(
    () => (line && !problem ? fromLineBody(line, Number(spacing), Number(width)) : null),
    [line, spacing, width, problem],
  );
  const query = useGeometryFromLine(useDebouncedValue(body, 300));
  const result = line ? query.data : undefined;
  useEffect(() => {
    onPreview(result?.geometry ?? null);
  }, [result, onPreview]);

  return (
    <PanelFrame
      title={t('map.tool_treeLine')}
      icon={Spline}
      onClose={onCancel}
      footer={
        line ? (
          <>
            <Button size="sm" variant="secondary" onClick={onRedraw}>
              {t('map.redraw')}
            </Button>
            <Button
              size="sm"
              disabled={!result || Boolean(problem) || query.isFetching}
              onClick={() =>
                result &&
                onCreate(plotRequestFor('tree-line', result.geometry, result.suggested_tree_count))
              }
            >
              {t('map.createPlot')}
            </Button>
          </>
        ) : (
          <Button size="sm" variant="secondary" onClick={onCancel}>
            {t('app.cancel')}
          </Button>
        )
      }
    >
      {!line ? (
        <p className="m-0 text-[13px] leading-relaxed text-ink-2">{t('map.treeLineHint')}</p>
      ) : (
        <>
          <dl className="m-0 grid grid-cols-2 gap-2">
            <div className="rounded-[10px] bg-ground px-3 py-2">
              <dt className="text-[11px] text-muted">{t('map.lineLength')}</dt>
              <dd className="m-0 font-mono text-[15px] font-semibold">
                {result
                  ? `${formatNumber(result.length_m, locale, { maximumFractionDigits: 0 })} m`
                  : '—'}
              </dd>
            </div>
            <div className="rounded-[10px] bg-ground px-3 py-2">
              <dt className="text-[11px] text-muted">{t('map.suggestedTrees')}</dt>
              <dd className="m-0 font-mono text-[15px] font-semibold">
                {result ? formatInteger(result.suggested_tree_count, locale) : '—'}
              </dd>
            </div>
          </dl>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="flex flex-col gap-1 text-[12px] text-ink-2">
              <label htmlFor="tree-line-spacing">
                {t('map.spacing')}
                <span className="sr-only"> (m)</span>
              </label>
              <span className="flex items-center gap-1.5">
                <input
                  id="tree-line-spacing"
                  type="number"
                  min={0.5}
                  max={50}
                  step={0.5}
                  value={spacing}
                  onChange={(e) => setSpacing(e.target.value)}
                  className="field-input h-9"
                />
                <span className="text-muted" aria-hidden="true">
                  m
                </span>
              </span>
            </div>
            <div className="flex flex-col gap-1 text-[12px] text-ink-2">
              <label htmlFor="tree-line-width">
                {t('map.stripWidth')}
                <span className="sr-only"> (m)</span>
              </label>
              <span className="flex items-center gap-1.5">
                <input
                  id="tree-line-width"
                  type="number"
                  min={1}
                  max={50}
                  step={0.5}
                  value={width}
                  onChange={(e) => setWidth(e.target.value)}
                  className="field-input h-9"
                />
                <span className="text-muted" aria-hidden="true">
                  m
                </span>
              </span>
            </div>
          </div>
          {problem && <Problem>{t(`map.line_${problem}`)}</Problem>}
          {query.error && <Problem>{errorMessage(query.error, t)}</Problem>}
          <p className="m-0 text-[12px] text-muted">{t('map.treeLineNote')}</p>
          <OfflineNote />
        </>
      )}
    </PanelFrame>
  );
}

// ─── Pin + size ──────────────────────────────────────────────────────────────

interface PinProps {
  pin: LatLon | null;
  country: string;
  locale: string;
  onUseCentre: () => void;
  onCreate: (request: NewPlotRequest) => void;
  onCancel: () => void;
  onPreview: (geometry: PreviewGeometry | null) => void;
}

export function PinSizePanel({
  pin,
  country,
  locale,
  onUseCentre,
  onCreate,
  onCancel,
  onPreview,
}: PinProps) {
  const { t } = useTranslation();
  const areaUnit = useUiStore((s) => s.areaUnit);
  const size = useAreaSize(country);
  const body = useMemo(
    () => (pin && !size.problem ? fromPointBody(pin, size.value, size.unit) : null),
    [pin, size.problem, size.value, size.unit],
  );
  const query = useGeometryFromPoint(useDebouncedValue(body, 300));
  const result = pin ? query.data : undefined;
  useEffect(() => {
    onPreview(
      result?.geometry ?? (pin ? { type: 'Point', coordinates: [pin.lon, pin.lat] } : null),
    );
  }, [result, pin, onPreview]);
  const problem = sizeProblemText(size.problem, t);

  return (
    <PanelFrame
      title={t('map.tool_pin')}
      icon={MapPin}
      onClose={onCancel}
      footer={
        <>
          <Button size="sm" variant="secondary" onClick={onCancel}>
            {t('app.cancel')}
          </Button>
          <Button
            size="sm"
            disabled={!pin || !result || Boolean(size.problem) || query.isFetching}
            onClick={() => result && onCreate(plotRequestFor('pin', result.geometry))}
          >
            {t('map.createPlot')}
          </Button>
        </>
      }
    >
      <p className="m-0 text-[13px] leading-relaxed text-ink-2">
        {pin ? t('map.pinPlaced', { position: formatLatLon(pin) }) : t('map.pinHint')}
      </p>
      <Button size="sm" variant="secondary" onClick={onUseCentre} className="self-start">
        <Crosshair size={15} aria-hidden="true" />
        {t('map.useCentre')}
      </Button>
      <AreaSizeInput
        id="pin-size"
        value={size.text}
        onValue={size.setText}
        unit={size.unit}
        onUnit={size.setUnit}
      />
      {problem && <Problem>{problem}</Problem>}
      {result && (
        <p className="m-0 text-[12px] text-ink-2">
          {t('map.squareOf', {
            area: formatArea(result.area_hectares, country, locale, areaUnit).primary,
          })}
        </p>
      )}
      {query.error && <Problem>{errorMessage(query.error, t)}</Problem>}
      <p className="m-0 text-[12px] text-muted">{t('map.pinNote')}</p>
      <OfflineNote />
    </PanelFrame>
  );
}

// ─── Coordinates ─────────────────────────────────────────────────────────────

interface CoordinatesProps {
  country: string;
  locale: string;
  onCreate: (request: NewPlotRequest) => void;
  onCancel: () => void;
  onPreview: (geometry: PreviewGeometry | null) => void;
}

export function CoordinatesPanel({
  country,
  locale,
  onCreate,
  onCancel,
  onPreview,
}: CoordinatesProps) {
  const { t } = useTranslation();
  const areaUnit = useUiStore((s) => s.areaUnit);
  const [text, setText] = useState('');
  const debouncedText = useDebouncedValue(text, 400);
  const parse = useParseCoordinates(debouncedText);
  const parsed = text.trim() && debouncedText.trim() ? parse.data : undefined;
  const size = useAreaSize(country);
  const single = parsed?.kind === 'point' ? parsed.points[0] : null;
  const pointBody = useMemo(
    () => (single && !size.problem ? fromPointBody(single, size.value, size.unit) : null),
    [single, size.problem, size.value, size.unit],
  );
  const square = useGeometryFromPoint(useDebouncedValue(pointBody, 300));
  const squareResult = single ? square.data : undefined;
  const polygon =
    parsed?.kind === 'polygon' && parsed.geometry?.type === 'Polygon' ? parsed.geometry : null;

  useEffect(() => {
    if (polygon) onPreview(polygon);
    else if (single)
      onPreview(squareResult?.geometry ?? { type: 'Point', coordinates: [single.lon, single.lat] });
    else onPreview(null);
  }, [polygon, single, squareResult, onPreview]);

  const canCreate = polygon
    ? true
    : Boolean(single && squareResult && !size.problem && !square.isFetching);
  const create = () => {
    if (polygon) onCreate(plotRequestFor('coordinates', polygon));
    else if (squareResult) onCreate(plotRequestFor('pin', squareResult.geometry));
  };
  const sizeProblem = sizeProblemText(size.problem, t);

  return (
    <PanelFrame
      title={t('map.tool_coordinates')}
      icon={Keyboard}
      onClose={onCancel}
      footer={
        <>
          <Button size="sm" variant="secondary" onClick={onCancel}>
            {t('app.cancel')}
          </Button>
          <Button size="sm" disabled={!canCreate || parse.isFetching} onClick={create}>
            {t('map.createPlot')}
          </Button>
        </>
      }
    >
      <label htmlFor="coordinates-text" className="text-[13px] leading-snug text-ink-2">
        {t('map.coordinatesLabel')}
      </label>
      <textarea
        id="coordinates-text"
        rows={4}
        spellCheck={false}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={'13.2923, 77.5384'}
        className="field-input h-auto min-h-[96px] resize-y py-2 font-mono text-[13px]"
      />
      {parsed?.kind === 'polygon' && parsed.area_hectares != null && (
        <p className="m-0 text-[13px] font-medium text-forest-deep">
          {t('map.coordinatesPolygon', {
            count: parsed.points.length,
            area: formatArea(parsed.area_hectares, country, locale, areaUnit).primary,
          })}
        </p>
      )}
      {single && (
        <>
          <p className="m-0 text-[13px] text-ink-2">
            {t('map.coordinatesOnePoint', { position: formatLatLon(single) })}
          </p>
          <AreaSizeInput
            id="coordinates-size"
            value={size.text}
            onValue={size.setText}
            unit={size.unit}
            onUnit={size.setUnit}
          />
          {sizeProblem && <Problem>{sizeProblem}</Problem>}
        </>
      )}
      {parsed && parsed.warnings.length > 0 && (
        <ul className="m-0 flex list-disc flex-col gap-0.5 pl-4 text-[12px] text-amber-text">
          {parsed.warnings.slice(0, 4).map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      {parse.error && <Problem>{errorMessage(parse.error, t)}</Problem>}
      {square.error && single && <Problem>{errorMessage(square.error, t)}</Problem>}
      <OfflineNote />
    </PanelFrame>
  );
}
