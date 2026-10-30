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
    body: 'Tell us your solar and battery size and your tariff. About three minutes.',
  },
  {
    title: 'Connect your inverter',
    body: "We read your system's data and build a 24-hour plan for the battery.",
  },
  {
    title: 'See what you saved',
    body: 'Track savings, outages and panel health from one dashboard.',
  },
] as const;

export const FAQS = [
  {
    question: 'Which inverters work with SolarSense?',
    answer:
      'GoodWe hybrid inverters connect today. If you use another brand, tell us during setup and we will add it to the list.',
  },
  {
    question: 'Does SolarSense control my inverter?',
    answer:
      'For now it advises: it shows you the plan and you apply it on your inverter app. Automatic control is coming and you will always be able to override it.',
  },
  {
    question: 'Do I need to know my tariff?',
    answer:
      'It helps. You enter your peak and off-peak rates and export credit from your bill, and you can change them any time in Settings.',
  },
  {
    question: 'Is it for homes only?',
    answer:
      'No. The same dashboard works for homes and commercial buildings that have solar and a battery.',
  },
] as const;
