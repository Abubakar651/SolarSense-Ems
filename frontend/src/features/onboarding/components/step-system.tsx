import { Field } from '@/components/forms/field';
import { rules } from '@/lib/validators';

const REQUIRED = [rules.required()];
const SOLAR_RULES = [rules.required(), rules.num(0.5, 2000)];
const BATTERY_RULES = [rules.required(), rules.num(1, 5000)];

export function StepSystem({ hidden }: { hidden: boolean }) {
  return (
    <div className="card" data-step="1" hidden={hidden}>
      <h2 style={{ marginBottom: 'var(--sp-4)' }}>Your solar &amp; battery system</h2>
      <div className="two">
        <Field
          id="ob-pv"
          group="1"
          label="Solar capacity (kWp)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="7.02"
          rules={SOLAR_RULES}
        />
        <Field
          id="ob-bat"
          group="1"
          label="Battery capacity (kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="5.12"
          rules={BATTERY_RULES}
        />
      </div>
      <div className="field">
        <label htmlFor="ob-inv">Inverter brand</label>
        <select className="input" id="ob-inv" name="ob-inv">
          <option>GoodWe</option>
          <option>Other (tell us later)</option>
        </select>
        <p className="hint">
          GoodWe inverters connect automatically through their portal. Other brands are added on
          request.
        </p>
      </div>
      <Field
        id="ob-sn"
        group="1"
        label="Inverter serial number"
        type="text"
        autoComplete="off"
        placeholder="From the inverter label"
        rules={REQUIRED}
      />
    </div>
  );
}
