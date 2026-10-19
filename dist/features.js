/**
 * Free NEET PG planning features: historical rank scan (choice count),
 * institute profiles, course directory, seat-capacity view, eligibility
 * self-check and choice-list tools. Everything runs locally on bundled,
 * source-dated data. Nothing here predicts an allotment, converts marks
 * to a rank, or decides eligibility for a seat pool.
 */
import {
  rankScan, qualifyingStatus, eligibilityChecks,
  instituteSummary, capacityRows, listCheck,
} from './domain.js';

export function createFeatures(ctx) {
  const {
    e, num, money, shortMoney, icon, btn, badge, external, heading,
    openModal, download, buildCSV, toast, selectField, option, collegeCell, empty, ID,
  } = ctx;
  const D = () => ctx.data(), S = () => ctx.state();
  const allRecords = () => ctx.records(), allInstitutes = () => ctx.institutes();
  const inst = id => ctx.inst(id), rec = id => ctx.rec(id);
  const unique = values => [...new Set(values.filter(v => v != null && v !== ''))].sort();
  let scanVisible = 36, instituteQuery = '', courseQuery = '', capacityVisible = 36;
  let lastScan = null, lastChecks = null;

  const scanInputs = () => S().scan || {};
  const bandLabel = band => band === 'reached'
    ? '<span class="badge success">Closed beyond your rank</span>'
    : band === 'near' ? '<span class="badge warning">Near miss (within 10%)</span>'
      : '<span class="badge neutral">Closed ahead of your rank</span>';

  function runScan() {
    const f = scanInputs();
    lastScan = rankScan(allRecords(), {
      rank: f.rank, category: f.category || '', quota: f.quota || '',
      specialty: f.specialty || '', program: f.program || '', state: f.state || '', year: f.year || '',
    }, allInstitutes());
    return lastScan;
  }

  function predictor() {
    const f = scanInputs();
    const cutoffs = allRecords().filter(r => r.recordKind === 'cutoff');
    const scan = f.rank ? (lastScan && lastScan.rank === Number(f.rank) ? lastScan : runScan()) : null;
    const scale = D().scoreScale || {};
    const scoreResult = f.score ? qualifyingStatus(f.score, scale) : null;
    const reached = scan?.available ? scan.pools.filter(p => p.band === 'reached') : [];
    const shown = reached.slice(0, scanVisible);
    return heading('How many pools closed beyond your rank?',
      'A free historical count from bundled MCC allotments — one pool is one institute + course + quota + seat category, judged by its latest observation.', '<span class="chip">Free · No login</span>')
      + `<div class="grid cols-2"><section class="panel"><div class="panel-header"><h2>Scan by All India rank</h2><span class="badge success">HISTORICAL</span></div>
      <form id="scan-form" class="panel-body form-grid">
        <label class="field"><span>Your NEET PG All India rank</span><input name="rank" type="number" min="1" step="1" required placeholder="e.g. 25,000" value="${e(f.rank || '')}"></label>
        ${selectField('category', 'Seat category', unique(cutoffs.map(r => r.category)), f.category || '')}
        ${selectField('quota', 'Quota', unique(cutoffs.map(r => r.quota)), f.quota || '')}
        ${selectField('specialty', 'Specialty', unique(cutoffs.map(r => r.specialty)), f.specialty || '')}
        ${selectField('program', 'Programme', unique(cutoffs.map(r => r.program)), f.program || '')}
        ${selectField('state', 'State', unique(cutoffs.map(r => inst(r.instituteId).state)), f.state || '')}
        ${selectField('year', 'Source year', unique(cutoffs.map(r => String(r.year))).sort().reverse(), f.year || '')}
        <button class="btn primary">Count historical pools ${icon('arrow')}</button>
        <p class="small text-muted">Blank filters mean “all”. Broad selections can include quotas or categories you cannot claim — verify every pool before you rely on it.</p>
      </form></section>
      <section class="panel"><div class="panel-header"><h2>Score vs qualifying thresholds</h2><span class="badge neutral">${e(scale.year || '')} NOTICE</span></div>
      <form id="score-form" class="panel-body">
        <label class="field"><span>Your NEET PG score (out of ${e(scale.maximum ?? '—')})</span><input name="score" type="number" min="0" required placeholder="From your scorecard" value="${e(f.score || '')}"></label>
        <button class="btn secondary">Compare with thresholds</button>
        <div aria-live="polite">${scoreResult ? (scoreResult.available
          ? `<div class="section-gap">${scoreResult.results.map(r => `<p>${r.meets ? icon('check') : icon('close')} <strong>${e(r.category)}</strong> — threshold ${num(r.threshold)} (${num(r.percentile)}th percentile): ${r.meets ? 'met' : 'not met'}</p>`).join('')}<p class="small text-muted">${e(scoreResult.note)} ${external(scoreResult.sourceUrl, 'Official notice')}</p></div>`
          : `<p class="data-note">${e(scoreResult.reason)}</p>`) : ''}</div>
        <p class="small text-muted">Zyjock does not convert marks to a rank: no sourced marks-to-rank curve is bundled. Use the AIR on your official scorecard in the scan.</p>
        <p><a class="btn subtle" href="#eligibility">Run the full document self-check ${icon('arrow')}</a></p>
      </form></section></div>`
      + (scan ? (scan.available
        ? `<section class="panel section-gap"><div class="panel-header"><div><span class="badge success">LATEST OBSERVATION PER POOL</span><h2>${num(scan.reachedCount)} pools closed at or beyond AIR ${num(scan.rank)}</h2></div>${btn(`${icon('download')} Export reached pools`, 'scan-export')}</div>
          <div class="panel-body"><div class="grid cols-4">
            <div class="stat-card"><span class="metric-label">Pools reached</span><strong class="metric-value">${num(scan.reachedCount)}</strong><span class="small">of ${num(scan.totalPools)} pools in scope</span></div>
            <div class="stat-card"><span class="metric-label">Institutes reached</span><strong class="metric-value">${num(scan.reachedInstitutes)}</strong><span class="small">Distinct institutes</span></div>
            <div class="stat-card"><span class="metric-label">Near misses</span><strong class="metric-value">${num(scan.nearCount)}</strong><span class="small">Closed within 10% ahead of your rank</span></div>
            <div class="stat-card"><span class="metric-label">Ahead of your rank</span><strong class="metric-value">${num(scan.beyondCount)}</strong><span class="small">Needed a better (lower) rank</span></div>
          </div>
          <p class="small text-muted section-gap">Top reached specialties: ${scan.bySpecialty.slice(0, 8).map(s => `<button class="chip" data-action="scan-specialty" data-id="${e(s.specialty)}">${e(s.specialty)} · ${num(s.count)}</button>`).join(' ')}</p>
          <p class="data-note">${e(scan.note)}</p></div>
          ${shown.length ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Institute & specialty</th><th>Quota / category</th><th>Latest observation</th><th>Opening AIR</th><th>Closing AIR</th><th>Band</th><th></th></tr></thead><tbody>
            ${shown.map(p => { const r = p.record; return `<tr><td>${collegeCell(r)}</td><td>${e(r.quota)}<br><span class="text-muted">${e(r.category)}</span></td><td>${e(r.year)} · ${e(r.round)}${p.history.length > 1 ? `<br><span class="small text-muted">${p.history.length} observations</span>` : ''}</td><td class="numeric">${num(r.openingRank)}</td><td class="numeric">${num(p.closingRank)}</td><td>${bandLabel(p.band)}</td><td><button class="icon-btn" data-action="save-record" data-id="${e(r.id)}" aria-label="Save to active choice list">${icon('plus')}</button></td></tr>`; }).join('')}
          </tbody></table></div>` : empty('No pool in scope closed beyond this rank', 'Try removing a filter, or inspect near misses in the historical explorer.', 'scan-reset')}
          ${reached.length > scanVisible ? `<div class="toolbar section-gap">${btn('Show more pools', 'scan-more')}<span class="small text-muted">Showing ${scanVisible} of ${num(reached.length)}. Export includes every reached pool.</span></div>` : ''}
          </section>`
        : `<p class="data-note section-gap">${e(scan.reason)}</p>`)
        : `<section class="panel section-gap"><div class="panel-body"><h2>Read the count correctly</h2><p>Each pool keeps its own year, round, quota and allotted seat category. “Reached” only means that pool’s latest bundled closing AIR was at or beyond yours. It does not check your eligibility, this year’s seats, or other candidates’ choices — so treat it as a research starting point, then verify in the explorers and the current bulletin.</p><p><a class="btn secondary" href="#cutoffs">Inspect every round ${icon('arrow')}</a> <a class="btn subtle" href="#rank">Rank guidance</a></p></div></section>`);
  }

  function instituteProfile(id) {
    const i = inst(id);
    const s = instituteSummary(allRecords(), id);
    if (!s.records.length) { toast('No bundled records for this institute yet.', 'warning'); return; }
    const seatRows = [...s.seatRows].sort((a, b) => String(a.course).localeCompare(String(b.course)));
    const latestCutoffs = new Map();
    for (const r of s.cutoffRows) {
      const key = [r.courseCode || r.course, r.quota, r.category].join('|');
      const prev = latestCutoffs.get(key);
      if (!prev || r.year > prev.year || String(r.round) > String(prev.round)) latestCutoffs.set(key, r);
    }
    openModal(i.name, `<div class="toolbar"><span class="chip">${e(i.type || 'Institute')}</span><span class="text-muted">${e(i.state || '')}${i.city ? ' · ' + e(i.city) : ''}</span>${i.instituteCode ? `<span class="chip">MCC code ${e(i.instituteCode)}</span>` : ''}</div>
      ${i.address ? `<p class="small text-muted">${e(i.address)}</p>` : ''}
      <div class="grid cols-4">
        <div class="stat-card"><span class="metric-label">Published seats (snapshot)</span><strong class="metric-value">${num(s.totalSeats)}</strong><span class="small">${num(s.seatPools)} seat pools</span></div>
        <div class="stat-card"><span class="metric-label">Specialties</span><strong class="metric-value">${num(s.specialties.length)}</strong><span class="small">${e(s.programs.join(' · '))}</span></div>
        <div class="stat-card"><span class="metric-label">Most competitive closing AIR</span><strong class="metric-value">${num(s.mostCompetitiveClosing)}</strong><span class="small">Lowest bundled historical closing</span></div>
        <div class="stat-card"><span class="metric-label">Pools with reported tuition</span><strong class="metric-value">${num(s.feesKnown)}</strong><span class="small">Blank means not reported</span></div>
      </div>
      ${seatRows.length ? `<section class="section-gap"><h3>Published seat pools</h3><div class="table-wrap"><table class="data-table"><thead><tr><th>Course</th><th>Quota / category</th><th>Seats</th><th>Matched closing AIR</th><th></th></tr></thead><tbody>
        ${seatRows.slice(0, 40).map(r => `<tr><td><button class="college-name" data-action="detail" data-id="${e(r.id)}">${e(r.course)}</button></td><td>${e(r.quota)}<br><span class="text-muted">${e(r.category)}</span></td><td class="numeric">${num(r.seats)}</td><td class="numeric">${num(r.historicalClosingRank)}${r.historicalYear ? `<br><span class="small text-muted">${e(r.historicalYear)} · ${e(r.historicalRound)}</span>` : ''}</td><td><button class="icon-btn" data-action="save-record" data-id="${e(r.id)}" aria-label="Save to active choice list">${icon('plus')}</button></td></tr>`).join('')}
      </tbody></table></div>${seatRows.length > 40 ? `<p class="small text-muted">Showing 40 of ${num(seatRows.length)} pools. Use the college explorer filtered by this institute name for the rest.</p>` : ''}</section>` : ''}
      ${latestCutoffs.size ? `<section class="section-gap"><h3>Latest historical cutoffs by pool</h3><div class="table-wrap"><table class="data-table"><thead><tr><th>Course</th><th>Quota / category</th><th>Year · round</th><th>Closing AIR</th></tr></thead><tbody>
        ${[...latestCutoffs.values()].slice(0, 40).map(r => `<tr><td>${e(r.course)}</td><td>${e(r.quota)}<br><span class="text-muted">${e(r.category)}</span></td><td>${e(r.year)} · ${e(r.round)}</td><td class="numeric">${num(r.closingRank)}</td></tr>`).join('')}
      </tbody></table></div></section>` : '<p class="data-note section-gap">No bundled historical cutoff observations for this institute.</p>'}
      <p class="small text-muted">Seat snapshots and historical observations keep their own dates. Verify current seats, fees and recognition with MCC and the institute before acting.</p>
      ${i.officialUrl ? `<p>${external(i.officialUrl, 'Institution website')}</p>` : ''}`);
  }

  function institutes() {
    const counts = new Map();
    for (const r of allRecords()) {
      if (!counts.has(r.instituteId)) counts.set(r.instituteId, { seats: 0, pools: 0, cutoffs: 0 });
      const c = counts.get(r.instituteId);
      if (r.recordKind === 'seat-matrix') { c.pools += 1; c.seats += Number(r.seats) || 0; }
      if (r.recordKind === 'cutoff') c.cutoffs += 1;
    }
    const q = instituteQuery.toLowerCase();
    const rows = allInstitutes()
      .map(i => ({ i, ...(counts.get(i.id) || { seats: 0, pools: 0, cutoffs: 0 }) }))
      .filter(x => (x.pools || x.cutoffs) && (!q || `${x.i.name} ${x.i.state || ''} ${x.i.city || ''}`.toLowerCase().includes(q)))
      .sort((a, b) => b.seats - a.seats || String(a.i.name).localeCompare(String(b.i.name)));
    return heading('Institutes, profile by profile.', 'Every college and hospital in the bundled NEET PG snapshots, with its seat pools and historical observations in one place.')
      + `<form id="institute-search" class="panel filters"><label class="filter-field search-field"><span>Find an institute</span><div class="search-input">${icon('search')}<input name="search" placeholder="Name, city or state…" value="${e(instituteQuery)}"></div></label><button class="btn primary">Search institutes</button></form>
      <p class="small text-muted">${num(rows.length)} institutes with bundled records. Seat totals are dated publication snapshots, not live vacancies.</p>
      <div class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Institute</th><th>Type</th><th>Published seats</th><th>Seat pools</th><th>Cutoff observations</th><th></th></tr></thead><tbody>
      ${rows.slice(0, 60).map(x => `<tr><td><button class="college-name" data-action="institute-profile" data-id="${e(x.i.id)}">${e(x.i.name)}</button><div class="college-meta">${e(x.i.city || x.i.state || '')}</div></td><td>${e(x.i.type || '—')}</td><td class="numeric">${num(x.seats)}</td><td class="numeric">${num(x.pools)}</td><td class="numeric">${num(x.cutoffs)}</td><td>${btn('Profile', 'institute-profile', 'subtle', `data-id="${e(x.i.id)}"`)}</td></tr>`).join('')}
      </tbody></table></div></div>${rows.length > 60 ? '<p class="small text-muted section-gap">Showing the 60 largest by published seats. Search to find a specific institute.</p>' : ''}`;
  }

  function courses() {
    const glossary = D().courseGlossary || [];
    const seatsByCode = new Map();
    for (const r of allRecords()) {
      if (r.recordKind !== 'seat-matrix' || !r.courseCode) continue;
      if (!seatsByCode.has(r.courseCode)) seatsByCode.set(r.courseCode, { seats: 0, pools: 0, course: r.course });
      const a = seatsByCode.get(r.courseCode); a.seats += Number(r.seats) || 0; a.pools += 1;
    }
    const q = courseQuery.toLowerCase();
    const rows = glossary.filter(g => !q || `${g.code} ${g.label}`.toLowerCase().includes(q));
    return heading('Course codes, decoded.', 'The official NEET PG course glossary bundled with Zyjock, beside published seat counts per code.')
      + `<form id="course-search" class="panel filters"><label class="filter-field search-field"><span>Find a course code or name</span><div class="search-input">${icon('search')}<input name="search" placeholder="Try DANS or anaesthesiology…" value="${e(courseQuery)}"></div></label><button class="btn primary">Find course</button></form>
      <p class="small text-muted">${num(rows.length)} of ${num(glossary.length)} glossary entries. Use the exact code printed in the official matrix when you fill choices on the MCC portal.</p>
      <div class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Code</th><th>Course (official label)</th><th>Published seats</th><th>Pools</th><th>Glossary source</th></tr></thead><tbody>
      ${rows.map(g => { const a = seatsByCode.get(g.code) || { seats: 0, pools: 0 }; return `<tr><td><strong>${e(g.code)}</strong></td><td>${e(g.label)}</td><td class="numeric">${num(a.seats)}</td><td class="numeric">${num(a.pools)}</td><td>${external(g.sourceUrl, 'Official glossary')}${g.sourcePages ? `<span class="small text-muted"> pp. ${e(g.sourcePages)}</span>` : ''}</td></tr>`; }).join('')}
      </tbody></table></div></div>
      <p class="data-note section-gap">Course duration and recognition status are not bundled as a validated dataset. Confirm them in the current MCC bulletin, the NMC college listing and the institute prospectus.</p>`;
  }

  function seatchanges() {
    const cap = capacityRows(allRecords());
    const shown = cap.withoutHistory.slice(0, capacityVisible);
    return heading('Where is the capacity?', 'Published seats by specialty, and the pools that have no matched historical cutoff yet. Seats and past allotments are different quantities — no fake “increase” is computed from them.')
      + `<div class="grid cols-4">
        <div class="stat-card"><span class="metric-label">Published seats</span><strong class="metric-value">${num(cap.totalSeats)}</strong><span class="small">In the bundled snapshot</span></div>
        <div class="stat-card"><span class="metric-label">Pools with matched history</span><strong class="metric-value">${num(cap.withHistory.length)}</strong><span class="small">Exact institute + course + quota + category match</span></div>
        <div class="stat-card"><span class="metric-label">Pools without a match</span><strong class="metric-value">${num(cap.withoutHistory.length)}</strong><span class="small">May be new, renamed or unmatched — not labelled “new seats”</span></div>
        <div class="stat-card"><span class="metric-label">Specialties</span><strong class="metric-value">${num(cap.bySpecialty.length)}</strong><span class="small">With published seats</span></div>
      </div>
      <section class="panel section-gap"><div class="panel-header"><h2>Seats by specialty</h2><span class="small text-muted">All quotas and categories combined</span></div>
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Specialty</th><th>Published seats</th><th>Pools</th><th>With matched history</th></tr></thead><tbody>
      ${cap.bySpecialty.slice(0, 30).map(a => `<tr><td>${e(a.specialty)}</td><td class="numeric">${num(a.seats)}</td><td class="numeric">${num(a.pools)}</td><td class="numeric">${num(a.withHistory)}</td></tr>`).join('')}
      </tbody></table></div></section>
      <section class="panel section-gap"><div class="panel-header"><h2>Pools without a matched historical cutoff</h2><span class="small text-muted">Competitiveness unknown — research individually</span></div>
      ${shown.length ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Institute & specialty</th><th>Quota / category</th><th>Seats</th><th></th></tr></thead><tbody>
      ${shown.map(x => `<tr><td>${collegeCell(x.record)}</td><td>${e(x.record.quota)}<br><span class="text-muted">${e(x.record.category)}</span></td><td class="numeric">${num(x.seats)}</td><td><button class="icon-btn" data-action="save-record" data-id="${e(x.record.id)}" aria-label="Save to active choice list">${icon('plus')}</button></td></tr>`).join('')}
      </tbody></table></div>` : empty('Every published pool has a matched history', 'Nothing to list here for this snapshot.', null)}
      ${cap.withoutHistory.length > capacityVisible ? `<div class="toolbar section-gap">${btn('Show more pools', 'capacity-more')}<span class="small text-muted">Showing ${capacityVisible} of ${num(cap.withoutHistory.length)}.</span></div>` : ''}
      </section>
      <p class="data-note">A missing match never means an easy seat. When a newer official matrix is bundled, re-check this page: pools move between the two groups as matching evidence improves.</p>`;
  }

  function eligibility() {
    const scale = D().scoreScale || {};
    const saved = S().eligibility || {};
    const radio = (name, label) => `<fieldset class="field"><legend>${e(label)}</legend>${[['yes', 'Yes'], ['no', 'No'], ['unknown', 'Not sure']].map(([v, l]) => `<label class="checkbox-row"><input type="radio" name="${name}" value="${v}" ${saved[name] === v ? 'checked' : ''}><span>${l}</span></label>`).join('')}</fieldset>`;
    const statusBadge = s => s === 'met' ? '<span class="badge success">Covered</span>' : s === 'not-met' ? '<span class="badge warning">Gap found</span>' : '<span class="badge neutral">Verify</span>';
    return heading('Check your documents, pool by pool.', 'A self-check built from the published requirements bundled with Zyjock. It prepares you for verification — it cannot declare you eligible for any seat.')
      + `<div class="grid cols-2"><section class="panel"><div class="panel-header"><h2>Your answers</h2><span class="badge neutral">STAYS ON THIS DEVICE</span></div>
      <form id="eligibility-form" class="panel-body form-grid">
        <label class="field"><span>NEET PG score (out of ${e(scale.maximum ?? '—')})</span><input name="score" type="number" min="0" placeholder="From your scorecard" value="${e(saved.score || '')}"></label>
        ${selectField('thresholdCategory', 'Qualifying-threshold row that applies to you', (scale.qualifyingThresholds || []).map(t => t.category), saved.thresholdCategory || '', 'Select row')}
        ${radio('internshipByCutoff', 'Internship completed by the published cut-off date?')}
        ${radio('registered', 'MBBS qualification with medical registration in place?')}
        <button class="btn primary">Run self-check ${icon('arrow')}</button>
        <p class="small text-muted">The bundled guide lists an internship completion cut-off of 30 September 2026 from MCC’s 2026 bulletin. Always re-confirm dates in the current bulletin.</p>
      </form></section>
      <section class="panel"><div class="panel-header"><h2>Your checklist</h2></div><div class="panel-body" aria-live="polite">
      ${lastChecks ? lastChecks.map(c => `<article class="notice-item"><div><p>${statusBadge(c.status)} <strong>${e(c.label)}</strong></p><p class="small">${e(c.detail)}</p></div></article>`).join('')
        + `<p class="small text-muted">Next: open each saved pool and check its quota, category and authority conditions in the current bulletin.</p>`
        : '<p class="text-muted">Answer the four prompts and run the check. Unknown answers stay “Verify” — they are never treated as eligibility.</p>'}
      <p>${external(scale.sourceUrl, 'Qualifying-threshold notice')}</p>
      <p><button class="btn subtle" data-action="guide-detail" data-id="pg-eligibility">Read the eligibility guide</button> <button class="btn subtle" data-action="guide-detail" data-id="pg-documents">Document list</button></p>
      </div></section></div>`;
  }

  const TAGS = [['', 'No tag'], ['dream', 'Dream'], ['target', 'Target'], ['backup', 'Backup']];
  function tagSelect(list, recordId) {
    const current = (list.tags || {})[recordId] || '';
    return `<select data-tag-for="${e(recordId)}" aria-label="Tag this choice">${TAGS.map(([v, l]) => option(v, l, current)).join('')}</select>`;
  }

  function listCheckModal() {
    const list = ctx.selectedList();
    const rows = (list?.items || []).map(rec).filter(Boolean);
    const warnings = listCheck(rows);
    const bySpecialty = {};
    for (const r of rows) bySpecialty[r.specialty || r.course] = (bySpecialty[r.specialty || r.course] || 0) + 1;
    const tags = list.tags || {};
    const tagCounts = { dream: 0, target: 0, backup: 0 };
    for (const id of list.items) if (tagCounts[tags[id]] != null) tagCounts[tags[id]] += 1;
    openModal(`List check — ${list.name}`, `
      <p><strong>${num(rows.length)}</strong> choices · ${num(Object.keys(bySpecialty).length)} specialties · Dream ${tagCounts.dream} · Target ${tagCounts.target} · Backup ${tagCounts.backup}</p>
      ${warnings.length ? warnings.map(w => `<p class="data-note">${icon('info')} ${e(w.message)}</p>`).join('') : '<p class="data-note">No duplicate pools, zero-seat entries or cutoff gaps found in this list.</p>'}
      <p class="small text-muted">Tags are your own labels for ordering your research. They are not admission chances, and this check does not evaluate eligibility. Order still matters most: place every pool you would accept above every pool you would not.</p>`);
  }

  async function action(a, id, dataset = {}) {
    if (a === 'institute-profile') { instituteProfile(id); return true; }
    if (a === 'scan-more') { scanVisible += 36; ctx.render(); return true; }
    if (a === 'scan-reset') { S().scan = {}; lastScan = null; scanVisible = 36; ctx.save(); ctx.render(); return true; }
    if (a === 'scan-specialty') { S().scan = { ...(S().scan || {}), specialty: id }; scanVisible = 36; lastScan = null; runScan(); ctx.save(); ctx.render(); return true; }
    if (a === 'scan-export') {
      const scan = lastScan || runScan();
      if (!scan.available) { toast('Run a scan first.', 'warning'); return true; }
      const rows = scan.pools.filter(p => p.band === 'reached').map(p => ({ ...p.record, instituteName: inst(p.record.instituteId).name, state: inst(p.record.instituteId).state, latestClosingRank: p.closingRank, observations: p.history.length }));
      download(buildCSV(rows, ['instituteName', 'state', 'course', 'specialty', 'program', 'quota', 'category', 'year', 'round', 'openingRank', 'latestClosingRank', 'observations', 'sourceUrl']), 'zyjock-rank-scan.csv', 'text/csv;charset=utf-8');
      return true;
    }
    if (a === 'capacity-more') { capacityVisible += 36; ctx.render(); return true; }
    if (a === 'duplicate-list') {
      const list = ctx.selectedList();
      if (!list) return true;
      const copy = { id: ID(), name: `${list.name} (copy)`, items: [...list.items], tags: { ...(list.tags || {}) } };
      S().lists.push(copy); S().activeList = copy.id; ctx.save(); ctx.render();
      toast('Choice list duplicated.');
      return true;
    }
    if (a === 'list-check') { listCheckModal(); return true; }
    return false;
  }

  function submit(id, values) {
    if (id === 'scan-form') { S().scan = { ...(S().scan || {}), ...values }; scanVisible = 36; lastScan = null; runScan(); ctx.save(); ctx.render(); return true; }
    if (id === 'score-form') { S().scan = { ...(S().scan || {}), score: values.score }; ctx.save(); ctx.render(); return true; }
    if (id === 'institute-search') { instituteQuery = values.search || ''; ctx.render(); return true; }
    if (id === 'course-search') { courseQuery = values.search || ''; ctx.render(); return true; }
    if (id === 'eligibility-form') { S().eligibility = values; lastChecks = eligibilityChecks(values, D().scoreScale || {}); ctx.save(); ctx.render(); return true; }
    return false;
  }

  function change(target) {
    if (target.dataset.tagFor) {
      const list = ctx.selectedList();
      if (!list) return true;
      list.tags = list.tags || {};
      if (target.value) list.tags[target.dataset.tagFor] = target.value; else delete list.tags[target.dataset.tagFor];
      ctx.save();
      return true;
    }
    return false;
  }

  return { predictor, institutes, courses, seatchanges, eligibility, instituteProfile, tagSelect, action, submit, change };
}

