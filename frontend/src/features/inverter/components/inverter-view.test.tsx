import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { inverterMock } from '@/services/repositories/inverter/inverter.mock';
import { InverterView } from './inverter-view';

describe('InverterView', () => {
  it('shows the sample reading with its label and dashes for missing readings', async () => {
    render(<InverterView result={await inverterMock.getLive()} />);
    expect(screen.getByRole('heading', { name: 'Live inverter' })).toBeVisible();
    expect(screen.getByText('Sample data')).toBeVisible();
    expect(screen.getByText('Importing 0.85 kW')).toBeVisible();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Energy flow' })).toBeVisible();
    expect(screen.getByRole('img', { name: /Energy flow\./ })).toBeInTheDocument();
  });

  it('explains when the inverter cannot be reached and offers a retry', () => {
    render(
      <InverterView result={{ status: 'offline', message: 'Inverter offline or unreachable.' }} />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Inverter offline or unreachable.');
    expect(screen.getByRole('link', { name: 'Try again' })).toHaveAttribute('href', '/inverter');
  });
});
