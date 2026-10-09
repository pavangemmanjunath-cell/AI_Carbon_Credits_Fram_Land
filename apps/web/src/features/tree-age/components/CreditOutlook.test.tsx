import '../i18n';
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import i18n from '@/i18n';
import { assessmentFixture } from '../fixtures';
import type { CreditOutlook as Outlook } from '../types';
import { CreditOutlook } from './CreditOutlook';

const existing = assessmentFixture({ age: 30 }).credit_outlook;
const planning = assessmentFixture({ age: 0 }).credit_outlook;

afterEach(async () => {
  // Unmount first, so switching the language back does not update a mounted component.
  cleanup();
  await i18n.changeLanguage('en');
});

describe('CreditOutlook', () => {
  it('says in one sentence what the rules mean for trees that already stand', () => {
    render(<CreditOutlook outlook={existing} age={30} />);
    const banner = screen.getByRole('region', { name: 'Credit outlook' });
    expect(within(banner).getByText(existing.summary)).toBeVisible();
  });

  it('always adds that an estimate is not a carbon credit', () => {
    render(<CreditOutlook outlook={existing} age={30} />);
    expect(
      screen.getByText('Scenario estimate only. This is not an issued carbon credit.'),
    ).toBeVisible();
  });

  it('keeps the reminder even when the API gave no sentence', () => {
    const empty: Outlook = { existing_trees: '', summary: '', based_on_rule_ids: [] };
    render(<CreditOutlook outlook={empty} age={30} />);
    expect(
      screen.getByText('Scenario estimate only. This is not an issued carbon credit.'),
    ).toBeVisible();
  });

  it('uses the API sentence for planned trees too, in English', () => {
    render(<CreditOutlook outlook={planning} age={0} />);
    expect(screen.getByText(planning.summary)).toBeVisible();
  });

  it('gives other languages a translated sentence for the same verdict', async () => {
    await i18n.changeLanguage('de');
    render(<CreditOutlook outlook={existing} age={30} />);
    expect(
      screen.getByText(/Bereits stehende Bäume bringen in der Regel keine Entnahmezertifikate/),
    ).toBeVisible();
    expect(screen.queryByText(existing.summary)).not.toBeInTheDocument();
    expect(
      screen.getByText('Nur Szenarioschätzung. Dies ist kein ausgestelltes CO₂-Zertifikat.'),
    ).toBeVisible();
  });

  it('gives other languages a planning sentence when the trees are only planned', async () => {
    await i18n.changeLanguage('fr');
    render(<CreditOutlook outlook={planning} age={0} />);
    expect(screen.queryByText(planning.summary)).not.toBeInTheDocument();
    const banner = screen.getByRole('region', { name: 'Perspective de crédits' });
    expect(
      within(banner).getByText(/Une nouvelle plantation ne peut donner des crédits/),
    ).toBeVisible();
    expect(
      within(banner).getByText(
        'Estimation de scénario uniquement. Ce n’est pas un crédit carbone émis.',
      ),
    ).toBeVisible();
  });

  it('falls back to the API sentence for a verdict it has no translation for', async () => {
    await i18n.changeLanguage('de');
    const odd: Outlook = {
      existing_trees: 'under-review',
      summary: 'A verdict this page does not know.',
      based_on_rule_ids: [],
    };
    render(<CreditOutlook outlook={odd} age={30} />);
    expect(screen.getByText('A verdict this page does not know.')).toBeVisible();
  });

  it('gives each verdict its own look', () => {
    const looks = new Set<string>();
    for (const verdict of ['not-eligible', 'conditional', 'eligible']) {
      const { container, unmount } = render(
        <CreditOutlook
          outlook={{ existing_trees: verdict, summary: verdict, based_on_rule_ids: [] }}
          age={30}
        />,
      );
      looks.add(container.querySelector('section')?.className ?? '');
      unmount();
    }
    // "eligible" shares the calm green of a planned tree; the other two must differ from it.
    expect(looks.size).toBe(3);
  });
});
