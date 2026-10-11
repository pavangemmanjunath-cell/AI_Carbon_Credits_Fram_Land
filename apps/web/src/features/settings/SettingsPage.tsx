import { Bot, ChevronRight, ShieldCheck, TreePine } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { REGIONS } from '@/config/regions';
import { LANGUAGES } from '@/i18n';
import { useAgentCatalog } from '@/services/agentsApi';
import { useUiStore } from '@/store/uiStore';
import { ImagerySettings } from './ImagerySettings';

export default function SettingsPage() {
  const { t } = useTranslation();
  const s = useUiStore();
  // Read-only: the server operator decides whether an optional LLM may rephrase agent messages.
  const catalog = useAgentCatalog();
  const framework = catalog.data?.framework;
  const narration = !framework
    ? t('settings.aiNarrationUnknown')
    : framework.llm_enabled
      ? t('settings.aiNarrationOn')
      : t('settings.aiNarrationOff');
  return (
    <div className="mx-auto flex max-w-[860px] flex-col gap-4 p-5">
      <div className="flex flex-col gap-1">
        <h1 className="m-0 text-[24px]">{t('settings.title')}</h1>
        <p className="m-0 text-sm text-muted">{t('settings.saved')}</p>
      </div>
      <section className="card flex flex-col gap-4 p-5">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-semibold">{t('settings.language')}</span>
          <select
            value={s.language}
            onChange={(e) => s.setLanguage(e.target.value)}
            className="field-input h-10 max-w-xs"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <span className="text-[12px] text-muted">{t('settings.languageHint')}</span>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-semibold">{t('settings.country')}</span>
          <select
            value={s.country}
            onChange={(e) => s.setCountry(e.target.value)}
            className="field-input h-10 max-w-xs"
          >
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {t(`country.${r.id}`)}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0 text-sm">
          <legend className="mb-1 font-semibold">{t('settings.units')}</legend>
          {(['auto', 'hectare', 'acre'] as const).map((u) => (
            <label key={u} className="flex items-center gap-2.5">
              <input
                type="radio"
                name="units"
                className="h-4 w-4 accent-forest"
                checked={s.areaUnit === u}
                onChange={() => s.setAreaUnit(u)}
              />
              {t(
                u === 'auto'
                  ? 'settings.unitsAuto'
                  : u === 'hectare'
                    ? 'settings.unitsHectare'
                    : 'settings.unitsAcre',
              )}
            </label>
          ))}
        </fieldset>
        <div className="flex flex-col gap-1.5 text-sm">
          <span className="font-semibold">{t('settings.processing')}</span>
          <span className="flex items-start gap-2.5">
            <ShieldCheck size={16} className="mt-0.5 shrink-0 text-forest" aria-hidden="true" />
            <span>
              {t('landing.modeDeterministic')}
              <span className="block text-[12px] text-muted">
                {t('landing.modeDeterministicText')}
              </span>
            </span>
          </span>
          <span className="flex items-start gap-2.5">
            <Bot size={16} className="mt-0.5 shrink-0 text-forest" aria-hidden="true" />
            <span>
              {t('settings.aiNarration')}: <strong>{narration}</strong>
              <span className="block text-[12px] text-muted">{t('settings.aiNarrationHow')}</span>
            </span>
          </span>
        </div>
      </section>
      <ImagerySettings />
      <Link
        to="/app/species"
        className="card flex items-center gap-3 p-5 text-ink no-underline transition-colors hover:border-forest"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-mint text-forest-deep">
          <TreePine size={20} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-[16px] font-semibold">{t('settings.speciesReference')}</span>
          <span className="text-[13px] text-ink-2">{t('settings.speciesReferenceText')}</span>
        </span>
        <ChevronRight size={18} className="text-muted" aria-hidden="true" />
      </Link>
      <section className="card flex flex-col gap-2 p-5 text-sm leading-relaxed text-ink-2">
        <h2 className="m-0 text-[16px] text-ink">{t('settings.privacyTitle')}</h2>
        <p className="m-0">{t('settings.privacyText1')}</p>
        <p className="m-0">{t('settings.privacyText2')}</p>
        <p className="m-0">{t('settings.privacyText3')}</p>
        <p className="m-0 font-mono text-[12px] text-muted">
          {t('settings.apiStatus', { status: s.apiStatus, mode: s.apiMode ?? '—' })}
        </p>
      </section>
    </div>
  );
}
