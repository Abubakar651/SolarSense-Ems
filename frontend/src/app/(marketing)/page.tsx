import { CtaBand } from '@/features/landing/components/cta-band';
import { Faq } from '@/features/landing/components/faq';
import { FeatureBento } from '@/features/landing/components/feature-bento';
import { Hero } from '@/features/landing/components/hero';
import { LandingFooter } from '@/features/landing/components/landing-footer';
import { LandingNav } from '@/features/landing/components/landing-nav';
import { Steps } from '@/features/landing/components/steps';
import { Strip } from '@/features/landing/components/strip';
import { getServices } from '@/services';
import type { MonthReport } from '@/types/domain/reports';

export default async function LandingPage() {
  const { energy, panels, outage, reports, alerts } = getServices();
  const [plan, soiling, outageData, report, alertList] = await Promise.all([
    energy.getDayPlan(),
    panels.getSoiling(),
    outage.getOutage(),
    reports.getReport(),
    alerts.listAlerts(),
  ]);

  return (
    <section data-route="landing">
      <LandingNav />
      <Hero plan={plan} />
      <Strip />
      <section className="sect" id="features" aria-labelledby="features-h">
        <div className="wrap">
          <div className="sect-h">
            <h2 id="features-h">Built for how power works in Pakistan</h2>
            <p>
              Peak tariffs, outages and dust all change what your system should do. SolarSense plans
              for them.
            </p>
          </div>
          <FeatureBento
            plan={plan}
            soiling={soiling}
            outage={outageData}
            report={report.months[0] as MonthReport}
            latestAlert={alertList[0]}
          />
        </div>
      </section>
      <Steps />
      <Faq />
      <CtaBand />
      <LandingFooter />
    </section>
  );
}
