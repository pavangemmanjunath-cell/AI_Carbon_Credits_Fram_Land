import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import de from './de.json';
import en from './en.json';
import es from './es.json';
import fr from './fr.json';
import hi from './hi.json';
import kn from './kn.json';
import { mapEnv } from '@/config/mapEnv';

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Français' },
  { code: 'es', label: 'Español' },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]['code'];

function initialLanguage(): string {
  try {
    const persisted = localStorage.getItem('carboncreditbuy-ui');
    if (persisted) {
      const parsed = JSON.parse(persisted) as { state?: { language?: string } };
      const code = parsed.state?.language;
      if (code && LANGUAGES.some((l) => l.code === code)) return code;
    }
  } catch {
    /* storage unavailable (private mode, tests) */
  }
  return mapEnv.defaultLanguage;
}

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
      kn: { translation: kn },
      de: { translation: de },
      fr: { translation: fr },
      es: { translation: es },
    },
    lng: initialLanguage(),
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    returnEmptyString: false,
  });
}

export default i18n;
