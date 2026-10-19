/**
 * Zyjock's browser-only counselling data tools.
 *
 * Import columns: instituteId OR instituteName, exam, course; optional id, city,
 * state, type, counselling, quota, category, year, round, openingRank,
 * closingRank, seats, annualFee, monthlyStipend, bondYears, bondPenalty,
 * previousSeats, sourceUrl, sourceLabel. Unknown numbers must stay blank.
 * Imported rows always remain unverified, regardless of a supplied status.
 */

const NUMERIC_FIELDS = ['year', 'openingRank', 'closingRank', 'seats', 'annualFee', 'monthlyStipend', 'bondYears', 'bondPenalty', 'previousSeats'];
const DEFAULT_COLUMNS = ['id', 'instituteId', 'instituteName', 'exam', 'course', 'counselling', 'quota', 'category', 'year', 'round', 'rankType', 'openingRank', 'closingRank', 'seats', 'annualFee', 'monthlyStipend', 'bondYears', 'bondPenalty', 'previousSeats', 'dataStatus', 'sourceUrl', 'sourceLabel'];
const EMPTY = new Set(['', '-', '—', 'na', 'n/a', 'null', 'unknown', 'not available']);
const text = value => value == null ? '' : String(value).trim();
const lower = value => text(value).toLowerCase();
const present = value => value != null && text(value) !== '';
const unrestricted = value => !present(value) || ['all', 'any'].includes(lower(value));
const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

function numberOrNull(value) {
  if (value == null || EMPTY.has(lower(value))) return null;
  if (typeof value === 'boolean') return null;
  const cleaned = text(value).replace(/[,₹\s]/g, '');
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(cleaned)) return null;
  const result = Number(cleaned);
  return Number.isFinite(result) ? result : null;
}

function canonicalExam(value) {
  const candidate = text(value).toUpperCase().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ');
  const aliases = { UG: 'NEET UG', PG: 'NEET PG', NEETUG: 'NEET UG', NEETPG: 'NEET PG', NEETMDS: 'NEET MDS', INICET: 'INICET', 'INI CET': 'INICET', NEETSS: 'NEET SS', DNBPDCET: 'DNB PDCET' };
  return aliases[candidate] || candidate;
}

function instituteMap(institutes = []) {
  if (institutes instanceof Map) return institutes;
  if (!Array.isArray(institutes)) return new Map(Object.entries(institutes || {}));
  return new Map(institutes.map(institute => [String(institute.id), institute]));
}

function institution(record, map) {
  return map.get(String(record.instituteId)) || record.institute || {
    name: record.instituteName || record.instituteId,
    state: record.state,
    city: record.city,
    type: record.type,
  };
}

function matches(value, selected) {
  if (unrestricted(selected)) return true;
  if (Array.isArray(selected)) return !selected.length || selected.some(item => lower(item) === lower(value));
  return lower(value) === lower(selected);
}

function validURL(value) {
  try { return ['http:', 'https:'].includes(new URL(value).protocol); } catch { return false; }
}

/** Copy and normalize one record; absent numeric facts remain null. */
export function normalizeRecord(input = {}) {
  const record = { ...input };
  for (const field of NUMERIC_FIELDS) record[field] = numberOrNull(input[field]);
  for (const field of ['id', 'instituteId', 'course', 'counselling', 'quota', 'category', 'round', 'sourceUrl', 'sourceLabel']) record[field] = text(input[field]);
  record.exam = canonicalExam(input.exam);
  record.dataStatus = ['verified', 'imported'].includes(input.dataStatus) ? input.dataStatus : 'demo';
  return record;
}

/** Rank means an observed closing rank >= the supplied rank, not a prediction. */
export function filterRecords(records = [], filters = {}, institutes = []) {
  const map = instituteMap(institutes);
  const rank = numberOrNull(filters.rank);
  const minimumFee = numberOrNull(filters.minFee);
  const maximumFee = numberOrNull(filters.maxFee);
  const query = lower(filters.search);
  const includeUnknown = filters.includeUnknown === true || filters.includeUnknown === 'true';
  return records.filter(record => {
    const institute = institution(record, map);
    if (query && !lower([institute.name, institute.city, institute.state, record.instituteName, record.course, record.quota, record.category, record.counselling].filter(Boolean).join(' ')).includes(query)) return false;
    if (!unrestricted(filters.exam) && canonicalExam(record.exam) !== canonicalExam(filters.exam)) return false;
    if (!matches(institute.state || record.state, filters.state)) return false;
    if (!matches(institute.city || record.city, filters.city)) return false;
    if (!matches(institute.type || record.type, filters.type)) return false;
    for (const field of ['course', 'specialty', 'program', 'counselling', 'quota', 'category', 'year', 'round', 'rankType']) if (!matches(record[field], filters[field])) return false;
    if (!unrestricted(filters.dataMode) && lower(record.dataStatus) !== lower(filters.dataMode)) return false;
    if (rank != null && rank > 0) {
      if ((record.rankType || 'Not specified') !== (filters.rankType || 'NEET PG AIR')) return false;
      const cutoff = numberOrNull(record.recordKind==='seat-matrix'?record.historicalClosingRank:record.closingRank);
      if (cutoff == null ? !includeUnknown : cutoff < rank) return false;
    }
    if (minimumFee != null || maximumFee != null) {
      const fee = numberOrNull(record.annualFee);
      if (fee == null) { if (!includeUnknown) return false; }
      else if ((minimumFee != null && fee < minimumFee) || (maximumFee != null && fee > maximumFee)) return false;
    }
    return true;
  });
}

function compareNumber(a, b, direction = 1) {
  const left = numberOrNull(a), right = numberOrNull(b);
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  return (left - right) * direction;
}

function sorter(sort, map) {
  const aliases = {
    fee: 'annualFee', fees: 'annualFee', 'fee-asc': 'annualFee', 'fees-asc': 'annualFee', 'fee-low': 'annualFee', 'annualFee-asc': 'annualFee',
    'fee-desc': '-annualFee', 'fees-desc': '-annualFee', 'annualFee-desc': '-annualFee',
    rank: 'closingRank', 'rank-asc': 'closingRank', 'closingRank-asc': 'closingRank',
    'rank-desc': '-closingRank', 'closingRank-desc': '-closingRank',
    seats: '-seats', 'seats-desc': '-seats', 'seats-asc': 'seats',
    stipend: '-monthlyStipend', 'stipend-desc': '-monthlyStipend', 'stipend-asc': 'monthlyStipend',
    bond: 'bondYears', 'bond-asc': 'bondYears', 'name-asc': 'name', alphabetical: 'name',
    'year-desc': '-year', 'year-asc': 'year', 'seat-change': '-seatDelta',
  };
  const input = typeof sort === 'object' && sort ? `${sort.direction === 'desc' ? '-' : ''}${sort.field}` : (sort || 'name');
  const key = aliases[input] || input;
  const descending = key.startsWith('-');
  const field = descending ? key.slice(1) : key;
  const direction = descending ? -1 : 1;
  return (a, b) => {
    const ia = institution(a, map), ib = institution(b, map);
    if (field === 'closingRank') return compareNumber(a.recordKind==='seat-matrix'?a.historicalClosingRank:a.closingRank,b.recordKind==='seat-matrix'?b.historicalClosingRank:b.closingRank,direction);
    if (NUMERIC_FIELDS.includes(field)) return compareNumber(a[field], b[field], direction);
    if (field === 'seatDelta') return compareNumber(compareMetrics(a).seatDelta, compareMetrics(b).seatDelta, direction);
    const first = ['name', 'city', 'state', 'type'].includes(field) ? ia[field] : a[field];
    const second = ['name', 'city', 'state', 'type'].includes(field) ? ib[field] : b[field];
    return collator.compare(text(first), text(second)) * direction;
  };
}

/** Stable sorting with missing numeric values always last; never mutates input. */
export function sortRecords(records = [], sort = 'name', institutes = []) {
  const map = instituteMap(institutes);
  const compare = sorter(sort, map);
  return records.map((record, index) => ({ record, index })).sort((a, b) => compare(a.record, b.record) || a.index - b.index).map(item => item.record);
}

export function compareMetrics(input = {}) {
  const record = normalizeRecord(input);
  const seatDelta = record.seats == null || record.previousSeats == null ? null : record.seats - record.previousSeats;
  return {
    openingRank: record.openingRank, closingRank: record.closingRank,
    annualFee: record.annualFee, monthlyStipend: record.monthlyStipend,
    annualStipend: record.monthlyStipend == null ? null : record.monthlyStipend * 12,
    netAnnualCost: record.annualFee == null || record.monthlyStipend == null ? null : record.annualFee - record.monthlyStipend * 12,
    bondYears: record.bondYears, bondPenalty: record.bondPenalty,
    seats: record.seats, previousSeats: record.previousSeats, seatDelta,
    seatChangePercent: seatDelta == null || !record.previousSeats ? null : seatDelta / record.previousSeats * 100,
    dataStatus: record.dataStatus, sourceUrl: record.sourceUrl, sourceLabel: record.sourceLabel,
  };
}

/** Deterministic preference ordering. No admission probabilities are inferred. */
export function generateChoices(records = [], preferences = {}, institutes = []) {
  const map = instituteMap(institutes);
  let choices = filterRecords(records, { ...preferences, ...preferences.filters }, institutes);
  const preferredCities = preferences.cities || preferences.preferredCities || [];
  const preferredStates = preferences.states || preferences.preferredStates || [];
  const preferredCourses = preferences.courses || preferences.preferredCourses || [];
  const order = Array.isArray(preferences.priorities) && preferences.priorities.length ? preferences.priorities : [preferences.sort || preferences.priority || 'fees', 'rank', 'name'];
  const preferenceIndex = (list, value) => { const position = list.findIndex(item => lower(item) === lower(value)); return position < 0 ? list.length : position; };
  const compare = order.map(priority => {
    if (['city', 'location'].includes(priority) && preferredCities.length) return (a, b) => preferenceIndex(preferredCities, institution(a, map).city) - preferenceIndex(preferredCities, institution(b, map).city);
    if (priority === 'state' && preferredStates.length) return (a, b) => preferenceIndex(preferredStates, institution(a, map).state) - preferenceIndex(preferredStates, institution(b, map).state);
    if (priority === 'course' && preferredCourses.length) return (a, b) => preferenceIndex(preferredCourses, a.course) - preferenceIndex(preferredCourses, b.course);
    return sorter(priority, map);
  });
  choices = choices.map((record, index) => ({ record, index })).sort((a, b) => {
    for (const comparator of compare) { const value = comparator(a.record, b.record); if (value) return value; }
    return a.index - b.index;
  }).map(item => item.record);
  if (preferences.deduplicate) {
    const seen = new Set();
    choices = choices.filter(record => { const key = [record.instituteId, record.exam, record.course, record.quota, record.category].join('|'); if (seen.has(key)) return false; seen.add(key); return true; });
  }
  const limit = numberOrNull(preferences.limit);
  return limit != null && limit >= 0 ? choices.slice(0, Math.floor(limit)) : choices;
}

/**
 * Curves must be explicitly supplied for one exam: [{exam,difficulty?,year,
 * sourceUrl,sourceLabel|label,dataStatus:'verified'|'demo',points:[{marks|score,rank}]}].
 * Difficulty only selects an explicitly labelled curve; it never changes scores
 * or fabricates a curve. Curves without a difficulty label are fixed.
 * Interpolation stays inside the supplied domain. Demo results stay demo.
 */
export function rankEstimate(marks, difficulty = null, curves = []) {
  const value = numberOrNull(marks);
  if (value == null) return { available: false, reason: 'Enter valid marks to inspect a sourced rank curve.' };
  const supplied = Array.isArray(curves) ? curves : curves?.curves || [];
  const candidates = supplied.filter(curve => curve && (curve.dataStatus === 'demo' || validURL(curve.sourceUrl)) && (!present(curve.difficulty) || (present(difficulty) && lower(curve.difficulty) === lower(difficulty))));
  const exams = new Set(candidates.map(curve => canonicalExam(curve.exam)).filter(Boolean));
  if (exams.size > 1) return { available: false, reason: 'Select curves for one exam before estimating a rank. Different exams have different marks and rank scales.' };
  const curve = candidates.sort((a, b) => Number(present(b.difficulty)) - Number(present(a.difficulty)) || (Number(b.year) || 0) - (Number(a.year) || 0))[0];
  if (!curve) return { available: false, reason: 'No sourced marks-to-rank curve is available. Marks alone cannot determine a counselling rank.' };
  const points = (curve.points || []).map(point => ({ marks: numberOrNull(point.marks) ?? numberOrNull(point.score), rank: numberOrNull(point.rank) })).filter(point => point.marks != null && point.rank != null && point.rank > 0).sort((a, b) => a.marks - b.marks);
  if (points.length < 2 || points.some((point, index) => index > 0 && (point.marks === points[index - 1].marks || point.rank > points[index - 1].rank))) return { available: false, reason: 'The supplied curve does not contain a valid monotonic marks-to-rank series.' };
  if (value < points[0].marks || value > points.at(-1).marks) return { available: false, reason: `Marks are outside the supplied curve (${points[0].marks}–${points.at(-1).marks}).` };
  const exact = points.find(point => point.marks === value);
  const upperIndex = points.findIndex(point => point.marks >= value);
  const low = exact || points[upperIndex - 1];
  const high = exact || points[upperIndex];
  const rank = exact ? exact.rank : low.rank + (high.rank - low.rank) * (value - low.marks) / (high.marks - low.marks);
  const difficultyApplied = present(curve.difficulty);
  const dataStatus = curve.dataStatus === 'demo' ? 'demo' : curve.dataStatus === 'verified' ? 'verified' : 'imported';
  const curveKind = dataStatus === 'demo' ? 'fictional demo' : dataStatus === 'verified' ? 'historical' : 'unverified supplied';
  const method = `${exact ? 'Exact supplied point' : 'Linear interpolation between supplied points'} on ${difficultyApplied ? 'the' : 'a fixed'} ${curveKind} curve. ${difficultyApplied ? `Selected curve is explicitly labelled difficulty ${curve.difficulty}.` : 'No difficulty adjustment is supported by this curve.'}`;
  return {
    available: true, rank: Math.round(rank), lowerRank: Math.min(low.rank, high.rank), upperRank: Math.max(low.rank, high.rank),
    dataStatus, sourceLabel: curve.sourceLabel || curve.label || 'Supplied rank curve', sourceUrl: curve.sourceUrl || '', year: curve.year || null,
    exam: canonicalExam(curve.exam), difficultyApplied, difficulty: difficultyApplied ? curve.difficulty : null,
    minimumMarks: points[0].marks, maximumMarks: points.at(-1).marks, lowerMarks: low.marks, upperMarks: high.marks, method,
    rangeMeaning: exact ? 'The supplied curve has an exact point at these marks. This is not an uncertainty interval.' : 'These are the ranks at the two surrounding curve points, not a confidence interval or admission probability.',
  };
}

function csvCell(value) {
  let cell = value == null ? '' : String(value);
  // Prevent a spreadsheet from interpreting imported text as a formula.
  if (/^[\s\u0000-\u001f]*[=+\-@]/.test(cell) || /^[\t\r\n]/.test(cell)) cell = `'${cell}`;
  return /[",\r\n]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell;
}

/** Columns can be field names or {key,label,value(row)} definitions. */
export function buildCSV(rows = [], columns = DEFAULT_COLUMNS) {
  const definitions = columns.map(column => typeof column === 'string' ? { key: column, label: column } : column);
  return [definitions.map(column => csvCell(column.label || column.key)).join(','), ...rows.map(row => definitions.map(column => csvCell(typeof column.value === 'function' ? column.value(row) : row[column.key])).join(','))].join('\r\n');
}

/** RFC-style quoted fields, escaped quotes, commas and embedded newlines. */
export function parseCSV(input = '') {
  const source = String(input).replace(/^\uFEFF/, '');
  const matrix = [], parseErrors = [];
  let row = [], cell = '', inQuotes = false, closedQuote = false, line = 1;
  const finishCell = () => { row.push(cell); cell = ''; closedQuote = false; };
  const finishRow = () => { finishCell(); if (row.some(value => value.trim() !== '')) matrix.push(row); row = []; };
  for (let index = 0; index < source.length; index++) {
    const character = source[index];
    if (inQuotes) {
      if (character === '"') {
        if (source[index + 1] === '"') { cell += '"'; index++; }
        else { inQuotes = false; closedQuote = true; }
      } else { cell += character; if (character === '\n') line++; }
      continue;
    }
    if (character === '"') {
      if (cell === '' && !closedQuote) inQuotes = true;
      else { parseErrors.push({ row: line, field: '', message: 'Unexpected quote in an unquoted field.' }); cell += character; }
    } else if (character === ',') finishCell();
    else if (character === '\n' || character === '\r') {
      if (character === '\r' && source[index + 1] === '\n') index++;
      finishRow(); line++;
    } else {
      if (closedQuote && character.trim() !== '') parseErrors.push({ row: line, field: '', message: 'Unexpected text after a quoted field.' });
      if (!closedQuote || character.trim() !== '') cell += character;
    }
  }
  if (inQuotes) parseErrors.push({ row: line, field: '', message: 'Unterminated quoted field.' });
  if (row.length || cell !== '' || closedQuote) finishRow();
  const headers = (matrix.shift() || []).map(header => header.trim());
  if (new Set(headers.map(lower)).size !== headers.length) parseErrors.push({ row: 1, field: '', message: 'Duplicate column headings are not supported.' });
  if (headers.some(header => !header)) parseErrors.push({ row: 1, field: '', message: 'Every column needs a heading.' });
  const rows = matrix.map((values, index) => {
    if (values.length !== headers.length) parseErrors.push({ row: index + 2, field: '', message: `Expected ${headers.length} columns but found ${values.length}.` });
    return Object.fromEntries(headers.map((header, column) => [header, values[column] ?? '']));
  });
  Object.defineProperty(rows, 'errors', { value: parseErrors, enumerable: false });
  Object.defineProperty(rows, 'columns', { value: headers, enumerable: false });
  return rows;
}

const HEADER_ALIASES = {
  institute: 'instituteName', college: 'instituteName', collegename: 'instituteName', institutename: 'instituteName', instituteid: 'instituteId', collegeid: 'instituteId',
  openingrank: 'openingRank', closingrank: 'closingRank', cutoff: 'closingRank', cutoffrank: 'closingRank', annualfee: 'annualFee', fee: 'annualFee', fees: 'annualFee', annualfees: 'annualFee',
  monthlystipend: 'monthlyStipend', stipend: 'monthlyStipend', bondyears: 'bondYears', bondpenalty: 'bondPenalty', previousseats: 'previousSeats', sourceurl: 'sourceUrl', sourcelabel: 'sourceLabel', datastatus: 'dataStatus',
};

export function validateImport(rows = []) {
  const errors = [...(rows.errors || [])], warnings = [], records = [];
  if (!Array.isArray(rows) || !rows.length) return { valid: false, records, errors: [{ row: 1, field: '', message: 'The CSV contains no data rows.' }], warnings };
  const ids = new Set();
  rows.forEach((original, index) => {
    const rowNumber = index + 2;
    const input = Object.fromEntries(Object.entries(original).map(([key, value]) => {
      const compact = lower(key).replace(/[\s_-]/g, '');
      return [HEADER_ALIASES[compact] || compact, value];
    }));
    const rowErrors = [];
    const fail = (field, message) => rowErrors.push({ row: rowNumber, field, message });
    if (!present(input.instituteId) && !present(input.instituteName)) fail('instituteId', 'Provide an instituteId or instituteName.');
    if (canonicalExam(input.exam) !== 'NEET PG') fail('exam', 'This workspace accepts NEET PG records only.');
    if (!present(input.course)) fail('course', 'Provide a course.');
    for (const field of NUMERIC_FIELDS) {
      const value = numberOrNull(input[field]);
      if (present(input[field]) && !EMPTY.has(lower(input[field])) && value == null) fail(field, 'Use a number or leave unknown values blank.');
      if (value != null && value < 0) fail(field, 'Values cannot be negative.');
      if (value != null && ['openingRank', 'closingRank', 'seats', 'previousSeats', 'year'].includes(field) && !Number.isInteger(value)) fail(field, 'Use a whole number.');
      if (value === 0 && ['openingRank', 'closingRank'].includes(field)) fail(field, 'Ranks must be greater than zero.');
      if (field === 'year' && value != null && (value < 1900 || value > 2200)) fail(field, 'Provide a four-digit counselling year.');
    }
    const opening = numberOrNull(input.openingRank), closing = numberOrNull(input.closingRank);
    if (opening != null && closing != null && opening > closing) fail('closingRank', 'Closing rank cannot be smaller than opening rank.');
    if (present(input.sourceUrl) && !validURL(input.sourceUrl)) fail('sourceUrl', 'Use an http or https source URL.');
    const instituteId = text(input.instituteId) || `import-${text(input.instituteName).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || index + 1}`;
    const id = text(input.id) || `import-${instituteId}-${index + 1}`;
    if (ids.has(id)) fail('id', 'Duplicate record id in this import.');
    ids.add(id);
    if (input.dataStatus === 'verified') warnings.push({ row: rowNumber, field: 'dataStatus', message: 'Imported data remains unverified until independently checked.' });
    if (rowErrors.length) errors.push(...rowErrors);
    else records.push(normalizeRecord({ ...input, id, instituteId, imported: true, dataStatus: 'imported', sourceLabel: input.sourceLabel || 'User imported · unverified' }));
  });
  return { valid: errors.length === 0, records, errors, warnings };
}

/** Keep years and rounds separate within each college/course/quota/category. */
export function groupCutoffs(records = []) {
  const groups = new Map();
  for (const record of records) {
    const fields = ['instituteId', 'exam', 'course', 'counselling', 'quota', 'category'];
    const key = JSON.stringify(fields.map(field => record[field] ?? ''));
    if (!groups.has(key)) groups.set(key, { key, ...Object.fromEntries(fields.map(field => [field, record[field]])), records: [], points: [] });
    groups.get(key).records.push(record);
  }
  for (const group of groups.values()) {
    group.records.sort((a, b) => compareNumber(a.year, b.year) || collator.compare(text(a.round), text(b.round)));
    group.points = group.records.map(record => ({ id: record.id, year: numberOrNull(record.year), round: record.round, openingRank: numberOrNull(record.openingRank), closingRank: numberOrNull(record.closingRank), dataStatus: record.dataStatus, sourceUrl: record.sourceUrl, sourceLabel: record.sourceLabel }));
  }
  return [...groups.values()];
}

export function summarizeData(data = {}) {
  const records = Array.isArray(data) ? data : data.records || [];
  const institutes = Array.isArray(data.institutes) ? data.institutes : [];
  const unique = values => [...new Set(values.filter(present))].sort((a, b) => collator.compare(text(a), text(b)));
  const verified = records.filter(record => record.dataStatus === 'verified').length;
  return {
    total: records.length, recordCount: records.length, instituteCount: new Set(records.map(record => record.instituteId).filter(present)).size,
    verified, demo: records.filter(record => record.dataStatus === 'demo').length, imported: records.filter(record => record.dataStatus === 'imported').length,
    years: unique(records.map(record => numberOrNull(record.year))).sort((a, b) => b - a),
    exams: unique(records.map(record => record.exam)), courses: unique(records.map(record => record.course)),
    states: unique(institutes.map(institute => institute.state).concat(records.map(record => record.state))),
    quotas: unique(records.map(record => record.quota)), categories: unique(records.map(record => record.category)), rounds: unique(records.map(record => record.round)),
    sourced: records.filter(record => validURL(record.sourceUrl)).length,
    withCutoffs: records.filter(record => numberOrNull(record.closingRank) != null).length,
    withFees: records.filter(record => numberOrNull(record.annualFee) != null).length,
    withSeats: records.filter(record => numberOrNull(record.seats) != null).length,
    verifiedWithCutoffs: records.filter(record => record.dataStatus === 'verified' && numberOrNull(record.closingRank) != null).length,
  };
}

/* ------------------------------------------------------------------ */
/* NEET PG planning helpers. Every result is a historical comparison:  */
/* nothing here predicts an allotment or decides eligibility.          */
/* ------------------------------------------------------------------ */

const ROUND_ORDER = { 'round 1': 1, 'round 2': 2, 'round 3': 3, 'round 4': 4, 'stray vacancy': 5, 'mop up': 6, 'mop-up': 6 };
const roundRank = round => ROUND_ORDER[lower(round)] ?? 0;
const poolKeyOf = record => [record.instituteId, record.courseCode || record.course, record.quota, record.category].map(v => lower(v)).join('|');
const closingOf = record => numberOrNull(record.recordKind === 'seat-matrix' ? record.historicalClosingRank : record.closingRank);

/** Display band only: how a past closing rank compares with a candidate rank. */
export function rankBand(closingRank, rank) {
  const closing = numberOrNull(closingRank), value = numberOrNull(rank);
  if (closing == null || value == null || value <= 0) return null;
  if (closing >= value) return 'reached';
  if (closing >= value * 0.9) return 'near';
  return 'beyond';
}

/**
 * Count and list distinct seat pools whose latest historical observation
 * closed at or beyond the supplied rank. One pool = institute + course +
 * quota + allotted seat category. Filters match exactly (blank = all).
 */
export function rankScan(records = [], options = {}, institutes = []) {
  const rank = numberOrNull(options.rank);
  if (rank == null || rank <= 0) return { available: false, reason: 'Enter your NEET PG All India rank from your official scorecard.', pools: [], totalPools: 0, reachedCount: 0, nearCount: 0, beyondCount: 0, bySpecialty: [] };
  const map = instituteMap(institutes);
  const wanted = (value, selected) => unrestricted(selected) || lower(value) === lower(selected);
  const groups = new Map();
  for (const record of records) {
    if (record.recordKind !== 'cutoff' && closingOf(record) == null) continue;
    const closing = closingOf(record);
    if (closing == null) continue;
    const inst = institution(record, map);
    if (!wanted(record.category, options.category) || !wanted(record.quota, options.quota)
      || !wanted(record.specialty, options.specialty) || !wanted(record.program, options.program)
      || !wanted(inst.state || record.state, options.state)
      || !wanted(record.year, options.year)) continue;
    const key = poolKeyOf(record);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(record);
  }
  const pools = [...groups.values()].map(history => {
    const sorted = [...history].sort((a, b) => compareNumber(a.year, b.year) || roundRank(a.round) - roundRank(b.round));
    const latest = sorted.at(-1);
    return { record: latest, closingRank: closingOf(latest), band: rankBand(closingOf(latest), rank), history: sorted };
  }).sort((a, b) => compareNumber(a.closingRank, b.closingRank));
  const reached = pools.filter(p => p.band === 'reached');
  const specialtyCounts = new Map();
  for (const p of reached) specialtyCounts.set(p.record.specialty || p.record.course, (specialtyCounts.get(p.record.specialty || p.record.course) || 0) + 1);
  return {
    available: true, rank, pools,
    totalPools: pools.length,
    reachedCount: reached.length,
    nearCount: pools.filter(p => p.band === 'near').length,
    beyondCount: pools.filter(p => p.band === 'beyond').length,
    reachedInstitutes: new Set(reached.map(p => p.record.instituteId)).size,
    bySpecialty: [...specialtyCounts].map(([specialty, count]) => ({ specialty, count })).sort((a, b) => b.count - a.count),
    note: 'Counts distinct institute/course/quota/category pools using each pool\'s latest bundled observation. A past closing rank does not establish current eligibility or a future allotment.',
  };
}

/** Compare a score with published NEET PG qualifying thresholds. Not a rank estimate. */
export function qualifyingStatus(score, scoreScale = {}) {
  const value = numberOrNull(score);
  const thresholds = Array.isArray(scoreScale?.qualifyingThresholds) ? scoreScale.qualifyingThresholds : [];
  if (value == null || !thresholds.length) return { available: false, reason: 'Enter your official NEET PG score to compare it with the published qualifying thresholds.', results: [] };
  if (scoreScale.maximum != null && (value < 0 || value > Number(scoreScale.maximum))) return { available: false, reason: `Score must be between 0 and ${scoreScale.maximum}.`, results: [] };
  return {
    available: true, score: value, maximum: scoreScale.maximum ?? null, sourceUrl: scoreScale.sourceUrl || '',
    results: thresholds.map(t => ({ category: t.category, percentile: t.percentile ?? null, threshold: numberOrNull(t.score), meets: value >= numberOrNull(t.score) })),
    note: scoreScale.note || 'Qualifying thresholds only. They are not college admission cut-offs and do not convert marks to a rank.',
  };
}

/** Document self-check from published bulletin requirements. Never decides seat eligibility. */
export function eligibilityChecks(answers = {}, scoreScale = {}) {
  const checks = [];
  const q = qualifyingStatus(answers.score, scoreScale);
  const chosen = q.results.find(r => lower(r.category) === lower(answers.thresholdCategory));
  if (!q.available) checks.push({ id: 'qualification', label: 'NEET PG qualification', status: 'verify', detail: 'Enter your official score and select the threshold row that applies to you, then confirm qualification on your NBEMS scorecard.' });
  else if (!chosen) checks.push({ id: 'qualification', label: 'NEET PG qualification', status: 'verify', detail: 'Select the published threshold row that applies to you. Thresholds can be revised by notice; re-check before registration.' });
  else checks.push({ id: 'qualification', label: 'NEET PG qualification', status: chosen.meets ? 'met' : 'not-met', detail: chosen.meets ? `Your score meets the published ${chosen.category} threshold of ${chosen.threshold}. Keep the official scorecard ready; a revised notice can change thresholds.` : `Your score is below the published ${chosen.category} threshold of ${chosen.threshold}. Watch for any official percentile-reduction notice before assuming the position is final.` });
  const tri = (id, label, value, metDetail) => checks.push({ id, label, status: value === 'yes' ? 'met' : value === 'no' ? 'not-met' : 'verify', detail: value === 'yes' ? metDetail : value === 'no' ? 'This is listed as a requirement in the counselling bulletin material bundled with Zyjock. Resolve it before choice filling and confirm the exact rule in the current bulletin.' : 'Not answered. Confirm this against the current bulletin before you rely on any seat pool.' });
  tri('internship', 'Internship completion by the published cut-off', answers.internshipByCutoff, 'Keep your internship completion certificate ready for document verification.');
  tri('registration', 'MBBS qualification and medical registration', answers.registered, 'Keep your MBBS degree/provisional certificate and registration certificate ready.');
  checks.push({ id: 'pool-conditions', label: 'Seat-pool conditions (quota, category, domicile, institutional, minority, NRI)', status: 'verify', detail: 'Conditions differ by quota, category and authority, and Zyjock cannot decide them for an individual pool. Check every pool you save against the current MCC or state bulletin.' });
  return checks;
}

/** Aggregate every bundled record for one institute. */
export function instituteSummary(records = [], instituteId) {
  const mine = records.filter(r => String(r.instituteId) === String(instituteId));
  const seatRows = mine.filter(r => r.recordKind === 'seat-matrix');
  const cutoffRows = mine.filter(r => r.recordKind === 'cutoff');
  const uniq = values => [...new Set(values.filter(present))].sort((a, b) => collator.compare(text(a), text(b)));
  const closings = cutoffRows.map(r => numberOrNull(r.closingRank)).filter(v => v != null);
  return {
    instituteId, records: mine, seatRows, cutoffRows,
    seatPools: seatRows.length, cutoffPools: new Set(cutoffRows.map(poolKeyOf)).size,
    totalSeats: seatRows.reduce((sum, r) => sum + (numberOrNull(r.seats) || 0), 0),
    specialties: uniq(mine.map(r => r.specialty)), programs: uniq(mine.map(r => r.program)),
    quotas: uniq(mine.map(r => r.quota)), categories: uniq(mine.map(r => r.category)),
    mostCompetitiveClosing: closings.length ? Math.min(...closings) : null,
    feesKnown: mine.filter(r => numberOrNull(r.annualFee) != null).length,
  };
}

/**
 * Current published capacity beside matched history. Seats and past
 * allotments are different quantities, so no like-for-like delta is claimed;
 * a seat delta appears only when a previousSeats value was supplied.
 */
export function capacityRows(records = []) {
  const seats = records.filter(r => r.recordKind === 'seat-matrix');
  const withHistory = [], withoutHistory = [];
  const bySpecialty = new Map();
  for (const r of seats) {
    const entry = {
      record: r, seats: numberOrNull(r.seats),
      hasHistory: r.historicalClosingRank != null || (Array.isArray(r.historyIds) && r.historyIds.length > 0),
      historicalClosingRank: numberOrNull(r.historicalClosingRank),
      seatDelta: numberOrNull(r.seats) != null && numberOrNull(r.previousSeats) != null ? numberOrNull(r.seats) - numberOrNull(r.previousSeats) : null,
    };
    (entry.hasHistory ? withHistory : withoutHistory).push(entry);
    const key = r.specialty || r.course || 'Unclassified';
    if (!bySpecialty.has(key)) bySpecialty.set(key, { specialty: key, seats: 0, pools: 0, withHistory: 0 });
    const agg = bySpecialty.get(key);
    agg.seats += entry.seats || 0; agg.pools += 1; if (entry.hasHistory) agg.withHistory += 1;
  }
  return {
    withHistory, withoutHistory,
    totalSeats: seats.reduce((sum, r) => sum + (numberOrNull(r.seats) || 0), 0),
    bySpecialty: [...bySpecialty.values()].sort((a, b) => b.seats - a.seats),
  };
}

const median = values => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};
const sortHistory = rows => [...rows].sort((a, b) => compareNumber(a.year, b.year) || roundRank(a.round) - roundRank(b.round));

/**
 * How closing ranks moved across rounds, per pool. Positive drift means the
 * pool closed at a higher (easier) rank in its latest observation. Historical
 * description only — later rounds differ in seats, rules and participants.
 */
export function roundDrift(records = [], options = {}, institutes = []) {
  const map = instituteMap(institutes);
  const wanted = (value, selected) => unrestricted(selected) || lower(value) === lower(selected);
  const groups = new Map();
  for (const record of records) {
    if (record.recordKind !== 'cutoff') continue;
    const closing = numberOrNull(record.closingRank);
    if (closing == null) continue;
    const inst = institution(record, map);
    if (!wanted(record.category, options.category) || !wanted(record.quota, options.quota)
      || !wanted(record.specialty, options.specialty) || !wanted(record.program, options.program)
      || !wanted(inst.state || record.state, options.state) || !wanted(record.year, options.year)) continue;
    const key = poolKeyOf(record);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(record);
  }
  const pools = [...groups.values()].map(history => {
    const sorted = sortHistory(history);
    const first = sorted[0], last = sorted.at(-1);
    const firstClosing = numberOrNull(first.closingRank), lastClosing = numberOrNull(last.closingRank);
    const drift = sorted.length > 1 ? lastClosing - firstClosing : null;
    return {
      record: last, history: sorted, observations: sorted.length,
      firstClosing, lastClosing, drift,
      direction: drift == null ? 'single' : drift > 0 ? 'loosened' : drift < 0 ? 'tightened' : 'flat',
    };
  }).sort((a, b) => compareNumber(b.drift, a.drift));
  const multi = pools.filter(p => p.drift != null);
  const bySpecialty = new Map();
  for (const p of multi) {
    const key = p.record.specialty || p.record.course;
    if (!bySpecialty.has(key)) bySpecialty.set(key, []);
    bySpecialty.get(key).push(p.drift);
  }
  return {
    pools, totalPools: pools.length, multiRoundPools: multi.length,
    medianDrift: median(multi.map(p => p.drift)),
    loosenedShare: multi.length ? multi.filter(p => p.drift > 0).length / multi.length : null,
    bySpecialty: [...bySpecialty].map(([specialty, drifts]) => ({ specialty, pools: drifts.length, medianDrift: median(drifts) }))
      .sort((a, b) => b.pools - a.pools),
    note: 'Drift compares each pool\'s first and latest bundled closing AIR. Rounds differ in seats, rules and participants; past loosening does not promise future movement.',
  };
}

/** Every cutoff pool for one institute, with ordered history and gap vs a rank. */
export function poolHistory(records = [], instituteId, yourRank = null) {
  const rank = numberOrNull(yourRank);
  // Historical entities keep their own ids; seat rows link them via historyIds.
  const linked = new Set();
  for (const record of records) {
    if (String(record.instituteId) === String(instituteId) && Array.isArray(record.historyIds)) {
      for (const id of record.historyIds) linked.add(String(id));
    }
  }
  const groups = new Map();
  const seen = new Set();
  for (const record of records) {
    const mine = String(record.instituteId) === String(instituteId) || linked.has(String(record.id));
    if (!mine || record.recordKind !== 'cutoff' || seen.has(String(record.id))) continue;
    seen.add(String(record.id));
    if (numberOrNull(record.closingRank) == null) continue;
    const key = poolKeyOf(record);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(record);
  }
  return [...groups.values()].map(history => {
    const sorted = sortHistory(history);
    const latest = sorted.at(-1);
    const latestClosing = numberOrNull(latest.closingRank);
    const bestClosing = Math.max(...sorted.map(r => numberOrNull(r.closingRank)));
    return {
      record: latest, course: latest.course, specialty: latest.specialty, program: latest.program,
      quota: latest.quota, category: latest.category, history: sorted,
      latestClosing, bestClosing,
      gap: rank != null && rank > 0 ? latestClosing - rank : null,
      bestGap: rank != null && rank > 0 ? bestClosing - rank : null,
    };
  }).sort((a, b) => compareNumber(a.latestClosing, b.latestClosing));
}

/* Shareable choice-list links: the whole list travels in the URL, no account. */
const SHARE_TAGS = ['dream', 'target', 'backup'];

export function buildSharePayload(list = {}, recordOf = () => null) {
  const items = (Array.isArray(list.items) ? list.items : []).slice(0, 500).map(id => {
    const record = recordOf(id) || {};
    return [String(id), text(record.dataset) || 'mcc'];
  });
  const tags = {};
  for (const [id] of items) if (SHARE_TAGS.includes(list.tags?.[id])) tags[id] = list.tags[id];
  return { v: 1, app: 'zyjock', name: text(list.name).slice(0, 120) || 'Shared choice list', items, tags };
}

/** Validate an untrusted share payload. Returns a clean copy or null (fail closed). */
export function parseSharePayload(input) {
  if (!input || typeof input !== 'object' || input.v !== 1 || !Array.isArray(input.items)) return null;
  if (input.items.length > 500) return null;
  const items = [];
  for (const entry of input.items) {
    if (!Array.isArray(entry) || entry.length !== 2) return null;
    const [id, dataset] = entry;
    if (typeof id !== 'string' || !id || id.length > 200) return null;
    if (typeof dataset !== 'string' || !/^(mcc|state:.+)$/.test(dataset) || dataset.length > 80) return null;
    items.push([id, dataset]);
  }
  const tags = {};
  if (input.tags && typeof input.tags === 'object') {
    for (const [id] of items) if (SHARE_TAGS.includes(input.tags[id])) tags[id] = input.tags[id];
  }
  return { v: 1, app: 'zyjock', name: (typeof input.name === 'string' ? input.name.trim().slice(0, 120) : '') || 'Shared choice list', items, tags };
}

export function encodeShareToken(payload) {
  const bytes = new TextEncoder().encode(JSON.stringify(payload));
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function decodeShareToken(token) {
  try {
    if (typeof token !== 'string' || !/^[A-Za-z0-9_-]+$/.test(token) || token.length > 100000) return null;
    const base64 = token.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - token.length % 4) % 4);
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch { return null; }
}

/** Compare two ordered lists by record id. Positions are 1-based. */
export function listDiff(aItems = [], bItems = []) {
  const a = [...aItems], b = [...bItems];
  const posA = new Map(a.map((id, i) => [id, i + 1])), posB = new Map(b.map((id, i) => [id, i + 1]));
  const common = a.filter(id => posB.has(id));
  return {
    common,
    onlyA: a.filter(id => !posB.has(id)),
    onlyB: b.filter(id => !posA.has(id)),
    moved: common.filter(id => posA.get(id) !== posB.get(id)).map(id => ({ id, from: posA.get(id), to: posB.get(id) })),
  };
}

/** Factual checks over an ordered choice list. No chance or quality scores. */
export function listCheck(items = []) {
  const warnings = [];
  const seen = new Map();
  for (const r of items) {
    const key = poolKeyOf(r);
    if (seen.has(key)) warnings.push({ type: 'duplicate-pool', ids: [seen.get(key), r.id], message: 'The same institute, course, quota and category appears more than once. A counselling portal normally accepts each choice once.' });
    else seen.set(key, r.id);
    if (numberOrNull(r.seats) === 0) warnings.push({ type: 'zero-seats', ids: [r.id], message: 'A saved entry has zero published seats in its snapshot.' });
    if (closingOf(r) == null) warnings.push({ type: 'no-cutoff', ids: [r.id], message: 'A saved entry has no bundled historical closing rank. Treat its competitiveness as unknown, not easy.' });
  }
  return warnings;
}
