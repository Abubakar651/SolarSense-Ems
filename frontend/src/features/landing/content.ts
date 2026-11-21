export const SECTION_LINKS = [
  { id: 'features', label: 'Features' },
  { id: 'how', label: 'How it works' },
  { id: 'faq', label: 'FAQ' },
] as const;

export const SECTION_IDS = SECTION_LINKS.map((link) => link.id);

export const COMPATIBILITY = [
  { icon: 'zap', label: 'GoodWe hybrid inverters' },
  { icon: 'clock', label: 'Time-of-use tariffs' },
  { icon: 'grid', label: 'Net-metering export credit' },
  { icon: 'sun', label: 'Rooftop solar and battery' },
] as const;

export const STEPS = [
  {
    title: 'Set up your site',
    body: 'Solar, battery and tariff. Three minutes.',
  },
  {
    title: 'Connect your inverter',
    body: 'We build a 24-hour battery plan.',
  },
  {
    title: 'See what you saved',
    body: 'Savings, outages and panel health.',
  },
] as const;

export const FAQS = [
  {
    question: 'Which inverters work with SolarSense?',
    answer: 'GoodWe hybrid inverters today. Tell us your brand during setup.',
  },
  {
    question: 'Does SolarSense control my inverter?',
    answer: 'Not yet. It shows the plan; you apply it in your inverter app.',
  },
  {
    question: 'Do I need to know my tariff?',
    answer: 'Copy the rates from your bill. You can change them any time.',
  },
  {
    question: 'Is it for homes only?',
    answer: 'No. It works for any building with solar and a battery.',
  },
] as const;
