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
const DEFAULT_COLUMNS = ['id', 'instituteId', 'instituteName', 'exam', 'course', 'counselling', 'quota', 'category', 'year', 'round', 'openingRank', 'closingRank', 'seats', 'annualFee', 'monthlyStipend', 'bondYears', 'bondPenalty', 'previousSeats', 'dataStatus', 'sourceUrl', 'sourceLabel'];
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
    for (const field of ['course', 'counselling', 'quota', 'category', 'year', 'round']) if (!matches(record[field], filters[field])) return false;
    if (!unrestricted(filters.dataMode) && lower(record.dataStatus) !== lower(filters.dataMode)) return false;
    if (rank != null && rank > 0) {
      const cutoff = numberOrNull(record.closingRank);
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
    if (!['NEET UG', 'NEET PG', 'NEET MDS', 'INICET', 'NEET SS', 'DNB PDCET'].includes(canonicalExam(input.exam))) fail('exam', 'Use NEET UG, NEET PG, NEET MDS, INICET, NEET SS, or DNB PDCET.');
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
