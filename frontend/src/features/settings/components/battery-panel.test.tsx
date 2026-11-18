import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SettingsFormProvider } from './settings-form';
import { BatteryPanel } from './battery-panel';

function setup() {
  render(
    <SettingsFormProvider value={{ values: { reserve: '15' }, set: () => undefined }}>
      <BatteryPanel capacityKwh={5.12} blackouts={[]} onBlackoutsChange={() => undefined} />
    </SettingsFormProvider>,
  );
}

describe('BatteryPanel', () => {
  it('does not let the reserve go below the 15% inverter floor', () => {
    setup();
    expect(screen.getByRole('slider')).toHaveAttribute('min', '15');
  });

  it('offers only settings the backend can act on', () => {
    setup();
    expect(screen.queryByText('Priority')).not.toBeInTheDocument();
    expect(screen.queryByText(/overnight charge window/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/export extra solar/i)).not.toBeInTheDocument();
  });

  it('lists the fixed rules as always on, not as switches', () => {
    setup();
    expect(screen.getByText('Never charge from the grid at peak rates')).toBeVisible();
    expect(screen.getAllByText('Always on')).toHaveLength(3);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });
});
