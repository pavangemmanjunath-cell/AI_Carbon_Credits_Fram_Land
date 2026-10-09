import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '@/i18n';
import { useUiStore } from '@/store/uiStore';

export function LanguageSelect({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  const language = useUiStore((s) => s.language);
  const setLanguage = useUiStore((s) => s.setLanguage);
  return (
    <label className="flex items-center gap-2 text-[13px] text-muted">
      {!compact && <span className="hidden sm:inline">{t('app.language')}</span>}
      <select
        aria-label={t('app.language')}
        value={language}
        onChange={(event) => setLanguage(event.target.value)}
        className="field-input h-9 w-auto pr-7 text-[13px] text-ink"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}
