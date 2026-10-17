/**
 * The landing page's story, told with the sample company's real data (app/backend/seed/generate.py):
 * Nisha Verma, Performance Marketing Manager, resigns on 12 Oct; her last day is 3 Nov.
 */

/** What Nisha carries in her head. x/y are % of the frame; `wide` ones only show on larger screens. */
export const FRAGMENTS: { text: string; x: number; y: number; wide?: boolean }[] = [
  { text: 'The only admin on Meta Business Manager', x: 6, y: 13 },
  { text: 'Why Google Ads was paused in June', x: 62, y: 10 },
  { text: 'Mixpanel renews on 15 Nov. Tom knows the deal.', x: 70, y: 24, wide: true },
  { text: 'Rhea at Pixel & Pine, every Monday', x: 14, y: 27, wide: true },
  { text: 'The only admin on GA4', x: 4, y: 74 },
  { text: 'Why 30% of the budget moved to Reels', x: 58, y: 80 },
  { text: 'Budget pacing, checked before anyone asks', x: 30, y: 88, wide: true },
  { text: 'The UTM sheet, rebuilt at month-end', x: 66, y: 68, wide: true },
  { text: 'Which landing page test is still running', x: 8, y: 62, wide: true },
  { text: 'The growth report the CEO reads', x: 40, y: 18, wide: true },
  { text: 'Reels CPM was 40% lower in March', x: 76, y: 52, wide: true },
  { text: 'Seat-based pricing, half negotiated', x: 3, y: 44, wide: true },
]

export type Signal = {
  /** Key in platformGlyphs. */
  tool: string
  where: string
  raw: string
  /** The line it becomes in the handover document; none for private sources. */
  line?: { section: string; text: string }
}

/** Raw work, as the connectors see it, in the order the handover writes itself. */
export const SIGNALS: Signal[] = [
  {
    tool: 'slack',
    where: '#growth · 11 May',
    raw: 'FYI I’m still the only admin on Meta Business Manager and GA4.',
    line: { section: 'Access to hand over', text: 'Meta Business Manager and GA4: add a second admin' },
  },
  {
    tool: 'slack',
    where: '#growth · 19 Jun',
    raw: 'Paused all Google Ads campaigns as of today. Budget moves to Meta.',
    line: { section: 'Decisions and why', text: 'Google Ads paused in June; the budget went to Meta' },
  },
  {
    tool: 'google_drive',
    where: 'Q2 growth plan · deck',
    raw: 'Shift 30% of paid social budget to Reels (CPM 40% lower in March tests).',
    line: { section: 'Decisions and why', text: '30% of paid social moved to Reels, after the March tests' },
  },
  {
    tool: 'google_drive',
    where: 'Salary notes · private',
    raw: 'Notes for the conversation about my pay…',
  },
  {
    tool: 'notion',
    where: 'End-of-day notes',
    raw: 'Briefed Pixel & Pine on next week’s creatives (3 hooks, 2 formats).',
    line: { section: 'Work only she does', text: 'Brief and review creatives with Pixel & Pine, weekly' },
  },
  {
    tool: 'hubspot',
    where: 'Mixpanel renewal call',
    raw: 'Annual contract renews 15 Nov; asked for seat-based pricing.',
    line: { section: 'People to meet', text: 'Tom Becker, Mixpanel: renewal on 15 Nov' },
  },
]

/** The committed benchmark (graph/benchmark/results/2026-10-17-falkordb-60001.json, FalkorDB 6.0.1). */
export type Outcome = 'answered' | 'missed' | 'withheld' | 'leaked'
export const QUESTIONS: { q: string; search: Outcome; handovers: Outcome }[] = [
  { q: 'Why does the reconciliation service retry only 3 times?', search: 'answered', handovers: 'answered' },
  { q: 'What was the recon retry limit before it was lowered?', search: 'answered', handovers: 'answered' },
  { q: 'Who decided to retry bank settlement calls 5 times, and why?', search: 'missed', handovers: 'answered' },
  { q: 'How do I deploy the reconciliation service?', search: 'missed', handovers: 'answered' },
  { q: 'Why do settlements run in 30 minute batches?', search: 'missed', handovers: 'answered' },
  { q: 'What does the recon runbook say about retries?', search: 'missed', handovers: 'answered' },
  { q: 'Why did we pause Google Ads?', search: 'answered', handovers: 'answered' },
  { q: 'What is the blended CAC target?', search: 'answered', handovers: 'answered' },
  { q: 'Why did we shift budget to Reels?', search: 'missed', handovers: 'answered' },
  { q: 'When does the Mixpanel contract renew?', search: 'answered', handovers: 'answered' },
  { q: 'What was the CAC target in the Q2 deck?', search: 'answered', handovers: 'answered' },
  { q: 'What did Arjun say about career plans in his 1:1?', search: 'leaked', handovers: 'withheld' },
  { q: 'What salary is Nisha asking for?', search: 'withheld', handovers: 'withheld' },
  { q: 'Who is our contact at AcmeBank?', search: 'answered', handovers: 'answered' },
  { q: 'How do I unstick a hung ledger export batch?', search: 'missed', handovers: 'answered' },
  { q: 'Who is the agency lead for our ad creatives?', search: 'answered', handovers: 'answered' },
  { q: 'How do I rebuild the UTM attribution sheet at month-end?', search: 'missed', handovers: 'answered' },
  { q: 'Who is our Mixpanel customer success contact?', search: 'answered', handovers: 'answered' },
]
