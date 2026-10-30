'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ValidatedForm } from '@/components/forms/validated-form';
import { useToast } from '@/providers/toast-provider';
import { LAST_STEP, ONBOARDING_STEPS, formValues, reviewRows, type ReviewRow } from '../view-model';
import { StepReview } from './step-review';
import { StepSite } from './step-site';
import { StepSystem } from './step-system';
import { StepTariff } from './step-tariff';

/** Four-step setup. Every step stays mounted (hidden) so values survive Back and Continue. */
export function OnboardingWizard() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [review, setReview] = useState<ReviewRow[]>([]);
  const moved = useRef(false);

  // After a step change, scroll to the top and move focus to the new step's heading.
  useEffect(() => {
    if (!moved.current) return;
    window.scrollTo(0, 0);
    const heading = document.querySelector<HTMLElement>(`[data-step="${step}"] h2`);
    heading?.setAttribute('tabindex', '-1');
    heading?.focus();
  }, [step]);

  const onValid = (form: HTMLFormElement) => {
    if (step === LAST_STEP) {
      toast('Setup complete. Building your first plan…');
      router.push('/dashboard');
      return;
    }
    if (step === LAST_STEP - 1) setReview(reviewRows(formValues(form)));
    moved.current = true;
    setStep(step + 1);
  };

  return (
    <section data-route="onboarding">
      <div className="onb">
        <h1 tabIndex={-1}>Set up your site</h1>
        <p className="muted" style={{ margin: '4px 0 var(--sp-5)' }}>
          This takes about 3 minutes. You can change everything later in Settings.
        </p>
        <ol className="stepper" id="stepper" aria-label="Setup progress">
          {ONBOARDING_STEPS.map((label, index) => (
            <li
              key={label}
              data-state={index < step ? 'done' : undefined}
              aria-current={index === step ? 'step' : undefined}
            >
              {label}
            </li>
          ))}
        </ol>
        <ValidatedForm onValid={onValid} activeGroup={String(step)}>
          <StepSite hidden={step !== 0} />
          <StepSystem hidden={step !== 1} />
          <StepTariff hidden={step !== 2} />
          <StepReview hidden={step !== 3} rows={review} />
          <div className="row between" style={{ marginTop: 'var(--sp-5)' }}>
            <button
              className="btn btn-secondary"
              type="button"
              id="onbBack"
              style={{ visibility: step ? 'visible' : 'hidden' }}
              onClick={() => {
                moved.current = true;
                setStep(step - 1);
              }}
            >
              Back
            </button>
            <button className="btn btn-primary" type="submit" id="onbNext">
              {step === LAST_STEP ? 'Finish setup' : 'Continue'}
            </button>
          </div>
        </ValidatedForm>
      </div>
    </section>
  );
}
