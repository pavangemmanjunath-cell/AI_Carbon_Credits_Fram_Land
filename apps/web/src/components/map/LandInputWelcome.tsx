import { FileUp, Keyboard, MapPin, Pentagon, Spline, type LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ADD_LAND_OPTIONS, LAND_TOOL_KEYS, type AddLandOption } from '@/lib/landInput';

const ICONS: Record<AddLandOption, LucideIcon> = {
  boundary: Pentagon,
  'tree-line': Spline,
  pin: MapPin,
  coordinates: Keyboard,
  import: FileUp,
};

interface Props {
  onChoose: (option: AddLandOption) => void;
  onDismiss: () => void;
}

/** Centred "Add your land" card shown on the map while the user has no plots. */
export function LandInputWelcome({ onChoose, onDismiss }: Props) {
  const { t } = useTranslation();
  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-[rgba(243,246,242,0.55)] p-4 backdrop-blur-[2px]">
      <section
        aria-labelledby="add-land-title"
        className="card flex w-full max-w-[560px] flex-col gap-4 p-5 shadow-float"
      >
        <div className="flex flex-col gap-1">
          <h2 id="add-land-title" className="m-0 text-[20px]">
            {t('map.welcomeTitle')}
          </h2>
          <p className="m-0 text-sm text-ink-2">{t('map.welcomeText')}</p>
        </div>
        <ul className="m-0 grid list-none grid-cols-1 gap-2.5 p-0 sm:grid-cols-2">
          {ADD_LAND_OPTIONS.map((option) => {
            const Icon = ICONS[option];
            const key = LAND_TOOL_KEYS[option];
            return (
              <li key={option} className={option === 'import' ? 'sm:col-span-2' : undefined}>
                <button
                  type="button"
                  onClick={() => onChoose(option)}
                  className="flex h-full w-full items-center gap-3 rounded-[12px] border border-line bg-surface px-3.5 py-3 text-left transition-colors hover:border-forest hover:bg-mint"
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-mint text-forest-deep">
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  <span className="flex min-w-0 flex-col">
                    <span className="text-[15px] font-semibold text-ink">
                      {t(`map.tool_${key}`)}
                    </span>
                    <span className="text-[12px] leading-snug text-muted">
                      {t(`map.tool_${key}Hint`)}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <button
          type="button"
          onClick={onDismiss}
          className="self-center text-[13px] font-semibold text-forest underline-offset-2 hover:underline"
        >
          {t('map.welcomeLater')}
        </button>
      </section>
    </div>
  );
}
