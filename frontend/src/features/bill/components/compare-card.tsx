'use client';

import { useState } from 'react';
import { Check } from '@/components/forms/check';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { CardHeader } from '@/components/ui/card-header';
import { rules } from '@/lib/validators';
import type { BillToolsDefaults, ProsumerCompareRequest } from '@/types/domain/tariff';
import { readCompareForm } from '../view-model';
import { CompareResult } from './bill-results';

const LOAD_RULES = [rules.required(), rules.num(0.1, 1000)];
const UNITS_RULES = [rules.required(), rules.num(0, 100_000)];
const FPA_RULES = [rules.num(0, 100_000)];

export function CompareCard({ defaults }: { defaults: BillToolsDefaults }) {
  const [request, setRequest] = useState<ProsumerCompareRequest | null>(null);

  return (
    <div className="card">
      <CardHeader
        title="Net metering or net billing?"
        subtitle="Settle the same month both ways: units you bought and sent to the grid."
      />
      <ValidatedForm onValid={(form) => setRequest(readCompareForm(form))}>
        <Field
          id="cmp-load"
          label="Sanctioned load (kW)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          defaultValue={String(defaults.sanctionedLoadKw)}
          rules={LOAD_RULES}
        />
        <div className="two">
          <Field
            id="cmp-peak"
            label="Peak units bought (kWh)"
            type="text"
            autoComplete="off"
            inputMode="decimal"
            placeholder="0"
            rules={UNITS_RULES}
          />
          <Field
            id="cmp-off"
            label="Off-peak units bought (kWh)"
            type="text"
            autoComplete="off"
            inputMode="decimal"
            placeholder="0"
            rules={UNITS_RULES}
          />
        </div>
        <Field
          id="cmp-exp"
          label="Units sent to the grid (kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="0"
          rules={UNITS_RULES}
        />
        <Field
          id="cmp-fpa"
          label="Units two months ago (kWh)"
          type="text"
          autoComplete="off"
          inputMode="decimal"
          placeholder="0"
          rules={FPA_RULES}
        />
        <Check
          name="cmp-atl"
          label="Active taxpayer (ATL filer)"
          defaultChecked={defaults.isAtlFiler}
        />
        <Check
          name="cmp-duty"
          label="Include electricity duty"
          defaultChecked={defaults.includeElectricityDuty}
        />
        <button className="btn btn-primary" type="submit" style={{ marginTop: 'var(--sp-3)' }}>
          Compare
        </button>
      </ValidatedForm>
      {/* No comparison yet: it is worked out by POST /api/v2/prosumer/compare. */}
      <CompareResult request={request} comparison={null} />
    </div>
  );
}
