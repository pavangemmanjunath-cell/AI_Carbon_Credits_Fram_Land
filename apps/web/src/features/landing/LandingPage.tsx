import { useState } from 'react';
import { ArrowRight, Bot, Calculator, Globe2, MapPin, Search, ShieldCheck, Sprout, TreePine, Vegan } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';
import { LogoMark, Wordmark } from '@/components/brand/Logo';
import { buttonClass } from '@/components/ui/buttonStyles';
import { LanguageSelect } from '@/components/ui/LanguageSelect';
import { OfflineBanner } from '@/components/ui/OfflineBanner';
import { REGIONS } from '@/config/regions';
import { useUiStore } from '@/store/uiStore';
import { MapPreview } from './MapPreview';

const DATA_BADGES = [
  { label: 'ESA WorldCover 10 m', note: 'CC BY 4.0', tone: 'bg-vegetation' },
  { label: 'Copernicus Sentinel-2 L2A', note: 'free, full and open', tone: 'bg-water' },
  { label: 'USDA NASS Quick Stats', note: 'US public data', tone: 'bg-amber' },
  { label: 'data.gov.in', note: 'GODL-India', tone: 'bg-amber' },
  { label: '© OpenStreetMap contributors', note: 'ODbL · self-hosted PMTiles', tone: 'bg-muted' },
  { label: 'MapLibre GL JS', note: 'BSD-3-Clause', tone: 'bg-muted' },
];

const DOCS = 'https://github.com/pavangemmanjunath-cell/Carbon_Credits_Fram_Land';

export default function LandingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const country = useUiStore((s) => s.country);
  const setCountry = useUiStore((s) => s.setCountry);
  const [query, setQuery] = useState('');

  const go = () => navigate(`/app?country=${country}${query.trim() ? `&q=${encodeURIComponent(query.trim())}` : ''}`);

  const steps = [
    { icon: Vegan, title: t('landing.step1Title'), text: t('landing.step1Text') },
    { icon: TreePine, title: t('landing.step2Title'), text: t('landing.step2Text') },
    { icon: Sprout, title: t('landing.step3Title'), text: t('landing.step3Text') },
    { icon: Calculator, title: t('landing.step4Title'), text: t('landing.step4Text') },
  ];

  return (
    <div className="min-h-screen bg-ground text-ink">
      <OfflineBanner />
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line bg-surface px-6 py-3.5 lg:px-12">
        <Link to="/" className="flex items-center gap-3 no-underline">
          <LogoMark size={36} />
          <Wordmark />
        </Link>
        <nav aria-label="Primary" className="hidden gap-7 text-sm font-medium text-ink-2 md:flex">
          <Link to="/app" className="hover:text-forest">{t('nav.platform')}</Link>
          <a href={`${DOCS}/blob/main/docs/architecture/carbon-engine.md`} className="hover:text-forest">{t('nav.methodology')}</a>
          <a href="#data" className="hover:text-forest">{t('nav.dataSources')}</a>
          <a href="#regions" className="hover:text-forest">{t('nav.regions')}</a>
          <a href={DOCS} className="hover:text-forest">{t('nav.github')}</a>
        </nav>
        <div className="flex items-center gap-3">
          <LanguageSelect />
          <Link to="/app" className={buttonClass('primary', 'md')}>
            {t('nav.openWorkspace')} <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </header>

      <section className="mx-auto grid w-full max-w-[1440px] grid-cols-1 items-center gap-10 px-6 py-14 lg:grid-cols-2 lg:px-12">
        <div className="flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-mint px-3 py-1.5 text-[12px] font-semibold uppercase tracking-wider text-forest-deep">
            <Globe2 size={14} aria-hidden="true" /> {t('landing.eyebrow')}
          </span>
          <h1 className="m-0 text-[40px] font-bold leading-[1.05] tracking-tight lg:text-[54px]">
            {t('landing.title')
              .split('. ')
              .map((part, i, arr) => (
                <span key={part} className={i === arr.length - 1 ? 'block text-forest' : 'block'}>
                  {part}
                  {i < arr.length - 1 ? '.' : ''}
                </span>
              ))}
          </h1>
          <p className="m-0 max-w-[560px] text-[18px] leading-relaxed text-ink-2">{t('landing.subtitle')}</p>
          <form
            className="card flex max-w-[600px] flex-col gap-3 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              go();
            }}
          >
            <div role="group" aria-label={t('settings.country')} className="flex flex-wrap gap-1.5">
              {REGIONS.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  aria-pressed={country === r.id}
                  onClick={() => setCountry(r.id)}
                  className={`h-10 rounded-[8px] border px-3.5 text-sm font-semibold ${country === r.id ? 'border-forest bg-forest text-white' : 'border-line bg-surface text-ink hover:bg-ground'}`}
                >
                  {t(`country.${r.id}`)} · {r.id}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="flex h-12 flex-[1_1_280px] items-center gap-2.5 rounded-[10px] border border-line bg-ground px-3.5">
                <Search size={18} className="text-muted" aria-hidden="true" />
                <span className="sr-only">{t('map.searchLabel')}</span>
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('landing.searchPlaceholder')}
                  className="w-full bg-transparent text-[15px] outline-none"
                />
              </label>
              <button type="submit" className={buttonClass('dark', 'lg')}>
                <MapPin size={18} aria-hidden="true" /> {t('landing.locateMyLand')}
              </button>
            </div>
            <p className="m-0 flex items-center gap-2 text-[13px] text-muted">
              <ShieldCheck size={16} className="text-forest" aria-hidden="true" />
              {t('landing.trustLine')}
            </p>
          </form>
        </div>
        <MapPreview />
      </section>

      <section aria-label={t('landing.fourStepsTitle')} className="mx-auto w-full max-w-[1440px] px-6 pb-12 lg:px-12">
        <div className="mb-5 flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="m-0 text-[24px]">{t('landing.fourStepsTitle')}</h2>
          <span className="text-sm text-muted">{t('landing.fourStepsSubtitle')}</span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <article key={title} className="card flex flex-col gap-2.5 p-5">
              <span className="flex h-10 w-10 items-center justify-center rounded-[10px] bg-mint text-forest-deep">
                <Icon size={20} aria-hidden="true" />
              </span>
              <span className="font-mono text-[12px] text-muted">0{i + 1}</span>
              <h3 className="m-0 text-[17px]">{title}</h3>
              <p className="m-0 text-sm leading-relaxed text-ink-2">{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-surface">
        <div className="mx-auto w-full max-w-[1440px] px-6 py-12 lg:px-12">
          <h2 className="m-0 text-[24px]">{t('landing.threeNumbersTitle')}</h2>
          <p className="mb-5 mt-1.5 max-w-[760px] text-[15px] text-ink-2">{t('landing.threeNumbersSubtitle')}</p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <article className="rounded-[14px] border border-line bg-ground p-5">
              <span className="eyebrow text-forest-deep">{t('landing.environmentalBenefit')}</span>
              <p className="big-number my-2 text-[34px]">
                11.0 <span className="text-[15px] font-medium text-muted">tCO₂e / yr</span>
              </p>
              <p className="m-0 font-mono text-[13px] text-ink-2">low 7.7 · high 14.3 · confidence medium</p>
              <p className="mb-0 mt-2 text-sm text-ink-2">{t('landing.environmentalBenefitText')}</p>
            </article>
            <article className="rounded-[14px] border border-line bg-ground p-5">
              <span className="eyebrow text-forest-deep">{t('landing.indicativeValue')}</span>
              <p className="big-number my-2 text-[34px]">
                ₹12,122 <span className="text-[15px] font-medium text-muted">reference / yr</span>
              </p>
              <p className="m-0 font-mono text-[13px] text-ink-2">low ₹5,290 · high ₹23,142</p>
              <p className="mb-0 mt-2 text-sm font-medium text-amber-text">{t('landing.indicativeValueText')}</p>
            </article>
            <article className="rounded-[14px] border border-line bg-ground p-5">
              <span className="eyebrow text-forest-deep">{t('landing.otherIncome')}</span>
              <p className="big-number my-2 text-[26px]">Fruit · Timber · Incentives</p>
              <p className="m-0 font-mono text-[13px] text-ink-2">from statistics and your records</p>
              <p className="mb-0 mt-2 text-sm text-ink-2">{t('landing.otherIncomeText')}</p>
            </article>
          </div>
        </div>
      </section>

      <section id="data" className="mx-auto w-full max-w-[1440px] px-6 py-12 lg:px-12">
        <h2 className="m-0 text-[24px]">{t('landing.builtOnTitle')}</h2>
        <p className="mb-4 mt-1.5 text-[15px] text-ink-2">{t('landing.builtOnSubtitle')}</p>
        <div className="flex flex-wrap gap-2.5">
          {DATA_BADGES.map((b) => (
            <span key={b.label} className="card inline-flex items-center gap-2 px-3.5 py-2.5 text-sm">
              <span className={`h-2 w-2 rounded-full ${b.tone}`} aria-hidden="true" />
              {b.label} <span className="text-muted">{b.note}</span>
            </span>
          ))}
        </div>
        <div id="regions" className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {REGIONS.map((r) => (
            <article key={r.id} className="card flex flex-col gap-2.5 p-5">
              <div className="flex items-center justify-between">
                <h3 className="m-0 text-[18px]">{t(`country.${r.id}`)}</h3>
                <span className="rounded-[6px] bg-ground px-2 py-1 font-mono text-[12px] text-ink-2">
                  {r.id} · {r.currency} · {r.units.area}
                </span>
              </div>
              <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm text-ink-2">
                {[1, 2, 3].map((n) => (
                  <li key={n} className="flex gap-2">
                    <span className="font-bold text-forest">✓</span>
                    {t(`landing.region${r.id}${n}`)}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-panel-dark text-white">
        <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 items-center gap-10 px-6 py-12 lg:grid-cols-2 lg:px-12">
          <div className="flex flex-col gap-3">
            <h2 className="m-0 text-[26px] text-white">{t('landing.privacyTitle')}</h2>
            <p className="m-0 text-[15px] leading-relaxed text-[#C9D6CD]">{t('landing.privacyText')}</p>
            <div className="mt-2 flex max-w-[460px] flex-col gap-2.5 rounded-[12px] border border-[#3A4A41] p-4">
              <span className="text-[12px] uppercase tracking-wider text-mint-on-dark">{t('settings.processing')}</span>
              <span className="flex items-start gap-2.5 text-sm">
                <ShieldCheck size={16} className="mt-0.5 shrink-0 text-plot-fill" aria-hidden="true" />
                <span>
                  <span className="font-semibold">{t('landing.modeDeterministic')}</span>
                  <span className="block text-[13px] text-[#C9D6CD]">{t('landing.modeDeterministicText')}</span>
                </span>
              </span>
              <span className="flex items-start gap-2.5 text-sm">
                <Bot size={16} className="mt-0.5 shrink-0 text-mint-on-dark" aria-hidden="true" />
                <span>
                  <span className="font-semibold">{t('landing.modeAi')}</span>
                  <span className="block text-[13px] text-[#C9D6CD]">{t('landing.modeAiText')}</span>
                </span>
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {[
              ['Public', 'Country · approximate region · anonymized sample plots · aggregated metrics', 'text-mint-on-dark'],
              ['Private', 'Exact polygon · owner identity · farm address · land documents · management records', 'text-[#F4C790]'],
              ['Provenance', 'Every number carries its dataset version, acquisition date, model version and source.', 'text-mint-on-dark'],
              ['Uncertainty', 'Low, central and high bounds on every carbon output — a tree count never equals one exact number.', 'text-mint-on-dark'],
            ].map(([title, text, tone]) => (
              <div key={title} className="flex flex-col gap-1.5 rounded-[12px] border border-[#2E3F35] bg-panel-dark-2 p-4">
                <span className={`text-[12px] uppercase tracking-wider ${tone}`}>{title}</span>
                <span className="text-sm leading-relaxed text-[#E6EFE9]">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-line bg-surface px-6 py-5 text-[13px] text-muted lg:px-12">
        <span>{t('landing.footerLicense')}</span>
        <nav aria-label="Footer" className="flex flex-wrap gap-5 text-ink-2">
          <a href={`${DOCS}/blob/main/CITATION.cff`}>{t('landing.footerCite')}</a>
          <a href={`${DOCS}/blob/main/SECURITY.md`}>{t('landing.footerSecurity')}</a>
          <a href={`${DOCS}/blob/main/GOVERNANCE.md`}>{t('landing.footerGovernance')}</a>
          <a href={`${DOCS}/blob/main/ADOPTERS.md`}>{t('landing.footerAdopters')}</a>
          <a href={`${DOCS}/blob/main/docs/licensing/ATTRIBUTION.md`}>{t('landing.footerAttribution')}</a>
        </nav>
      </footer>
    </div>
  );
}
