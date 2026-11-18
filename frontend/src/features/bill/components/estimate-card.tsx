'use client';

import { useState } from 'react';
import { Check } from '@/components/forms/check';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { CardHeader } from '@/components/ui/card-header';
import { TARIFF_CATEGORIES, type TariffCategory } from '@/lib/tariff';
import { rules } from '@/lib/validators';
import type { BillEstimateRequest, BillToolsDefaults } from '@/types/domain/tariff';
import { readEstimateForm, usesPeakSplit } from '../view-model';
import { EstimateResult } from './bill-results';

/** The backend requires a sanctioned load above 0 kW. */
const LOAD_RULES = [rules.required(), rules.num(0.1, 1000)];
const UNITS_RULES = [rules.num(0, 100_000)];

export function EstimateCard({ defaults }: { defaults: BillToolsDefaults }) {
  const [category, setCategory] = useState<TariffCategory>(defaults.category);
  const [request, setRequest] = useState<BillEstimateRequest | null>(null);

  return (
    <div className="card">
      <CardHeader
        title="Bill estimate"
        subtitle="Work out a monthly LESCO bill from the units on your meter."
      />
      <ValidatedForm onValid={(form) => setRequest(readEstimateForm(form))}>
        <div className="field">
          <label htmlFor="bill-cat">Tariff category</label>
          <select
            className="input"
            id="bill-cat"
            name="bill-cat"
            value={category}
            onChange={(event) => setCategory(event.target.value as TariffCategory)}
          >
            {TARIFF_CATEGORIES.map(({ id, label }) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="bill-load"
          label="Sanctioned load (kW)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          defaultValue={String(defaults.sanctionedLoadKw)}
          rules={LOAD_RULES}
        />
        {usesPeakSplit(category) ? (
          <div className="two">
            <Field
              id="bill-peak"
              label="Peak units (kWh)"
              type="text"
              autoComplete="off"
              inputMode="decimal"
              placeholder="0"
              rules={UNITS_RULES}
            />
            <Field
              id="bill-off"
              label="Off-peak units (kWh)"
              type="text"
              autoComplete="off"
              inputMode="decimal"
              placeholder="0"
              rules={UNITS_RULES}
            />
          </div>
        ) : (
          <Field
            id="bill-kwh"
            label="Units used (kWh)"
            type="text"
            autoComplete="off"
            inputMode="decimal"
            placeholder="0"
            rules={UNITS_RULES}
          />
        )}
        <Field
          id="bill-fpa"
          label="Units two months ago (kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="0"
          rules={UNITS_RULES}
          hint="LESCO bases the fuel price adjustment on this month."
        />
        <Check
          name="bill-atl"
          label="Active taxpayer (ATL filer)"
          defaultChecked={defaults.isAtlFiler}
        />
        <Check
          name="bill-duty"
          label="Include electricity duty"
          defaultChecked={defaults.includeElectricityDuty}
        />
        <button className="btn btn-primary" type="submit" style={{ marginTop: 'var(--sp-3)' }}>
          Calculate
        </button>
      </ValidatedForm>
      {/* No estimate yet: the calculation lives on the backend (POST /api/v2/bill/estimate). */}
      <EstimateResult request={request} estimate={null} />
    </div>
  );
}
