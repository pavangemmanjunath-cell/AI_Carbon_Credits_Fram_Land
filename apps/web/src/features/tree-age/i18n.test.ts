import i18n from '@/i18n';
import { describe, expect, it } from 'vitest';
import { treeAgeBundles } from './i18n';

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') out[path] = value;
    else Object.assign(out, flatten(value, path));
  }
  return out;
}

function placeholders(text: string): string[] {
  return [...text.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map((m) => m[1]).sort();
}

function tags(text: string): string[] {
  return [...text.matchAll(/<\/?(\w+)>/g)].map((m) => m[0]).sort();
}

const languages = Object.keys(treeAgeBundles) as (keyof typeof treeAgeBundles)[];
const english = flatten(treeAgeBundles.en as unknown as Tree);

describe('tree-age page strings', () => {
  it('are registered for all six app languages', () => {
    expect(languages).toEqual(['en', 'hi', 'kn', 'de', 'fr', 'es']);
    for (const language of languages) {
      expect(i18n.getResource(language, 'translation', 'treeAge.title'), language).toBeTruthy();
      expect(i18n.getResource(language, 'translation', 'treeAge.notCredit'), language).toBeTruthy();
    }
  });

  it('keep the shared app strings next to them', () => {
    expect(i18n.getResource('en', 'translation', 'app')).toBeTruthy();
  });

  for (const language of languages.filter((l) => l !== 'en')) {
    it(`give ${language} every key, with the same placeholders and tags as English`, () => {
      const translated = flatten(treeAgeBundles[language] as unknown as Tree);
      expect(Object.keys(translated).sort()).toEqual(Object.keys(english).sort());
      for (const [key, text] of Object.entries(translated)) {
        expect(text.trim(), `${language}:${key}`).not.toBe('');
        expect(placeholders(text), `${language}:${key}`).toEqual(placeholders(english[key]));
        expect(tags(text), `${language}:${key}`).toEqual(tags(english[key]));
      }
    });
  }

  it('carry the not-a-credit sentence in every language, each translated', () => {
    const notCredit = languages.map((l) => (treeAgeBundles[l] as { notCredit: string }).notCredit);
    expect(new Set(notCredit).size).toBe(languages.length);
    expect(treeAgeBundles.en.notCredit).toBe(
      'Scenario estimate only. This is not an issued carbon credit.',
    );
  });

  it('keep the not-a-credit sentence at the end of the disclaimer, in every language', () => {
    for (const language of languages) {
      const bundle = treeAgeBundles[language];
      expect(bundle.disclaimer.endsWith(bundle.notCredit), language).toBe(true);
    }
  });

  it('write the command to start the API the same way everywhere', () => {
    for (const language of languages) {
      expect(treeAgeBundles[language].offlineBody, language).toContain('<code>make api</code>');
    }
  });

  it('name the four age classes and the six outcomes in every language', () => {
    for (const language of languages) {
      const bundle = treeAgeBundles[language];
      expect(Object.keys(bundle.ageClass).sort(), language).toEqual([
        'mature',
        'old',
        'unknown',
        'veteran',
        'young',
      ]);
      expect(Object.keys(bundle.outcome).sort(), language).toEqual([
        'conditional',
        'eligible',
        'not-applicable',
        'not-eligible',
        'payment',
        'protected',
        'unknown',
      ]);
    }
  });

  it('give each outcome its own word within a language, so the word alone tells them apart', () => {
    for (const language of languages) {
      const words = Object.entries(treeAgeBundles[language].outcome)
        .filter(([key]) => key !== 'unknown')
        .map(([, word]) => word);
      // "Payment" is also a rule category, but within the outcomes each word is used once.
      expect(new Set(words).size, language).toBe(words.length);
    }
  });

  it('pick the singular and the plural form for the age', () => {
    const en = i18n.getFixedT('en');
    expect(en('treeAge.ageYears', { count: 1 })).toBe('1 year');
    expect(en('treeAge.ageYears', { count: 30 })).toBe('30 years');
    const de = i18n.getFixedT('de');
    expect(de('treeAge.ageYears', { count: 1 })).toBe('1 Jahr');
    expect(de('treeAge.ageYears', { count: 30 })).toBe('30 Jahre');
  });
});
