import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  rankBand, rankScan, qualifyingStatus, eligibilityChecks,
  instituteSummary, capacityRows, listCheck,
} from '../dist/domain.js';

const inst = [
  { id: 'i1', name: 'Alpha Medical College', state: 'Delhi', city: 'Delhi', type: 'Government' },
  { id: 'i2', name: 'Beta Institute', state: 'Kerala', city: 'Kochi', type: 'Private' },
];
const cut = (id, instituteId, course, quota, category, year, round, closingRank, extra = {}) => ({
  id, instituteId, course, quota, category, year, round,
  recordKind: 'cutoff', exam: 'NEET PG', dataStatus: 'verified',
  openingRank: Math.max(1, closingRank - 100), closingRank, allotmentCount: 2,
  specialty: 'General Medicine', program: 'MD', ...extra,
});
const records = [
  cut('a-r1', 'i1', 'M.D. General Medicine', 'All India', 'Open', 2025, 'Round 1', 5000),
  cut('a-r2', 'i1', 'M.D. General Medicine', 'All India', 'Open', 2025, 'Round 2', 8000),
  cut('b-r1', 'i2', 'M.D. General Medicine', 'All India', 'Open', 2025, 'Round 1', 20000),
  cut('c-r1', 'i2', 'M.D. Paediatrics', 'All India', 'OBC', 2025, 'Round 1', 12000, { specialty: 'Paediatrics' }),
  cut('d-r1', 'i1', 'M.D. Anatomy', 'All India', 'Open', 2025, 'Round 1', null, { specialty: 'Anatomy' }),
];
// d-r1 has no closing rank: openingRank math above would break, fix explicitly
records.at(-1).openingRank = null;

test('rankBand classifies strictly from historical closing rank', () => {
  assert.equal(rankBand(8000, 8000), 'reached');
  assert.equal(rankBand(9000, 8000), 'reached');
  assert.equal(rankBand(7500, 8000), 'near');
  assert.equal(rankBand(1000, 8000), 'beyond');
  assert.equal(rankBand(null, 8000), null);
  assert.equal(rankBand(8000, null), null);
});

test('rankScan dedupes to latest observation per pool and counts reached pools', () => {
  const scan = rankScan(records, { rank: 10000 }, inst);
  // Pools: a (latest 8000 -> beyond at rank 10000? 8000<10000 and >=9000? no -> beyond), b (20000 reached), c (12000 reached), d excluded (no rank)
  assert.equal(scan.totalPools, 3);
  assert.equal(scan.reachedCount, 2);
  const a = scan.pools.find(p => p.record.id === 'a-r2');
  assert.ok(a, 'latest round wins for pool a');
  assert.equal(a.history.length, 2);
  assert.equal(scan.pools.filter(p => p.record.instituteId === 'i1' && p.record.course.includes('General')).length, 1);
});

test('rankScan respects category and state filters', () => {
  const scan = rankScan(records, { rank: 10000, category: 'OBC' }, inst);
  assert.equal(scan.totalPools, 1);
  assert.equal(scan.reachedCount, 1);
  const byState = rankScan(records, { rank: 10000, state: 'Delhi' }, inst);
  assert.ok(byState.pools.every(p => p.record.instituteId === 'i1'));
});

test('rankScan without a valid rank reports unavailable', () => {
  assert.equal(rankScan(records, {}, inst).available, false);
  assert.equal(rankScan(records, { rank: -5 }, inst).available, false);
});

const scale = {
  maximum: 720, sourceUrl: 'https://example.org/notice.pdf',
  qualifyingThresholds: [
    { category: 'General/EWS', percentile: 50, score: 262 },
    { category: 'SC/ST/OBC including PwBD', percentile: 40, score: 226 },
  ],
};

test('qualifyingStatus compares score with published thresholds only', () => {
  const q = qualifyingStatus(300, scale);
  assert.equal(q.available, true);
  assert.deepEqual(q.results.map(r => r.meets), [true, true]);
  assert.deepEqual(qualifyingStatus(240, scale).results.map(r => r.meets), [false, true]);
  assert.equal(qualifyingStatus(9999, scale).available, false);
  assert.equal(qualifyingStatus(null, scale).available, false);
});

test('eligibilityChecks never claims seat eligibility and flags unknowns', () => {
  const checks = eligibilityChecks({ score: 300, thresholdCategory: 'General/EWS', internshipByCutoff: 'unknown', registered: 'yes' }, scale);
  assert.ok(checks.some(c => c.status === 'verify'));
  assert.ok(checks.every(c => !/you are eligible/i.test(c.detail)));
  const low = eligibilityChecks({ score: 100, thresholdCategory: 'General/EWS', internshipByCutoff: 'yes', registered: 'yes' }, scale);
  assert.ok(low.some(c => c.status === 'not-met'));
});

test('instituteSummary aggregates one institute', () => {
  const seats = [
    { id: 's1', instituteId: 'i1', recordKind: 'seat-matrix', seats: 4, course: 'M.D. General Medicine', specialty: 'General Medicine', program: 'MD', quota: 'All India', category: 'Open', year: 2026, round: 'Round 1' },
    { id: 's2', instituteId: 'i1', recordKind: 'seat-matrix', seats: 2, course: 'M.S. General Surgery', specialty: 'General Surgery', program: 'MS', quota: 'All India', category: 'Open', year: 2026, round: 'Round 1' },
  ];
  const s = instituteSummary([...records, ...seats], 'i1');
  assert.equal(s.totalSeats, 6);
  assert.equal(s.seatPools, 2);
  assert.ok(s.specialties.includes('General Medicine'));
});

test('capacityRows separates pools with and without matched history', () => {
  const rows = capacityRows([
    { id: 's1', instituteId: 'i1', recordKind: 'seat-matrix', seats: 4, specialty: 'General Medicine', historicalClosingRank: 8000, historicalYear: 2025, historicalRound: 'Round 2' },
    { id: 's2', instituteId: 'i2', recordKind: 'seat-matrix', seats: 1, specialty: 'Anatomy' },
    { id: 'c1', instituteId: 'i1', recordKind: 'cutoff', seats: null },
  ]);
  assert.equal(rows.withHistory.length, 1);
  assert.equal(rows.withoutHistory.length, 1);
  assert.equal(rows.totalSeats, 5);
});

test('listCheck flags duplicate pools and zero-seat entries', () => {
  const items = [
    { id: 'x1', instituteId: 'i1', course: 'M.D. General Medicine', quota: 'All India', category: 'Open', seats: 2, recordKind: 'seat-matrix', historicalClosingRank: 5000 },
    { id: 'x2', instituteId: 'i1', course: 'M.D. General Medicine', quota: 'All India', category: 'Open', seats: 2, recordKind: 'seat-matrix', historicalClosingRank: 5000 },
    { id: 'x3', instituteId: 'i2', course: 'M.D. Anatomy', quota: 'All India', category: 'Open', seats: 0, recordKind: 'seat-matrix' },
  ];
  const warnings = listCheck(items);
  assert.ok(warnings.some(w => w.type === 'duplicate-pool'));
  assert.ok(warnings.some(w => w.type === 'zero-seats'));
  assert.ok(warnings.some(w => w.type === 'no-cutoff'));
  assert.deepEqual(listCheck([items[0]]), []);
});
