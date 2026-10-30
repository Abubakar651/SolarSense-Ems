import { Field } from '@/components/forms/field';
import { rules } from '@/lib/validators';

const REQUIRED = [rules.required()];

export function StepSite({ hidden }: { hidden: boolean }) {
  return (
    <div className="card" data-step="0" hidden={hidden}>
      <h2 style={{ marginBottom: 'var(--sp-4)' }}>About your site</h2>
      <Field
        id="ob-site"
        group="0"
        label="Site name"
        type="text"
        autoComplete="organization"
        placeholder="e.g. My Site"
        rules={REQUIRED}
      />
      <Field
        id="ob-addr"
        group="0"
        label="Address"
        type="text"
        autoComplete="street-address"
        placeholder="Street, area"
        rules={REQUIRED}
      />
      <div className="two">
        <Field
          id="ob-city"
          group="0"
          label="City"
          type="text"
          autoComplete="address-level2"
          placeholder="Your city"
          rules={REQUIRED}
        />
        <div className="field">
          <label htmlFor="ob-tz">Time zone</label>
          <input
            className="input"
            id="ob-tz"
            value="Set automatically from your city"
            readOnly
            aria-describedby="ob-tz-h"
          />
          <p className="hint" id="ob-tz-h">
            Set from your city.
          </p>
        </div>
      </div>
    </div>
  );
}
