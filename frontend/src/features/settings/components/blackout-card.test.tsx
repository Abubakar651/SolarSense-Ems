import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import type { BlackoutWindow } from '@/types/domain/settings';
import { BlackoutCard } from './blackout-card';

function Harness({ initial = [] }: { initial?: BlackoutWindow[] }) {
  const [blackouts, setBlackouts] = useState(initial);
  return <BlackoutCard blackouts={blackouts} onChange={setBlackouts} />;
}

function setup(initial?: BlackoutWindow[]) {
  render(<Harness initial={initial} />);
  return userEvent.setup();
}

async function addWindow(user: ReturnType<typeof userEvent.setup>, from: string, to: string) {
  if (from) await user.type(screen.getByLabelText('Blackout starts'), from);
  if (to) await user.type(screen.getByLabelText('Ends'), to);
  await user.click(screen.getByRole('button', { name: 'Add blackout' }));
}

describe('BlackoutCard', () => {
  it('says so when no blackouts are added', () => {
    setup();
    expect(screen.getByText('No blackouts added.')).toBeVisible();
  });

  it('lists an added window with its length and clears the inputs', async () => {
    const user = setup();
    await addWindow(user, '18:00', '20:30');
    expect(screen.getByText('18:00 – 20:30')).toBeVisible();
    expect(screen.getByText('Every day, 2 h 30 min')).toBeVisible();
    expect(screen.getByLabelText('Blackout starts')).toHaveValue('');
    expect(screen.getByLabelText('Ends')).toHaveValue('');
  });

  it('shows an error and adds nothing when a time is missing', async () => {
    const user = setup();
    await addWindow(user, '18:00', '');
    expect(screen.getByText('Choose a start and an end time.')).toBeVisible();
    expect(screen.getByText('No blackouts added.')).toBeVisible();
    expect(screen.getByLabelText('Blackout starts')).toBeInvalid();
  });

  it('rejects a window that is already listed', async () => {
    const user = setup([{ start: '14:00', end: '16:00' }]);
    await addWindow(user, '14:00', '16:00');
    expect(screen.getByText('That blackout is already listed.')).toBeVisible();
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
  });

  it('removes a window', async () => {
    const user = setup([
      { start: '14:00', end: '16:00' },
      { start: '22:00', end: '02:00' },
    ]);
    await user.click(screen.getByRole('button', { name: 'Remove blackout 14:00 to 16:00' }));
    expect(screen.queryByText('14:00 – 16:00')).not.toBeInTheDocument();
    expect(screen.getByText('22:00 – 02:00')).toBeVisible();
  });
});
