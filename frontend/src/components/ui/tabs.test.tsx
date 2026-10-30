import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Tabs } from './tabs';

const tabs = [
  { key: 'a', label: 'Alpha', content: <p>Alpha panel</p> },
  { key: 'b', label: 'Beta', content: <p>Beta panel</p> },
  { key: 'c', label: 'Gamma', content: <p>Gamma panel</p> },
];

function setup() {
  render(<Tabs id="t" panelsId="p" ariaLabel="Demo" tabs={tabs} />);
  return userEvent.setup();
}

const tab = (name: string) => screen.getByRole('tab', { name });

describe('Tabs', () => {
  it('starts on the first tab and shows only its panel', () => {
    setup();
    expect(tab('Alpha')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Alpha panel')).toBeVisible();
    expect(screen.getByText('Beta panel')).not.toBeVisible();
  });

  it('selects a tab on click', async () => {
    const user = setup();
    await user.click(tab('Beta'));
    expect(tab('Beta')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Beta panel')).toBeVisible();
    expect(screen.getByText('Alpha panel')).not.toBeVisible();
  });

  it('keeps only the selected tab in the tab order', async () => {
    const user = setup();
    expect(tab('Alpha')).toHaveAttribute('tabindex', '0');
    expect(tab('Beta')).toHaveAttribute('tabindex', '-1');
    await user.click(tab('Beta'));
    expect(tab('Beta')).toHaveAttribute('tabindex', '0');
    expect(tab('Alpha')).toHaveAttribute('tabindex', '-1');
  });

  it('moves focus and selection with the arrow keys, wrapping at both ends', async () => {
    const user = setup();
    await user.tab();
    await user.keyboard('{ArrowRight}');
    expect(tab('Beta')).toHaveFocus();
    expect(tab('Beta')).toHaveAttribute('aria-selected', 'true');
    await user.keyboard('{ArrowLeft}{ArrowLeft}');
    expect(tab('Gamma')).toHaveFocus();
    await user.keyboard('{ArrowRight}');
    expect(tab('Alpha')).toHaveFocus();
  });

  it('jumps to the first and last tab with Home and End', async () => {
    const user = setup();
    await user.tab();
    await user.keyboard('{End}');
    expect(tab('Gamma')).toHaveAttribute('aria-selected', 'true');
    await user.keyboard('{Home}');
    expect(tab('Alpha')).toHaveAttribute('aria-selected', 'true');
  });

  it('links each tab to its panel', () => {
    setup();
    const panel = document.getElementById('tp-b');
    expect(panel).toHaveAttribute('role', 'tabpanel');
    expect(panel).toHaveAttribute('aria-labelledby', 'tb-b');
    expect(tab('Beta')).toHaveAttribute('id', 'tb-b');
    expect(tab('Beta')).toHaveAttribute('aria-controls', 'tp-b');
  });
});
