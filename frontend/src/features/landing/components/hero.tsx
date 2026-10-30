import Link from 'next/link';
import { PlanChart } from '@/components/charts/plan-chart';
import { Icon } from '@/components/ui/icon';
import type { DayPlan } from '@/types/domain/energy';

/** Headline, calls to action and a sample "day of solar" chart. */
export function Hero({ plan }: { plan: DayPlan }) {
  return (
    <section className="hero" aria-label="Introduction">
      <div className="wrap">
        <div className="hero-grid">
          <div>
            <span className="eyebrow">
              <span className="dot live" />
              Make the most of every sunny hour
            </span>
            <h1 tabIndex={-1}>
              Use <em className="hl">every unit</em> your panels generate.
            </h1>
            <p className="lead">
              SolarSense stores surplus solar for the hours you need it, so less is wasted or
              exported cheaply and more of your own generation powers your site. It also tells you
              when washing the panels pays off, and shows what you saved.
            </p>
            <div className="cta">
              <Link className="btn btn-primary btn-lg" href="/signup">
                Create your account
                <Icon name="arrow" className="btn-arrow" />
              </Link>
              <Link className="btn btn-secondary btn-lg" href="/login">
                Log in
              </Link>
            </div>
            <p className="small">
              For homes and commercial buildings with solar and a battery. Works with GoodWe
              inverters today.
            </p>
          </div>
          <div className="plate">
            <div className="preview-bar">
              <span className="badge b-warn">Sample data</span>
            </div>
            <div className="plate-h">
              <h2>A day of solar</h2>
              <div className="legend" aria-hidden="true">
                <span>
                  <i className="sw soft" />
                  Solar
                </span>
                <span>
                  <i className="sw line" />
                  Usage
                </span>
                <span>
                  <i className="sw" />
                  Battery
                </span>
              </div>
            </div>
            <PlanChart
              id="chart-land"
              readoutId="land-readout"
              series={plan}
              now={plan.clockStart}
              height={{ narrow: 270, wide: 340 }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
