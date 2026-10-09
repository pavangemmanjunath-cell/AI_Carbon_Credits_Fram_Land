import type { ReactElement } from 'react';
import type * as Recharts from 'recharts';
import { act, cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '@/i18n';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { speciesFixture } from './fixtures';
import TreeAgePage from './TreeAgePage';
import {
  assessBodies,
  assessmentFor,
  jsonResponse,
  mockApi,
  problemResponse,
  renderWithProviders,
  restoreFetch,
  treeAgeRoutes,
} from './testUtils';
import type { TreeAgeRequestBody } from './types';

// jsdom has no layout, so the responsive wrapper would give the chart no size and draw nothing.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof Recharts>();
  const { cloneElement } = await import('react');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children as ReactElement<{ width: number; height: number }>, {
        width: 800,
        height: 290,
      }),
  };
});

const NOT_A_CREDIT = 'Scenario estimate only. This is not an issued carbon credit.';

const defaultBody: TreeAgeRequestBody = {
  country: 'IN',
  subdivision: null,
  setting: 'farm',
  species_id: 'mango',
  age_years: 30,
  tree_count: 25,
  girth_cm: null,
};

beforeEach(() => {
  localStorage.clear();
  resetUiStore();
});

afterEach(async () => {
  restoreFetch();
  // Unmount first, so resetting the language does not update a mounted page.
  cleanup();
  await i18n.changeLanguage('en');
  resetUiStore();
});

/** Waits in real time (the page's own 400 ms pause) without leaving updates outside `act`. */
async function sleep(ms: number) {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
  });
}

async function results() {
  return screen.findByRole('region', { name: 'Results' });
}

describe('TreeAgePage: the first look', () => {
  it('works out 30-year-old farm trees in India straight away and shows three values', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);

    const region = await results();
    const cards = within(region).getAllByRole('article');
    expect(cards.map((c) => c.getAttribute('aria-label'))).toEqual([
      'Carbon stored now',
      'Carbon removed per year now',
      'Age class',
    ]);
    expect(within(cards[0]).getByText('72')).toBeVisible();
    expect(within(cards[1]).getByText('3.3')).toBeVisible();
    expect(within(cards[2]).getByText('Mature')).toBeVisible();

    // One request, with exactly what the person sees, and nothing about a place.
    expect(assessBodies(calls)).toEqual([defaultBody]);
    expect(Object.keys(assessBodies(calls)[0]).sort()).toEqual([
      'age_years',
      'country',
      'girth_cm',
      'setting',
      'species_id',
      'subdivision',
      'tree_count',
    ]);
  });

  it('has one heading, one chart and one credit-outlook banner', async () => {
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    await results();

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1, name: 'Tree age' })).toBeVisible();
    expect(screen.getAllByText('Carbon stored as the trees age')).toHaveLength(1);
    expect(
      screen.getAllByRole('img', { name: /^Chart of carbon stored by tree age/ }),
    ).toHaveLength(1);
    expect(screen.getAllByRole('region', { name: 'Credit outlook' })).toHaveLength(1);
  });

  it('says in one sentence that trees like these do not usually earn credits, and that this is not a credit', async () => {
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    const banner = await screen.findByRole('region', { name: 'Credit outlook' });
    expect(
      within(banner).getByText(/Trees that already stand usually do not earn removal credits/),
    ).toBeVisible();
    expect(within(banner).getByText(NOT_A_CREDIT)).toBeVisible();
  });

  it('lists the rules that apply, with the others one click away', async () => {
    const user = userEvent.setup();
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);

    expect(
      await screen.findByRole('heading', { level: 2, name: 'Rules for trees of this age' }),
    ).toBeVisible();
    expect(
      screen.getByRole('article', { name: 'Karnataka Preservation of Trees Act, 1976' }),
    ).toBeVisible();
    expect(screen.queryByText('Haryana Pran Vayu Devta Pension Scheme')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Other rules in India (2)' }));
    expect(
      screen.getByRole('article', { name: 'Haryana Pran Vayu Devta Pension Scheme' }),
    ).toBeVisible();
    expect(screen.getByRole('article', { name: 'Portland heritage trees' })).toBeVisible();
  });

  it('ends with the disclaimer, word for word', async () => {
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    await results();
    const disclaimer = screen.getByText(/^Screening information only — not legal advice\./);
    expect(disclaimer).toHaveTextContent(`${NOT_A_CREDIT}`);
  });

  it('links back to the workspace', async () => {
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    expect(await screen.findByRole('link', { name: 'Workspace' })).toHaveAttribute('href', '/app');
  });

  it('shows a loading placeholder until the first answer arrives', async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    mockApi(
      treeAgeRoutes({
        'POST /tree-age/assess': async ({ body }) => {
          await gate;
          return jsonResponse(assessmentFor(body as TreeAgeRequestBody));
        },
      }),
    );
    renderWithProviders(<TreeAgePage />);
    expect(await screen.findByRole('status', { name: 'Calculating…' })).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Results' })).not.toBeInTheDocument();
    release();
    await results();
    expect(screen.queryByRole('status', { name: 'Calculating…' })).not.toBeInTheDocument();
  });
});

describe('TreeAgePage: the address bar is the memory', () => {
  it('reads every input from the link and sends exactly that', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(
      <TreeAgePage />,
      '/app/tree-age?country=US&subdivision=US-OR&species=pecan&age=80&trees=120&girth=95&setting=urban',
    );
    await results();

    expect(assessBodies(calls)).toEqual([
      {
        country: 'US',
        subdivision: 'US-OR',
        setting: 'urban',
        species_id: 'pecan',
        age_years: 80,
        tree_count: 120,
        girth_cm: 95,
      },
    ]);
    expect(screen.getByLabelText('Country')).toHaveValue('US');
    expect(screen.getByLabelText('State or region')).toHaveValue('US-OR');
    expect(screen.getByRole('radio', { name: 'Town or city' })).toBeChecked();
    expect(screen.getByLabelText('Species')).toHaveValue('pecan');
    expect(screen.getByLabelText('Age of the trees (years)')).toHaveValue('80');
    expect(screen.getByLabelText('Number of trees')).toHaveValue('120');
    expect(screen.getByLabelText(/Trunk girth at chest height/)).toHaveValue('95');
    expect(within(await results()).getByText('Veteran')).toBeVisible();
  });

  it('falls back to sensible values for a link that makes no sense', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(
      <TreeAgePage />,
      '/app/tree-age?country=ZZ&age=old&trees=abc&girth=1&setting=moon&species=!!',
    );
    await results();
    expect(assessBodies(calls)).toEqual([defaultBody]);
  });

  it('pulls numbers that are out of range back inside it', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />, '/app/tree-age?age=999&trees=0&girth=99999');
    await results();
    expect(assessBodies(calls)).toEqual([
      { ...defaultBody, age_years: 300, tree_count: 1, girth_cm: null },
    ]);
  });

  it('never sends a state that the API does not list for the country', async () => {
    const { calls } = mockApi(
      treeAgeRoutes({
        'GET /tree-age/rules': async () => {
          // The species list arrives first, so the page has to wait for this one.
          await new Promise((resolve) => setTimeout(resolve, 60));
          return jsonResponse({
            version: '1',
            updated: '2026-10-05',
            disclaimer: '',
            age_classes: [],
            subdivision_label: 'State',
            subdivisions: [{ code: 'IN-KA', name: 'Karnataka', type: 'state' }],
          });
        },
      }),
    );
    renderWithProviders(<TreeAgePage />, '/app/tree-age?country=IN&subdivision=IN-ZZ');
    await results();
    await sleep(200);
    expect(assessBodies(calls)).toEqual([defaultBody]);
    expect(screen.getByLabelText('State or region')).toHaveValue('');
  });

  it('sends a state that the API does list', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />, '/app/tree-age?country=IN&subdivision=IN-KA');
    await results();
    expect(assessBodies(calls)).toEqual([{ ...defaultBody, subdivision: 'IN-KA' }]);
    expect(screen.getByLabelText('State or region')).toHaveValue('IN-KA');
  });

  it('writes each change into the link at once, in one place, without piling up history', async () => {
    const user = userEvent.setup();
    mockApi(treeAgeRoutes());
    const { router } = renderWithProviders(<TreeAgePage />);
    await results();

    await user.click(screen.getByRole('radio', { name: 'Forest' }));
    await user.selectOptions(screen.getByLabelText('Species'), 'teak');
    await user.selectOptions(screen.getByLabelText('State or region'), 'IN-KA');
    const box = screen.getByLabelText('Number of trees');
    await user.clear(box);
    await user.type(box, '60');

    const search = new URLSearchParams(router.state.location.search);
    expect(Object.fromEntries(search)).toEqual({
      country: 'IN',
      subdivision: 'IN-KA',
      setting: 'forest',
      species: 'teak',
      age: '30',
      trees: '60',
    });
  });

  it('copies a link that reproduces the page', async () => {
    const user = userEvent.setup();
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />, '/app/tree-age?age=45&trees=10');
    await results();
    await user.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(await navigator.clipboard.readText()).toBe(
      `${window.location.origin}/app/tree-age?country=IN&setting=farm&species=mango&age=45&trees=10`,
    );
    expect(await screen.findByText('Link copied')).toBeVisible();
  });
});

describe('TreeAgePage: changing the trees', () => {
  it('waits for a dragged slider to settle, asks once, and keeps the old numbers meanwhile', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    const { router } = renderWithProviders(<TreeAgePage />);
    await results();
    const slider = screen.getByLabelText('Age of the trees, slider');

    for (const age of [31, 45, 60, 77])
      fireEvent.change(slider, { target: { value: String(age) } });

    // The link and the box follow the finger at once ...
    expect(router.state.location.search).toContain('age=77');
    expect(screen.getByLabelText('Age of the trees (years)')).toHaveValue('77');
    // ... the numbers on screen are the old ones, and say they are being replaced ...
    expect(screen.getByRole('status')).toHaveTextContent('Updating…');
    expect(screen.getByText('Mature')).toBeVisible();
    expect(assessBodies(calls)).toHaveLength(1);

    // ... and one request goes out once the finger stops.
    await waitFor(() => expect(assessBodies(calls)).toHaveLength(2), { timeout: 3000 });
    expect(assessBodies(calls).map((b) => b.age_years)).toEqual([30, 77]);
    expect(await screen.findByText('Veteran')).toBeVisible();
    await waitFor(() => expect(screen.getByRole('status')).toBeEmptyDOMElement());
    await sleep(500);
    expect(assessBodies(calls)).toHaveLength(2);
  });

  it('moves the dashed line on the chart to the new age', async () => {
    mockApi(treeAgeRoutes());
    const { container } = renderWithProviders(<TreeAgePage />);
    await results();
    const x = () =>
      container.querySelector('.recharts-reference-line line')?.getAttribute('x1') ?? '';
    const before = x();
    expect(before).not.toBe('');
    fireEvent.change(screen.getByLabelText('Age of the trees, slider'), {
      target: { value: '70' },
    });
    await screen.findByText('Old');
    expect(x()).not.toBe(before);
  });

  it('sends the typed number of trees and shows more carbon for more trees', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    await results();
    const box = screen.getByLabelText('Number of trees');
    await user.clear(box);
    await user.type(box, '250');
    await waitFor(() => expect(assessBodies(calls)).toHaveLength(2), { timeout: 3000 });
    expect(assessBodies(calls)[1]).toMatchObject({ tree_count: 250 });
    // Ten times the trees, ten times the carbon (72 → 720).
    await waitFor(() =>
      expect(
        within(screen.getByRole('region', { name: 'Results' })).getByText('720'),
      ).toBeVisible(),
    );
  });

  it('treats age 0 as planning: no trunk, a note, and nothing stored yet', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />, '/app/tree-age?age=0&girth=80');
    const region = await results();

    expect(assessBodies(calls)).toEqual([{ ...defaultBody, age_years: 0, girth_cm: null }]);
    expect(screen.getByLabelText(/Trunk girth at chest height/)).toBeDisabled();
    expect(screen.getAllByText('Planning new trees').length).toBeGreaterThan(0);
    expect(screen.getByText(/You are planning new trees, so nothing is stored yet/)).toBeVisible();
    expect(within(region).getByText('Young')).toBeVisible();
    expect(
      screen.getByText(/Newly planted trees can earn removal credits only through a project/),
    ).toBeVisible();
  });

  it('sends a trunk girth once the trees stand, and says the numbers come from the measurement', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(
      treeAgeRoutes({
        'POST /tree-age/assess': ({ body }) => {
          const request = body as TreeAgeRequestBody;
          const answer = assessmentFor(request);
          return jsonResponse({
            ...answer,
            carbon: {
              ...answer.carbon,
              method: request.girth_cm === null ? 'tier1-age' : 'tier2-girth',
            },
          });
        },
      }),
    );
    renderWithProviders(<TreeAgePage />);
    await results();
    expect(screen.queryByText(/Your trunk measurement gives the numbers above/)).toBeNull();
    await user.type(screen.getByLabelText(/Trunk girth at chest height/), '95');
    await waitFor(() => expect(assessBodies(calls)).toHaveLength(2), { timeout: 3000 });
    expect(assessBodies(calls)[1]).toMatchObject({ age_years: 30, girth_cm: 95 });
    expect(await screen.findByText(/Your trunk measurement gives the numbers above/)).toBeVisible();
  });

  it('does not ask the API again for a typo, and keeps the results on screen', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);
    await results();
    const box = screen.getByLabelText('Age of the trees (years)');
    await user.clear(box);
    await user.type(box, '4x');
    expect(screen.getByText('Use digits only.')).toBeVisible();
    // The results stay on screen while the typo is being fixed ...
    expect(screen.getByRole('region', { name: 'Results' })).toBeVisible();
    // ... "4" was a good number, so it was sent once things settled; "4x" never was.
    expect(await screen.findByText('Young', undefined, { timeout: 3000 })).toBeVisible();
    await sleep(500);
    expect(assessBodies(calls).map((b) => b.age_years)).toEqual([30, 4]);
  });

  it('resets the state and the species list when the country changes', async () => {
    const user = userEvent.setup();
    const { calls } = mockApi(treeAgeRoutes());
    const { router } = renderWithProviders(<TreeAgePage />, '/app/tree-age?subdivision=IN-KA');
    await results();
    expect(screen.getByLabelText('State or region')).toHaveValue('IN-KA');

    await user.selectOptions(screen.getByLabelText('Country'), 'US');

    await waitFor(() => expect(assessBodies(calls)).toHaveLength(2), { timeout: 3000 });
    expect(assessBodies(calls)[1]).toMatchObject({
      country: 'US',
      subdivision: null,
      species_id: 'black_walnut',
    });
    expect(calls.some((c) => c.path === '/species' && c.search.includes('country=US'))).toBe(true);
    expect(screen.getByLabelText('Species')).toHaveValue('black_walnut');
    const states = await within(screen.getByLabelText('State or region')).findAllByRole('option');
    expect(states.map((o) => o.textContent)).toEqual(['Not sure', 'California', 'Oregon']);
    expect(router.state.location.search).toContain('country=US');
    expect(router.state.location.search).not.toContain('subdivision');
  });

  it('works for an EU country that has no list of states', async () => {
    const { calls } = mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />, '/app/tree-age?country=FR');
    await results();
    expect(assessBodies(calls)[0]).toMatchObject({ country: 'FR', subdivision: null });
    expect(screen.queryByLabelText('State or region')).not.toBeInTheDocument();
  });
});

describe('TreeAgePage: when something goes wrong', () => {
  it('tells people to start the API when it is not running', async () => {
    const user = userEvent.setup();
    const down = () => {
      throw new TypeError('Failed to fetch');
    };
    mockApi({
      'GET /species': down,
      'GET /demo/species.json': () => jsonResponse(speciesFixture),
      'GET /tree-age/rules': down,
      'POST /tree-age/assess': down,
    });
    renderWithProviders(<TreeAgePage />);

    expect(await screen.findByText('The tree-age check needs the API')).toBeVisible();
    expect(screen.getByText('make api').tagName).toBe('CODE');
    expect(screen.queryByRole('region', { name: 'Results' })).not.toBeInTheDocument();
    // The questions can still be answered while waiting.
    expect(screen.getByLabelText('Number of trees')).toBeEnabled();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('The tree-age check needs the API')).toBeVisible();
  });

  it('shows the API’s own problem detail, and recovers on "Try again"', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    mockApi(
      treeAgeRoutes({
        'POST /tree-age/assess': ({ body }) => {
          attempts += 1;
          if (attempts === 1) {
            return problemResponse(422, 'Unprocessable Entity', 'species_id: unknown species');
          }
          return jsonResponse(assessmentFor(body as TreeAgeRequestBody));
        },
      }),
    );
    renderWithProviders(<TreeAgePage />);

    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText('Unprocessable Entity')).toBeVisible();
    expect(within(alert).getByText('species_id: unknown species')).toBeVisible();
    expect(within(alert).getByText('HTTP 422')).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Results' })).not.toBeInTheDocument();

    await user.click(within(alert).getByRole('button', { name: 'Try again' }));
    await results();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it('says so when a country has no species yet, and asks nothing', async () => {
    const { calls } = mockApi(treeAgeRoutes({ 'GET /species': () => jsonResponse([]) }));
    renderWithProviders(<TreeAgePage />);
    expect(
      await screen.findByText('No tree species are listed for this country yet.'),
    ).toBeVisible();
    expect(assessBodies(calls)).toEqual([]);
    expect(screen.queryByRole('status', { name: 'Calculating…' })).not.toBeInTheDocument();
  });

  it('shows the problem instead of the old numbers when a later request fails', async () => {
    const user = userEvent.setup();
    let attempts = 0;
    mockApi(
      treeAgeRoutes({
        'POST /tree-age/assess': ({ body }) => {
          attempts += 1;
          return attempts === 1
            ? jsonResponse(assessmentFor(body as TreeAgeRequestBody))
            : problemResponse(500, 'Internal Server Error', 'Something broke');
        },
      }),
    );
    renderWithProviders(<TreeAgePage />);
    await results();
    const box = screen.getByLabelText('Number of trees');
    await user.clear(box);
    await user.type(box, '80');
    expect(
      await screen.findByText('Internal Server Error', undefined, { timeout: 3000 }),
    ).toBeVisible();
    // Results from a failed request are never shown as if they were current.
    expect(screen.queryByRole('region', { name: 'Results' })).not.toBeInTheDocument();
  });
});

describe('TreeAgePage: other languages', () => {
  it('translates the page, the outlook sentence and the not-a-credit sentence', async () => {
    await i18n.changeLanguage('de');
    useUiStore.getState().setLanguage('de');
    mockApi(treeAgeRoutes());
    renderWithProviders(<TreeAgePage />);

    const region = await screen.findByRole('region', { name: 'Ergebnisse' });
    expect(screen.getByRole('heading', { level: 1, name: 'Baumalter' })).toBeVisible();
    // German decimal comma.
    expect(within(region).getByText('3,3')).toBeVisible();
    const banner = screen.getByRole('region', { name: 'Zertifikat-Aussichten' });
    expect(
      within(banner).getByText(
        /Bereits stehende Bäume bringen in der Regel keine Entnahmezertifikate/,
      ),
    ).toBeVisible();
    expect(
      within(banner).getByText(
        'Nur Szenarioschätzung. Dies ist kein ausgestelltes CO₂-Zertifikat.',
      ),
    ).toBeVisible();
    // The API's English disclaimer is replaced by the translated one.
    expect(screen.queryByText(/Screening information only/)).not.toBeInTheDocument();
    expect(
      screen.getByText(/^Nur Orientierungsinformationen, keine Rechtsberatung\./),
    ).toBeVisible();
  });
});
