import type { ReactNode } from 'react';
import { StepConnectIllustration } from '@/components/illustrations/step-connect';
import { StepSavingsIllustration } from '@/components/illustrations/step-savings';
import { StepSiteIllustration } from '@/components/illustrations/step-site';
import { Reveal } from '@/components/ui/reveal';
import { STEPS } from '../content';

const ILLUSTRATIONS: ReactNode[] = [
  <StepSiteIllustration key="site" />,
  <StepConnectIllustration key="connect" />,
  <StepSavingsIllustration key="savings" />,
];

export function Steps() {
  return (
    <section className="sect tint" id="how" aria-labelledby="how-h">
      <div className="wrap">
        <div className="sect-h">
          <h2 id="how-h">Up and running in three steps</h2>
        </div>
        <ol className="steps">
          {STEPS.map(({ title, body }, index) => (
            <Reveal as="li" key={title} index={index}>
              <div className="step-ill">{ILLUSTRATIONS[index]}</div>
              <span className="n">{index + 1}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
