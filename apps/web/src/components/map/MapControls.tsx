import { useEffect, useState, type ReactNode } from 'react';
import { Clock, Crosshair, Minus, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { MapViewMode } from '@/store/uiStore';

export function IconButton({
  label,
  onClick,
  active,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={`flex h-9 w-9 items-center justify-center rounded-[8px] ${active ? 'bg-mint text-forest-deep' : 'text-ink-2 hover:bg-ground'} disabled:opacity-40`}
    >
      {children}
    </button>
  );
}

interface ViewProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onLocate: () => void;
}

/** Zoom and "use my location" — the map is flat and north-up (no tilt, no 3D). */
export function ViewControls({ onZoomIn, onZoomOut, onLocate }: ViewProps) {
  const { t } = useTranslation();
  return (
    <div className="float-control flex w-11 flex-col gap-0.5 p-1">
      <IconButton label={t('map.zoomIn')} onClick={onZoomIn}>
        <Plus size={18} aria-hidden="true" />
      </IconButton>
      <IconButton label={t('map.zoomOut')} onClick={onZoomOut}>
        <Minus size={18} aria-hidden="true" />
      </IconButton>
      <IconButton label={t('map.locate')} onClick={onLocate}>
        <Crosshair size={18} aria-hidden="true" />
      </IconButton>
    </div>
  );
}

interface SwitchProps {
  value: MapViewMode;
  onChange: (value: MapViewMode) => void;
  satelliteAvailable: boolean;
  /** Shown as a tooltip on "Satellite": the provider name, or why it is unavailable. */
  satelliteNote?: string;
}

/** "Map | Satellite" segmented switch in the map's bottom-left corner. */
export function MapViewSwitch({ value, onChange, satelliteAvailable, satelliteNote }: SwitchProps) {
  const { t } = useTranslation();
  const options: { id: MapViewMode; label: string; disabled: boolean; title?: string }[] = [
    { id: 'map', label: t('map.viewMap'), disabled: false },
    {
      id: 'satellite',
      label: t('map.viewSatellite'),
      disabled: !satelliteAvailable,
      title: satelliteNote,
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label={t('map.viewSwitch')}
      className="float-control flex w-fit gap-0.5 p-0.5"
    >
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="radio"
          aria-checked={value === option.id}
          disabled={option.disabled}
          title={option.title}
          onClick={() => onChange(option.id)}
          className={`h-8 rounded-[8px] px-3 text-[13px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
            value === option.id ? 'bg-panel-dark text-white' : 'text-ink-2 hover:bg-ground'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Live clock (the viewer's local time), next to the zoom and locate buttons. */
export function LiveClock({ locale }: { locale: string }) {
  const { t } = useTranslation();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 15_000);
    return () => window.clearInterval(timer);
  }, []);
  const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(now);
  return (
    <div
      className="float-control flex items-center gap-1.5 px-2.5 py-1.5 text-[12px]"
      title={t('map.localTime')}
    >
      <span className="h-2 w-2 rounded-full bg-forest" aria-hidden="true" />
      <Clock size={14} aria-hidden="true" className="text-forest-deep" />
      <time dateTime={now.toISOString()} className="font-mono font-semibold text-ink">
        {time}
      </time>
      <span className="sr-only">{t('map.localTime')}</span>
    </div>
  );
}
