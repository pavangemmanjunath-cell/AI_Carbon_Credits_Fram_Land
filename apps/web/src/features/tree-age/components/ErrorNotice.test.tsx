import '../i18n';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError, NetworkError } from '@/services/api';
import { ErrorNotice } from './ErrorNotice';

describe('ErrorNotice', () => {
  it('tells people to start the API when it cannot be reached', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ErrorNotice error={new NetworkError('Could not reach the API')} onRetry={onRetry} />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('The tree-age check needs the API');
    expect(screen.getByText('make api').tagName).toBe('CODE');
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('treats a gateway error as "the API is not there" too', () => {
    render(<ErrorNotice error={new ApiError(503, undefined, 'Service Unavailable')} />);
    expect(screen.getByText('The tree-age check needs the API')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
  });

  it('shows the title and detail the API gave, and the HTTP status', () => {
    render(
      <ErrorNotice
        error={
          new ApiError(
            422,
            { title: 'Unprocessable Entity', detail: 'species_id: unknown species', status: 422 },
            'Request failed',
          )
        }
      />,
    );
    expect(screen.getByText('Unprocessable Entity')).toBeVisible();
    expect(screen.getByText('species_id: unknown species')).toBeVisible();
    expect(screen.getByText('HTTP 422')).toBeVisible();
    expect(screen.queryByText('make api')).not.toBeInTheDocument();
  });

  it('shows an ordinary error with a plain title and its message', () => {
    render(<ErrorNotice error={new Error('Boom')} />);
    expect(screen.getByText('Something went wrong')).toBeVisible();
    expect(screen.getByText('Boom')).toBeVisible();
  });

  it('copes with something that is not an error at all', () => {
    render(<ErrorNotice error={'nope'} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong');
  });
});
