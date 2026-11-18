import { Field } from '@/components/forms/field';
import {
  DEFAULT_REGIME,
  DEFAULT_TARIFF_CATEGORY,
  PROSUMER_REGIMES,
  TARIFF_CATEGORIES,
} from '@/lib/tariff';
import { rules } from '@/lib/validators';

/** The backend requires a sanctioned load above 0 kW (BillEstimateRequest). */
const LOAD_RULES = [rules.required(), rules.num(0.1, 1000)];

export function StepTariff({ hidden }: { hidden: boolean }) {
  return (
    <div className="card" data-step="2" hidden={hidden}>
      <h2 style={{ marginBottom: 4 }}>Your electricity tariff</h2>
      <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
        Prefilled with sample values. Check them against your bill.
      </p>
      <div className="field">
        <label htmlFor="ob-cat">Tariff category</label>
        <select className="input" id="ob-cat" name="ob-cat" defaultValue={DEFAULT_TARIFF_CATEGORY}>
          {TARIFF_CATEGORIES.map(({ id, label }) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="ob-reg">Solar export arrangement</label>
        <select
          className="input"
          id="ob-reg"
          name="ob-reg"
          defaultValue={DEFAULT_REGIME}
          aria-describedby="ob-reg-h"
        >
          {PROSUMER_REGIMES.map(({ id, label }) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <p className="hint" id="ob-reg-h">
          Decides what power you send to the grid earns. Check your net-metering agreement date.
        </p>
      </div>
      <Field
        id="ob-load"
        group="2"
        label="Sanctioned load (kW)"
        type="text"
        autoComplete="off"
        inputMode="decimal"
        placeholder="10"
        rules={LOAD_RULES}
        hint="Shown on your bill. Peak and off-peak rates and export credit are set by LESCO."
      />
    </div>
  );
}
