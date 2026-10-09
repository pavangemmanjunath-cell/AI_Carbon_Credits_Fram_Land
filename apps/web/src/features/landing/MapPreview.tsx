import { useTranslation } from 'react-i18next';

/** Stylised (not photographic) map preview with a drawn plot — no third-party imagery. */
export function MapPreview() {
  const { t } = useTranslation();
  const trees = [
    [210, 250], [250, 225], [290, 205], [330, 210], [365, 230],
    [230, 285], [270, 265], [310, 250], [350, 265],
    [260, 310], [300, 295], [340, 300],
  ];
  return (
    <figure className="relative m-0 overflow-hidden rounded-[18px] border border-line bg-[#E7EEE4] shadow-[0_24px_48px_-32px_rgba(20,33,26,0.45)]">
      <svg viewBox="0 0 640 460" role="img" aria-label={t('landing.previewTitle')} className="block h-auto w-full">
        <rect width="640" height="460" fill="#E7EEE4" />
        <polygon points="0,60 180,20 260,90 120,160 0,150" fill="#CFE0C6" />
        <polygon points="260,90 420,40 520,110 400,190 300,170" fill="#D9CBA3" />
        <polygon points="520,110 640,80 640,230 560,250" fill="#C9D9BF" />
        <polygon points="0,150 120,160 160,260 40,300 0,280" fill="#DCCFA9" />
        <polygon points="40,300 160,260 260,330 200,440 60,420" fill="#CFE0C6" />
        <polygon points="400,190 560,250 600,360 470,420 380,330" fill="#D1CBB0" />
        <polygon points="200,440 260,330 380,330 470,420 460,460 200,460" fill="#C5D8BA" />
        <path d="M0 330 C 120 300, 180 360, 300 350 S 520 300, 640 330" stroke="#9FB0A3" strokeWidth="7" fill="none" strokeLinecap="round" />
        <path d="M560 250 C 600 300, 560 340, 600 400 S 620 440, 640 460" stroke="#7FB1E0" strokeWidth="12" fill="none" strokeLinecap="round" opacity="0.9" />
        <polygon points="160,260 300,170 400,190 380,330 260,330" fill="#2FA85B" fillOpacity="0.28" stroke="#1E6B41" strokeWidth="3" strokeLinejoin="round" />
        <g fill="#2E8B57">
          {trees.map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="7" />
          ))}
        </g>
        <g fill="#FFFFFF" stroke="#1E6B41" strokeWidth="2.5">
          {[[160, 260], [300, 170], [400, 190], [380, 330], [260, 330]].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="6" />
          ))}
        </g>
      </svg>
      <figcaption className="absolute left-4 top-4 flex flex-col gap-2">
        <span className="card inline-flex items-center gap-2 px-3 py-2 text-[13px] font-semibold shadow-float">{t('landing.previewTitle')} · {t('landing.chipArea')}</span>
        <span className="card inline-flex items-center gap-2 px-3 py-2 text-[13px] shadow-float">
          <span className="h-2.5 w-2.5 rounded-full bg-vegetation" aria-hidden="true" />
          {t('landing.chipNdvi')}
        </span>
      </figcaption>
      <div className="absolute bottom-4 right-4 flex min-w-[200px] flex-col gap-0.5 rounded-[12px] bg-panel-dark px-3.5 py-3 text-white">
        <span className="text-[11px] uppercase tracking-wider text-mint-on-dark">{t('cards.estimatedRemoval')}</span>
        <span className="big-number text-[26px]">{t('landing.chipRemoval')}</span>
        <span className="text-[12px] text-mint-on-dark">{t('cards.notCredit')}</span>
      </div>
    </figure>
  );
}
