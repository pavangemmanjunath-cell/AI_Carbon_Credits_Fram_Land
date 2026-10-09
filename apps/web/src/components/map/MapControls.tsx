import type { ReactNode } from 'react';
import { Crosshair, Minus, Plus } from 'lucide-react';
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
    { id: 'satellite', label: t('map.viewSatellite'), disabled: !satelliteAvailable, title: satelliteNote },
  ];
  return (
    <div role="radiogroup" aria-label={t('map.viewSwitch')} className="float-control flex w-fit gap-0.5 p-0.5">
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
