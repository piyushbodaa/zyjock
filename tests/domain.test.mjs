import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  rankBand, rankScan, qualifyingStatus, eligibilityChecks,
  instituteSummary, capacityRows, listCheck,
  roundDrift, poolHistory, buildSharePayload, parseSharePayload,
  encodeShareToken, decodeShareToken, listDiff,
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

test('roundDrift measures first-to-last closing movement per pool', () => {
  const drift = roundDrift(records, {}, inst);
  const a = drift.pools.find(p => p.record.id === 'a-r2');
  assert.equal(a.firstClosing, 5000);
  assert.equal(a.lastClosing, 8000);
  assert.equal(a.drift, 3000);
  assert.equal(a.direction, 'loosened');
  assert.equal(drift.pools.filter(p => p.observations >= 2).length, 1);
  assert.equal(drift.medianDrift, 3000);
  assert.equal(drift.loosenedShare, 1);
});

test('roundDrift respects category filter and needs 2+ observations for medians', () => {
  const drift = roundDrift(records, { category: 'OBC' }, inst);
  assert.equal(drift.pools.length, 1);
  assert.equal(drift.medianDrift, null);
});

test('poolHistory groups one institute pools with ordered rounds and rank gap', () => {
  const pools = poolHistory(records, 'i1', 10000);
  const med = pools.find(p => p.course.includes('General Medicine'));
  assert.deepEqual(med.history.map(h => h.round), ['Round 1', 'Round 2']);
  assert.equal(med.latestClosing, 8000);
  assert.equal(med.gap, -2000); // needed a 2,000 better (lower) rank than 10,000
  assert.equal(poolHistory(records, 'i1', null).find(p => p.course.includes('General')).gap, null);
});

test('poolHistory follows historyIds to historical institute entities', () => {
  const seat = { id: 's-link', instituteId: 'i-current', recordKind: 'seat-matrix', seats: 2, course: 'M.D. General Medicine', historyIds: ['a-r1', 'a-r2'] };
  const pools = poolHistory([...records, seat], 'i-current', 9000);
  assert.equal(pools.length, 1);
  assert.equal(pools[0].latestClosing, 8000);
  assert.equal(pools[0].gap, -1000);
});

test('share payload round-trips and tampered input fails closed', () => {
  const list = { name: 'My list', items: ['r1', 'r2'], tags: { r1: 'dream' } };
  const byId = { r1: { dataset: 'mcc' }, r2: { dataset: 'state:Kerala' } };
  const payload = buildSharePayload(list, id => byId[id]);
  assert.deepEqual(payload.items, [['r1', 'mcc'], ['r2', 'state:Kerala']]);
  const token = encodeShareToken(payload);
  assert.deepEqual(parseSharePayload(JSON.parse(decodeShareToken(token))), payload);
  assert.equal(parseSharePayload(null), null);
  assert.equal(parseSharePayload({ v: 99, items: [] }), null);
  assert.equal(parseSharePayload({ v: 1, name: 'x', items: 'nope' }), null);
  assert.equal(parseSharePayload({ v: 1, name: 'x', items: [['ok', 'mcc'], [42, 'mcc']] }), null);
  assert.equal(decodeShareToken('!!!not-base64!!!'), null);
});

test('rankScan and roundDrift never mix state merit ranks into AIR results', () => {
  const stateRec = cut('st-1', 'i2', 'M.D. General Medicine', 'State Quota', 'Open', 2025, 'Round 1', 90000, { rankType: 'State merit rank', quota: 'State Quota' });
  const scan = rankScan([...records, stateRec], { rank: 10000 }, inst);
  assert.equal(scan.pools.some(p => p.record.id === 'st-1'), false);
  const scanState = rankScan([...records, stateRec], { rank: 10000, rankType: 'State merit rank' }, inst);
  assert.equal(scanState.totalPools, 1);
  const drift = roundDrift([...records, stateRec], {}, inst);
  assert.equal(drift.pools.some(p => p.record.id === 'st-1'), false);
});

test('poolHistory withholds AIR gap on non-AIR scales', () => {
  const stateRec = cut('st-2', 'i1', 'M.D. Anatomy', 'State Quota', 'Open', 2025, 'Round 1', 3000, { rankType: 'State merit rank', specialty: 'Anatomy' });
  const pools = poolHistory([stateRec], 'i1', 10000);
  assert.equal(pools[0].gap, null);
  assert.equal(pools[0].rankScale, 'State merit rank');
});

test('listDiff reports common, exclusive and moved entries', () => {
  const d = listDiff(['a', 'b', 'c'], ['b', 'a', 'd']);
  assert.deepEqual(d.common.sort(), ['a', 'b']);
  assert.deepEqual(d.onlyA, ['c']);
  assert.deepEqual(d.onlyB, ['d']);
  assert.deepEqual(d.moved, [{ id: 'a', from: 1, to: 2 }, { id: 'b', from: 2, to: 1 }]);
  assert.deepEqual(listDiff([], []).moved, []);
});
