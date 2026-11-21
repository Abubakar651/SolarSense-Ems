/** Response shapes of the account API; they mirror src/api/account_schemas.py in the backend. */

export interface UserDto {
  id: string;
  name: string;
  email: string;
  phone: string;
  onboarded: boolean;
}

export interface TokenDto {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: UserDto;
}

export interface SettingsDto {
  profile: { name: string; phone: string; email: string };
  site: {
    name: string;
    city: string;
    address: string;
    timezone: string;
    pv_kwp: number;
    battery_kwh: number;
    inverter_make: string;
    inverter_serial: string;
    /** The inverter's address on the home network; null until the user adds it. */
    inverter_host: string | null;
    /** Set only on the site that owns the recorded station dataset. */
    station_code: string | null;
  };
  reserve_pct: number;
  blackouts: { start: string; end: string }[];
  tariff: {
    category: string;
    regime: string;
    sanctioned_load_kw: number;
    is_atl_filer: boolean;
    include_electricity_duty: boolean;
    is_protected_consumer: boolean;
  };
  notifications: { key: string; in_app: boolean; email: boolean }[];
}

export interface AlertDto {
  id: string;
  severity: 'crit' | 'warn' | 'info' | 'ok';
  title: string;
  detail: string;
  created_at: string;
  read: boolean;
}

export interface ReportPrefsDto {
  monthly: boolean;
  weekly: boolean;
  send_to: string;
}

/** GET /api/insights/outages (src/api/insights.py). */
export interface OutageHistoryDto {
  /** Null while the site has neither recorded nor logged data. */
  period_start: string | null;
  period_end: string | null;
  events: {
    date: string;
    start: string;
    end: string;
    minutes: number;
    energy_kwh: number;
    soc_end_pct: number | null;
  }[];
  /** Last day of the station's recorded dataset (station site only) and of this site's own log. */
  recorded_through: string | null;
  logged_through: string | null;
  /** Complete days in this site's own log. */
  logged_days: number;
}

/** GET /api/insights/energy. */
export interface EnergyHistoryDto {
  daily: {
    date: string;
    solar_kwh: number;
    load_kwh: number;
    import_kwh: number;
    export_kwh: number;
    battery_charged_kwh?: number | null;
    battery_discharged_kwh?: number | null;
  }[];
  monthly: {
    month: string;
    pv_kwh: number;
    load_kwh: number;
    purchased_kwh: number;
    sold_kwh: number;
  }[];
  /** Up to the last 24 months, oldest first. */
  monthly_history?: EnergyHistoryDto['monthly'];
  /** Last day the monthly totals cover; null with no data yet. */
  metered_through: string | null;
  /** Last day of the station's recorded dataset (station site only) and of this site's own log. */
  recorded_through: string | null;
  logged_through: string | null;
  /** Complete days in this site's own log. */
  logged_days: number;
  /** Last day of the station's recorded hourly data its daily rows come from (station site only). */
  hourly_through?: string | null;
  /** The site's rates from the backend tariff engine (PKR/kWh as decimal strings); null with no data yet. */
  rates?: { self_consumed_pkr_per_kwh: string; export_pkr_per_kwh: string } | null;
  /** The latest month's LESCO bill estimate from the tariff engine (PKR as decimal strings). */
  current_month?: { month: string; cost_pkr: string; without_solar_pkr: string } | null;
}

/**
 * GET /api/insights/soiling: the site's dust model since its latest clean event (wash_date). 404
 * soiling_collecting (body: SoilingCollectingDto) while the live model gathers days; 503
 * weather_unavailable when the sunlight data can't be fetched.
 */
export interface SoilingHistoryDto {
  wash_date: string;
  as_of: string;
  model_pr: number[];
  daily_loss_kwh: number;
  /** live: fitted to this site's own log; recorded: the station's recorded model. */
  source: 'live' | 'recorded';
  clean_event: 'wash' | 'rain';
  logged_days_since_clean: number;
  loss_rate_per_day: number;
  /** What one lost kWh is worth at the site's tariff. */
  tariff_pkr_per_kwh: number;
  /** Typical price of one wash; the user can change it in the wash calculator. */
  wash_cost_pkr: number;
}

/** The 404 soiling_collecting body of GET /api/insights/soiling. */
export interface SoilingCollectingDto {
  detail: 'soiling_collecting';
  /** null when no wash was recorded and no washing rain fell recently. */
  clean_event: 'wash' | 'rain' | null;
  clean_date: string | null;
  logged_days_since_clean: number;
  days_needed: number;
}

/** GET /api/insights/rain: Lahore's forecast. 503 rain_forecast_unavailable when it can't be fetched. */
export interface RainForecastDto {
  /** Days until rain of threshold_mm or more; null when none is forecast within horizon_days. */
  days_until_rain: number | null;
  threshold_mm: number;
  horizon_days: number;
}

/** GET /api/dates (public). */
export interface DateBoundsDto {
  min_date: string;
  max_date: string;
}

/** POST /api/v2/optimize (Lesco2026OptimizeResponse in src/api/schemas.py). */
export interface OptimizeDto {
  status: string;
  timestamps: string[];
  solar_kw: number[];
  load_kw: number[];
  is_peak: number[];
  p_grid_import_kw: number[];
  p_ch_kw: number[];
  /** 25 values: the level before hour 0, then after each hour (kWh). */
  soc_kwh: number[];
  export_rate_used_pkr_per_kwh: string;
  /** The all-in rates (PKR/kWh) the solver priced peak and Off-Peak imports at; equal on a slab tariff. */
  peak_import_rate_pkr_per_kwh: string;
  off_peak_import_rate_pkr_per_kwh: string;
}

/** POST /api/v2/plan/today (LivePlanResponse): today's dispatch on live forecasts. */
export interface LivePlanDto extends OptimizeDto {
  /** Local day the plan covers (YYYY-MM-DD). */
  date: string;
  outage_prob: number[];
  /** Hours of the forecasters' lag history taken from logged inverter telemetry. */
  history_logged_hours: number;
  history_hours: number;
  /** The user's array the solar forecast was scaled to. */
  pv_kwp: number;
  /** The user's battery the dispatch was solved for, and their backup reserve (kWh). */
  battery_capacity_kwh: number;
  reserve_floor_kwh: number;
  /** True when no battery level was logged near midnight, so today's starting level is assumed. */
  initial_soc_assumed: boolean;
}

/** POST /api/agent/advisory/today (DailyBriefResponse). */
export interface DailyBriefDto {
  date: string;
  site_name: string;
  headline: string;
  dispatch_arbitrage_brief: string;
  blackout_resilience_brief: string;
  soiling_maintenance_brief: string;
  recommended_actions: string[];
  /** null: the figure can't be worked out today (e.g. the dust estimate is still collecting days). */
  key_metrics: Record<string, number | null>;
  generation_mode: string;
}

/** GET /api/v2/inverter/live (InverterLiveResponse). */
export interface InverterLiveDto {
  timestamp_iso: string;
  model_name: string;
  serial_number: string;
  battery_soc_pct: number;
  battery_soh_pct: number;
  battery_voltage_v: number;
  battery_current_a: number;
  battery_power_w: number;
  battery_mode: string;
  battery_temp_c: number;
  total_pv_power_w: number;
  pv1_power_w: number;
  pv2_power_w: number;
  house_consumption_w: number;
  grid_voltage_v: number;
  grid_frequency_hz: number;
  grid_active_power_w: number;
  grid_mode: string;
  is_grid_connected: boolean;
  is_blackout: boolean;
  backup_voltage_v: number;
  backup_power_w: number;
  work_mode: string;
  today_pv_kwh: number;
  today_export_kwh: number;
  today_import_kwh: number;
  today_load_kwh: number;
  today_battery_charge_kwh: number;
  today_battery_discharge_kwh: number;
  inverter_temp_air_c: number;
  inverter_temp_radiator_c: number;
}
