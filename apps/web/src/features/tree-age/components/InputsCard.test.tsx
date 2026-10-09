import '../i18n';
import { useState, type ComponentProps } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { speciesFixture, subdivisionsFixture } from '../fixtures';
import type { TreeAgeInputs } from '../types';
import { InputsCard } from './InputsCard';

const start: TreeAgeInputs = {
  country: 'IN',
  subdivision: null,
  setting: 'farm',
  speciesId: 'mango',
  age: 30,
  trees: 25,
  girthCm: null,
};

type CardProps = Partial<ComponentProps<typeof InputsCard>>;

/** The page owns the inputs; the card reports changes and the page passes them back down. */
function Harness({
  initial = start,
  onPatch,
  ...props
}: CardProps & { initial?: TreeAgeInputs; onPatch: (patch: Partial<TreeAgeInputs>) => void }) {
  const [inputs, setInputs] = useState(initial);
  return (
    <InputsCard
      inputs={inputs}
      onChange={(patch) => {
        onPatch(patch);
        setInputs((previous) => ({ ...previous, ...patch }));
      }}
      species={speciesFixture}
      speciesLoading={false}
      subdivisions={subdivisionsFixture}
      locale="en-IN"
      shareUrl="http://localhost/app/tree-age?country=IN&age=30"
      {...props}
    />
  );
}

describe('InputsCard', () => {
  it('asks for the country, the state, where the trees stand, the species, the age, the number and the trunk', () => {
    render(<Harness onPatch={vi.fn()} />);
    expect(screen.getByLabelText('Country')).toHaveValue('IN');
    expect(screen.getByLabelText('State or region')).toHaveValue('');
    expect(screen.getByRole('radio', { name: 'Farm' })).toBeChecked();
    expect(screen.getByLabelText('Species')).toHaveValue('mango');
    expect(screen.getByLabelText('Age of the trees (years)')).toHaveValue('30');
    expect(screen.getByLabelText('Age of the trees, slider')).toHaveValue('30');
    expect(screen.getByLabelText('Number of trees')).toHaveValue('25');
    expect(screen.getByLabelText(/Trunk girth at chest height/)).toHaveValue('');
  });

  it('puts India and the United States first, then the EU member states', () => {
    render(<Harness onPatch={vi.fn()} />);
    const select = screen.getByLabelText('Country');
    const top = Array.from(select.querySelectorAll(':scope > option')).map((o) => o.textContent);
    expect(top).toEqual(['India', 'United States']);
    const group = select.querySelector('optgroup');
    expect(group).toHaveAttribute('label', 'European Union');
    const eu = within(group as HTMLElement)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(eu).toContain('Germany');
    expect(eu).toContain('France');
    expect(eu).toEqual([...eu].sort((a, b) => a.localeCompare(b, 'en-IN')));
  });

  it('offers the states in alphabetical order, starting with "Not sure"', () => {
    render(<Harness onPatch={vi.fn()} />);
    const options = within(screen.getByLabelText('State or region'))
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(options).toEqual(['Not sure', 'Delhi', 'Haryana', 'Karnataka']);
  });

  it('has no state box for a country the API lists no states for', () => {
    render(<Harness onPatch={vi.fn()} subdivisions={[]} />);
    expect(screen.queryByLabelText('State or region')).not.toBeInTheDocument();
  });

  it('reports each choice as a small change', async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);

    await user.selectOptions(screen.getByLabelText('Country'), 'US');
    expect(onPatch).toHaveBeenLastCalledWith({ country: 'US' });

    await user.selectOptions(screen.getByLabelText('State or region'), 'IN-KA');
    expect(onPatch).toHaveBeenLastCalledWith({ subdivision: 'IN-KA' });
    await user.selectOptions(screen.getByLabelText('State or region'), 'Not sure');
    expect(onPatch).toHaveBeenLastCalledWith({ subdivision: null });

    await user.click(screen.getByRole('radio', { name: 'Town or city' }));
    expect(onPatch).toHaveBeenLastCalledWith({ setting: 'urban' });
    await user.click(screen.getByRole('radio', { name: 'Forest' }));
    expect(onPatch).toHaveBeenLastCalledWith({ setting: 'forest' });

    await user.selectOptions(screen.getByLabelText('Species'), 'teak');
    expect(onPatch).toHaveBeenLastCalledWith({ speciesId: 'teak' });
  });

  it('writes each species with its scientific name', () => {
    render(<Harness onPatch={vi.fn()} />);
    expect(screen.getByRole('option', { name: 'Mango (Mangifera indica)' })).toBeInTheDocument();
  });

  it('lets someone drag the age, and sends it straight away', () => {
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);
    fireEvent.change(screen.getByLabelText('Age of the trees, slider'), {
      target: { value: '80' },
    });
    expect(onPatch).toHaveBeenLastCalledWith({ age: 80 });
    expect(screen.getByLabelText('Age of the trees (years)')).toHaveValue('80');
  });

  it('describes the slider in words for screen readers, including 0', () => {
    render(<Harness onPatch={vi.fn()} />);
    const slider = screen.getByLabelText('Age of the trees, slider');
    expect(slider).toHaveAttribute('aria-valuetext', '30 years');
    fireEvent.change(slider, { target: { value: '1' } });
    expect(slider).toHaveAttribute('aria-valuetext', '1 year');
    fireEvent.change(slider, { target: { value: '0' } });
    expect(slider).toHaveAttribute('aria-valuetext', '0, planning new trees');
  });

  it('lets someone type an age that is past the end of the slider', async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);
    const box = screen.getByLabelText('Age of the trees (years)');
    await user.clear(box);
    await user.type(box, '200');
    expect(onPatch).toHaveBeenLastCalledWith({ age: 200 });
    expect(box).toHaveValue('200');
    // The slider stops at its own end instead of breaking.
    expect(screen.getByLabelText('Age of the trees, slider')).toHaveValue('150');
  });

  it('explains a mistake in the age box and sends nothing for it', async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);
    const box = screen.getByLabelText('Age of the trees (years)');
    await user.clear(box);
    expect(screen.getByText('Enter a number.')).toBeVisible();
    await user.type(box, '4.5');
    expect(screen.getByText('Use a whole number.')).toBeVisible();
    expect(box).toHaveAttribute('aria-invalid', 'true');
    await user.clear(box);
    await user.type(box, '301');
    expect(screen.getByText('The largest value is 300.')).toBeVisible();
    // Nothing above 300 or below 0 was ever sent.
    for (const [patch] of onPatch.mock.calls) {
      expect(patch.age).toBeLessThanOrEqual(300);
      expect(patch.age).toBeGreaterThanOrEqual(0);
    }
    await user.tab();
    expect(box).toHaveValue('30');
  });

  it('treats age 0 as planning new trees and switches the trunk box off', () => {
    render(<Harness onPatch={vi.fn()} initial={{ ...start, age: 0, girthCm: 80 }} />);
    expect(screen.getByText('Planning new trees')).toBeVisible();
    const girth = screen.getByLabelText(/Trunk girth at chest height/);
    expect(girth).toBeDisabled();
    expect(girth).toHaveValue('');
    expect(screen.getByText('A tree that is only planned has no trunk yet.')).toBeVisible();
  });

  it('explains how to measure the trunk when the trees already stand', () => {
    render(<Harness onPatch={vi.fn()} />);
    expect(screen.getByText('Use 0 if you are planning new trees.')).toBeVisible();
    expect(screen.getByText(/Wrap a tape around the trunk 1\.3 m/)).toBeVisible();
    expect(screen.getByLabelText(/Trunk girth at chest height/)).toBeEnabled();
  });

  it('sends the number of trees as it is typed and refuses nonsense', async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);
    const box = screen.getByLabelText('Number of trees');
    await user.clear(box);
    await user.type(box, '120');
    expect(onPatch).toHaveBeenLastCalledWith({ trees: 120 });
    await user.clear(box);
    await user.type(box, '0');
    expect(screen.getByText('The smallest value is 1.')).toBeVisible();
    await user.clear(box);
    await user.type(box, '12a');
    expect(screen.getByText('Use digits only.')).toBeVisible();
  });

  it('takes a trunk girth, with a decimal, and an empty box means "not measured"', async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(<Harness onPatch={onPatch} />);
    const box = screen.getByLabelText(/Trunk girth at chest height/);
    await user.type(box, '95.5');
    expect(onPatch).toHaveBeenLastCalledWith({ girthCm: 95.5 });
    await user.clear(box);
    expect(onPatch).toHaveBeenLastCalledWith({ girthCm: null });
    expect(screen.queryByText(/Use digits only|Enter a number/)).not.toBeInTheDocument();
    await user.type(box, '5');
    expect(screen.getByText('The smallest value is 10.')).toBeVisible();
    await user.clear(box);
    await user.type(box, '2500');
    expect(screen.getByText('The largest value is 2000.')).toBeVisible();
  });

  it('shows what the girth box is for: optional, in centimetres', () => {
    render(<Harness onPatch={vi.fn()} />);
    expect(screen.getByText(/optional/)).toBeVisible();
    expect(screen.getByText('cm')).toBeVisible();
  });

  describe('the species list', () => {
    it('is switched off and says so while it loads', () => {
      render(<Harness onPatch={vi.fn()} species={undefined} speciesLoading />);
      const select = screen.getByLabelText('Species');
      expect(select).toBeDisabled();
      expect(within(select).getByRole('option', { name: 'Loading species…' })).toBeInTheDocument();
    });

    it('says so when a country has no species', () => {
      render(<Harness onPatch={vi.fn()} species={[]} speciesLoading={false} />);
      expect(screen.getByRole('option', { name: 'No species available' })).toBeInTheDocument();
    });

    it('still shows a species from the address that the list does not have', () => {
      render(<Harness onPatch={vi.fn()} initial={{ ...start, speciesId: 'moringa' }} />);
      expect(screen.getByRole('option', { name: 'moringa' })).toBeInTheDocument();
    });
  });

  describe('Copy link', () => {
    it('copies the address of this page and says so', async () => {
      const user = userEvent.setup();
      render(<Harness onPatch={vi.fn()} />);
      await user.click(screen.getByRole('button', { name: 'Copy link' }));
      expect(await navigator.clipboard.readText()).toBe(
        'http://localhost/app/tree-age?country=IN&age=30',
      );
      expect(await screen.findByText('Link copied')).toBeVisible();
    });

    it('says what to do instead when the browser will not let it copy', async () => {
      const user = userEvent.setup();
      render(<Harness onPatch={vi.fn()} />);
      vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('denied'));
      await user.click(screen.getByRole('button', { name: 'Copy link' }));
      expect(
        await screen.findByText('Could not copy. Copy the address from the browser bar instead.'),
      ).toBeVisible();
    });
  });
});
