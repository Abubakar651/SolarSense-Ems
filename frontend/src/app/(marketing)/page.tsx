import { CtaBand } from '@/features/landing/components/cta-band';
import { Faq } from '@/features/landing/components/faq';
import { FeatureBento } from '@/features/landing/components/feature-bento';
import { Hero } from '@/features/landing/components/hero';
import { LandingFooter } from '@/features/landing/components/landing-footer';
import { LandingNav } from '@/features/landing/components/landing-nav';
import { Steps } from '@/features/landing/components/steps';
import { Strip } from '@/features/landing/components/strip';
import { readyData, readyPlan } from '@/lib/history';
import { getSampleServices } from '@/services';
import type { MonthReport } from '@/types/domain/reports';

export default async function LandingPage() {
  const { energy, panels, outage, reports, alerts } = getSampleServices();
  const [planResult, soilingResult, outageResult, reportResult, alertList] = await Promise.all([
    energy.getDayPlan(),
    panels.getSoiling(),
    outage.getOutage(),
    reports.getReport(),
    alerts.listAlerts(),
  ]);
  // The landing page always shows the bundled sample data, which is always ready.
  const plan = readyPlan(planResult);
  const soiling = readyData(soilingResult);
  const outageData = readyData(outageResult);
  const report = readyData(reportResult);

  return (
    <section data-route="landing">
      <LandingNav />
      <Hero plan={plan} />
      <Strip />
      <section className="sect" id="features" aria-labelledby="features-h">
        <div className="wrap">
          <div className="sect-h">
            <h2 id="features-h">Built for how power works in Pakistan</h2>
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
