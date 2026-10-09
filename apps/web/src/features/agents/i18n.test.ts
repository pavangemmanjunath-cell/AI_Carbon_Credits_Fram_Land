import i18n from '@/i18n';
import { describe, expect, it } from 'vitest';
import { agentsBundles } from './i18n';

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

const languages = Object.keys(agentsBundles) as (keyof typeof agentsBundles)[];
const english = flatten(agentsBundles.en as unknown as Tree);

describe('agents page strings', () => {
  it('are registered for all six app languages', () => {
    expect(languages).toEqual(['en', 'hi', 'kn', 'de', 'fr', 'es']);
    for (const language of languages) {
      expect(i18n.getResource(language, 'translation', 'agentsPage.title'), language).toBeTruthy();
      expect(i18n.getResource(language, 'translation', 'agentsPage.run'), language).toBeTruthy();
    }
  });

  it('keep the shared app strings next to them', () => {
    expect(i18n.getResource('en', 'translation', 'app')).toBeTruthy();
  });

  for (const language of languages.filter((l) => l !== 'en')) {
    it(`give ${language} every key, with the same placeholders and tags as English`, () => {
      const translated = flatten(agentsBundles[language] as unknown as Tree);
      expect(Object.keys(translated).sort()).toEqual(Object.keys(english).sort());
      for (const [key, text] of Object.entries(translated)) {
        expect(text.trim(), `${language}:${key}`).not.toBe('');
        expect(placeholders(text), `${language}:${key}`).toEqual(placeholders(english[key]));
        expect(tags(text), `${language}:${key}`).toEqual(tags(english[key]));
      }
    });
  }

  it('carry the not-a-credit sentence in every language, each translated', () => {
    const notCredit = languages.map((l) => (agentsBundles[l] as { notCredit: string }).notCredit);
    expect(new Set(notCredit).size).toBe(languages.length);
    expect(agentsBundles.en.notCredit).toBe(
      'Scenario estimate only. This is not an issued carbon credit.',
    );
  });

  it('write the command to start the API the same way everywhere', () => {
    for (const language of languages) {
      expect(agentsBundles[language].offlineBody, language).toContain('<code>make api</code>');
    }
  });
});
