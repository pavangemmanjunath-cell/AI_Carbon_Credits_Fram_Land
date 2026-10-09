/**
 * Attribution text for the map's own attribution bar. Attribution strings are
 * licence obligations and are never translated.
 */

/** Data layers the workspace always draws from (see docs/licensing/DATA_LICENSES.md). */
export function dataAttributions(year = new Date().getFullYear()): string[] {
  return ['ESA WorldCover 2021 © ESA (CC BY 4.0)', `Contains modified Copernicus Sentinel data ${year}`];
}

const ENTITIES: Record<string, string> = { '&copy;': '©', '&amp;': '&', '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };

/** Style sources may carry HTML attribution; the bar renders plain text only. */
export function plainAttribution(html: string | null | undefined): string {
  if (!html) return '';
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&[a-z#0-9]+;/gi, (entity) => ENTITIES[entity.toLowerCase()] ?? ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

interface StyleLike {
  sources?: Record<string, { attribution?: string } | unknown>;
}

/** Attribution of every basemap source in a MapLibre style (our own `atlas-` sources excluded). */
export function styleAttributions(style: StyleLike | null | undefined, ownPrefix = 'atlas-'): string[] {
  if (!style?.sources) return [];
  const out: string[] = [];
  for (const [id, source] of Object.entries(style.sources)) {
    if (id.startsWith(ownPrefix)) continue;
    const text = plainAttribution((source as { attribution?: string })?.attribution);
    if (text) out.push(text);
  }
  return out;
}

/** Basemap first, then the active imagery, then the data layers; duplicates removed. */
export function attributionParts(input: { basemap: string[]; imagery?: string | null; data: string[] }): string[] {
  const seen = new Set<string>();
  const parts: string[] = [];
  for (const raw of [...input.basemap, input.imagery ?? '', ...input.data]) {
    const text = plainAttribution(raw);
    const key = text.toLowerCase();
    if (!text || seen.has(key)) continue;
    seen.add(key);
    parts.push(text);
  }
  return parts;
}
