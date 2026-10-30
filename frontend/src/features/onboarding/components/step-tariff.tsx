import { Field } from '@/components/forms/field';
import { rules } from '@/lib/validators';

const RATE_RULES = [rules.required(), rules.num(1, 500)];
const EXPORT_RULES = [rules.required(), rules.num(0, 500)];

export function StepTariff({ hidden }: { hidden: boolean }) {
  return (
    <div className="card" data-step="2" hidden={hidden}>
      <h2 style={{ marginBottom: 4 }}>Your electricity tariff</h2>
      <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
        Prefilled with sample values. Check them against your bill.
      </p>
      <div className="field">
        <label htmlFor="ob-plan">Plan</label>
        <select className="input" id="ob-plan" name="ob-plan">
          <option>Time-of-use (peak / off-peak)</option>
          <option>Flat rate</option>
        </select>
      </div>
      <div className="two">
        <Field
          id="ob-peak"
          group="2"
          label="Peak rate (PKR/kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="46.85"
          rules={RATE_RULES}
        />
        <Field
          id="ob-off"
          group="2"
          label="Off-peak rate (PKR/kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="34.53"
          rules={RATE_RULES}
        />
      </div>
      <Field
        id="ob-exp"
        group="2"
        label="Export credit (PKR/kWh)"
        type="text"
        autoComplete="off"
        inputMode="decimal"
        placeholder="27.00"
        rules={EXPORT_RULES}
        hint="What your utility pays for power you send to the grid."
      />
    </div>
  );
}
