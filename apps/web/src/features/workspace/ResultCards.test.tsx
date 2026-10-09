import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { analysis, estimate, inventory, plot } from '@/test/fixtures';
import { ResultCards } from './ResultCards';

describe('ResultCards', () => {
  it('renders exactly three cards with area, NDVI and the removal range', () => {
    render(<ResultCards plot={plot} inventory={inventory} estimate={estimate} analysis={analysis} locale="en-IN" />);
    expect(screen.getAllByRole('article')).toHaveLength(3);
    expect(screen.getByText(/2\.13 ha/)).toBeInTheDocument();
    expect(screen.getByText(/0\.76/)).toBeInTheDocument();
    expect(screen.getByText(/7\.4 – 13\.8/)).toBeInTheDocument();
    expect(screen.getByText(/not an issued carbon credit/i)).toBeInTheDocument();
  });

  it('shows placeholders without data', () => {
    render(<ResultCards plot={null} inventory={null} locale="en-IN" />);
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });
});
