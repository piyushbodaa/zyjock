#!/usr/bin/env python3
"""Acquire and reconcile MCC's published 2026 Round 1 PG seat matrices.

Run with Python 3.12 and PyMuPDF (pip install pymupdf). No candidate data is
read or published. Each original row and the printed document totals must
reconcile before the compact browser dataset is written.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

BASE = Path(__file__).resolve().parent
DIST = BASE.parent / 'dist'
LANDING = 'https://mcc.nic.in/pg-medical-counselling/'
SOURCES = [
    {'key': 'aiq', 'title': 'Final All India Quota seats matrix PG 2026 counselling (MD/MS)', 'url': 'https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/10/202610151676193504.pdf'},
    {'key': 'deemed', 'title': 'Final deemed seats matrix PG counselling 2026 (MD/MS)', 'url': 'https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/10/20261015907178910.pdf'},
    {'key': 'dnb', 'title': 'Final seats matrix DNB PG counselling 2026', 'url': 'https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/10/202610151482599908.pdf'},
    {'key': 'internal', 'title': 'Final central internal quota seats matrix PG counselling 2026 (MD/MS)', 'url': 'https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/10/202610151906520168.pdf'},
]
DNB_CATEGORIES = ['Open', 'Open PwD', 'EWS', 'EWS PwD', 'OBC', 'OBC PwD', 'SC', 'SC PwD', 'ST', 'ST PwD']
DNB_ORIGINAL_CATEGORIES = ['Open', 'Open PwD', 'General-EWS', 'General-EWS PwD', 'OBC', 'OBC PwD', 'SC', 'SC PwD', 'ST', 'ST PwD']
CATEGORY_NAMES = {'OP': 'Open', 'BC': 'OBC', 'EW': 'EWS', 'SC': 'SC', 'ST': 'ST'}
STATES = ['Andaman And Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu And Kashmir', 'Jharkhand', 'Karnataka', 'Kerala', 'Ladakh', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal']
STATE_ALIASES = {'Tamilnadu': 'Tamil Nadu', 'Orissa': 'Odisha', 'Uttaranchal': 'Uttarakhand', 'Pondicherry': 'Puducherry', 'New Delhi': 'Delhi', 'Jammu & Kashmir': 'Jammu And Kashmir'}


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def normalized(value):
    return re.sub(r'[^a-z0-9]+', ' ', clean(value).lower()).strip()


def program_type(course):
    label = clean(course).upper()
    if label.startswith('(NBEMS-DIPLOMA)'):
        return 'NBEMS Diploma'
    if label.startswith('(NBEMS)'):
        return 'DNB'
    if re.match(r'^M\.?\s*D\.?\b', label):
        return 'MD'
    if re.match(r'^M\.?\s*S\.?\b', label):
        return 'MS'
    if label.startswith('M.CH.'):
        return 'MCh'
    if label.startswith('DIPLOMA') or '(D.D.V.L.)' in label:
        return 'Diploma'
    return 'Other PG'


def address_state(address):
    matches = []
    for label, canonical in [(s, s) for s in STATES] + list(STATE_ALIASES.items()):
        for match in re.finditer(r'(?<![A-Za-z])' + re.escape(label) + r'(?![A-Za-z])', address, re.I):
            matches.append((match.end(), len(label), canonical))
    return max(matches)[2] if matches else None


def identity(institution):
    match = re.search(r'\((\d{6})\)\s*$', institution)
    if not match:
        raise ValueError(f'Institution has no terminal six-digit MCC code: {institution}')
    code = match[1]
    name = institution[:match.start()].strip().rstrip(',').strip()
    return code, name


def category_name(value):
    match = re.fullmatch(r'(OP|BC|EW|SC|ST) (NO|PH)', value)
    if not match:
        raise ValueError(f'Unrecognized matrix category: {value}')
    return CATEGORY_NAMES[match[1]] + (' PwD' if match[2] == 'PH' else '')


def extract_source(source):
    key = source['key']
    pdf = BASE / f'mcc-2026-pg-r1-{key}-seat-matrix.pdf'
    if not pdf.exists():
        urllib.request.urlretrieve(source['url'], pdf)
    if not pdf.read_bytes().startswith(b'%PDF'):
        raise ValueError(f'{pdf.name} is not a PDF')
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    cache_path = pdf.with_suffix('.rows.json')
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if cached.get('parserVersion') == 2 and cached['summary']['sha256'] == pdf_hash:
            print(f'{key}: using reconciled extraction cache', flush=True)
            return cached['rows'], cached['summary']
    textfile = pdf.with_suffix('.txt')
    if not textfile.exists():
        subprocess.run(['pdftotext', '-layout', str(pdf), str(textfile)], check=True)
    document = pymupdf.open(pdf)
    expected_columns = 15 if key == 'dnb' else 7
    rows, totals, pages = [], [], []
    seen = set()
    for page_number, page in enumerate(document, 1):
        tables = page.find_tables().tables
        if not tables:
            raise ValueError(f'{key} page {page_number}: no table found')
        page_count = page_seats = 0
        for table in tables:
            for cells in table.extract():
                cells = [clean(cell) for cell in cells]
                combined = ' '.join(cells)
                if 'FINAL ' in cells[0] or cells[0] in ('StateName', 'Institute Type'):
                    continue
                if not any(cells):
                    continue
                # The internal PDF's final merged total label is outside the
                # extracted grid; its grid row contains only the last total cell.
                total_only_row = not any(cells[:-1]) and re.fullmatch(r'\d+', cells[-1] or '')
                if 'TOTAL SEATS' in combined or total_only_row:
                    numeric = [int(cell) for cell in cells if re.fullmatch(r'\d+', cell)]
                    totals.append(numeric)
                    continue
                if len(cells) != expected_columns:
                    raise ValueError(f'{key} page {page_number}: expected {expected_columns} columns, got {cells}')
                if key == 'dnb':
                    institute_type, original_institution, original_course, quota = cells[:4]
                    state = address_state(original_institution)
                    state_source = 'Institution address in the official matrix' if state else 'Not separately published and not identified in source address'
                    counts = [int(value) for value in cells[4:]]
                    if sum(counts[:-1]) != counts[-1]:
                        raise ValueError(f'DNB row category sum mismatch on page {page_number}: {cells}')
                    categories = list(zip(DNB_CATEGORIES, DNB_ORIGINAL_CATEGORIES, counts[:-1]))
                    row_total = counts[-1]
                else:
                    state, institute_type, original_institution, quota, original_course, original_category, seats = cells
                    state_source = 'StateName column in the official matrix'
                    categories = [(category_name(original_category), original_category, int(seats))]
                    row_total = int(seats)
                code, name = identity(original_institution)
                course_match = re.search(r'\(([A-Z0-9-]{3,5})\)\s*$', original_course) if key != 'dnb' else None
                course_code = course_match[1] if course_match else None
                course = original_course[:course_match.start()].strip() if course_match else original_course
                row_key = (code, original_course, quota, tuple((c, n) for c, _, n in categories))
                if row_key in seen:
                    raise ValueError(f'Duplicate original row in {key}: {row_key}')
                seen.add(row_key)
                rows.append(dict(instituteCode=code, institutionName=name, originalInstitution=original_institution,
                                 state=state, stateSource=state_source, instituteType=institute_type,
                                 course=course, courseCode=course_code, originalCourse=original_course,
                                 originalQuota=quota, categories=categories, totalSeats=row_total, sourcePage=page_number))
                page_count += 1
                page_seats += row_total
        pages.append({'page': page_number, 'rows': page_count, 'seats': page_seats})
        if page_number % 100 == 0:
            print(f'{key}: {page_number}/{len(document)} pages', flush=True)
    if len(totals) != 1:
        raise ValueError(f'{key}: expected one document total, found {totals}')
    extracted_total = sum(row['totalSeats'] for row in rows)
    if extracted_total != totals[0][-1]:
        raise ValueError(f'{key}: extracted {extracted_total} seats != printed {totals[0][-1]}')
    category_totals = Counter()
    for row in rows:
        for category, _, seats in row['categories']:
            category_totals[category] += seats
    if key == 'dnb' and [category_totals[c] for c in DNB_CATEGORIES] != totals[0][:-1]:
        raise ValueError(f'DNB document category totals mismatch: {category_totals} vs {totals[0]}')
    # A second Poppler extraction must independently expose the same number of
    # complete numeric data-row endings and the same row-seat sum.
    text = textfile.read_text()
    if key == 'dnb':
        numeric_rows = [list(map(int, m.groups())) for line in text.splitlines()
                        if 'TOTAL SEATS' not in line
                        and (m := re.search(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', line))]
    else:
        numeric_rows = [[int(m[1])] for line in text.splitlines()
                        if (m := re.search(r'\b(?:OP|BC|EW|SC|ST)\s+(?:NO|PH)\s+(\d+)\s*$', line))]
    if len(numeric_rows) != len(rows) or sum(row[-1] for row in numeric_rows) != extracted_total:
        raise ValueError(f'{key}: independent text-row reconciliation failed: {len(numeric_rows)} vs {len(rows)} rows, {sum(row[-1] for row in numeric_rows)} vs {extracted_total} seats')
    summary = dict(key=key, title=source['title'], url=source['url'], filename=pdf.name,
                   sha256=pdf_hash, pages=len(document),
                   originalRows=len(rows), publishedSeats=totals[0][-1], extractedSeats=extracted_total,
                   institutions=len({row['instituteCode'] for row in rows}), categoryTotals=dict(category_totals),
                   documentTotalsReconciled=True, independentTextRowsReconciled=True,
                   pageReconciliation=pages)
    print(f'{key}: reconciled {len(rows)} rows, {extracted_total} seats, {len(document)} pages', flush=True)
    cache_path.write_text(json.dumps({'parserVersion': 2, 'rows': rows, 'summary': summary}, ensure_ascii=False, separators=(',', ':')))
    return rows, summary


def main():
    collected = []
    # Separate processes keep independent PyMuPDF instances and reduce latency.
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(extract_source, source): source for source in SOURCES}
        for future in concurrent.futures.as_completed(futures):
            collected.append((futures[future], *future.result()))
    collected.sort(key=lambda item: [source['key'] for source in SOURCES].index(item[0]['key']))
    institutes = {}
    records = []
    source_summaries = []
    original_rows = 0
    zero_categories = 0
    glossary_path = BASE / 'pg-course-glossary.json'
    glossary = {}
    if glossary_path.exists():
        for item in json.loads(glossary_path.read_text()):
            key = normalized(item['label'])
            if key in glossary and glossary[key]['code'] != item['code']:
                raise ValueError(f'Ambiguous official course glossary entry: {key}')
            glossary[key] = item
    for source, rows, summary in collected:
        source_summaries.append(summary)
        original_rows += len(rows)
        for row in rows:
            code = row['instituteCode']
            institute_id = f'pg-mcc-{code}'
            course = row['course']
            course_code = row['courseCode']
            # Some branch codes wrap across lines in the source (D- GO, T- FM).
            # The spaces are layout artifacts, not part of the printed code.
            wrapped_code = re.search(r'\(([A-Z0-9-][A-Z0-9 -]{1,7})\)\s*$', row['originalCourse']) if source['key'] != 'dnb' else None
            if wrapped_code:
                course_code = wrapped_code[1].replace(' ', '')
                course = row['originalCourse'][:wrapped_code.start()].strip()
            code_source = source['url'] if course_code else None
            code_method = 'Printed branch code in the source matrix' if course_code else None
            if not course_code and normalized(course) in glossary:
                entry = glossary[normalized(course)]
                course_code, code_source = entry['code'], entry['sourceUrl']
                code_method = 'Exact normalized course label match to the official MCC course glossary'
            if institute_id not in institutes:
                institutes[institute_id] = dict(id=institute_id, name=row['institutionName'], originalInstitution=row['originalInstitution'],
                    normalizedInstitution=normalized(row['institutionName']), aliases=[row['institutionName']],
                    instituteCode=code, mccCode=code, city=None, state=row['state'], normalizedState=normalized(row['state']), stateSource=row['stateSource'],
                    type=row['instituteType'], originalInstituteType=row['instituteType'],
                    dataStatus='verified', sourceUrl=source['url'], sourceLabel=source['title'], sourcePage=row['sourcePage'])
            else:
                institute = institutes[institute_id]
                if row['institutionName'] not in institute['aliases']:
                    institute['aliases'].append(row['institutionName'])
                if not institute['state'] and row['state']:
                    institute['state'] = row['state']
                    institute['stateSource'] = row['stateSource']
            for category, original_category, seats in row['categories']:
                # Zero categories remain explicitly represented: a reported zero
                # is different from an unknown category not published in a file.
                zero_categories += seats == 0
                key = '|'.join([source['key'], code, row['originalCourse'], row['originalQuota'], original_category])
                records.append(dict(id='pg-seat-2026-' + hashlib.sha256(key.encode()).hexdigest()[:20],
                    instituteId=institute_id, instituteCode=code, originalInstitution=row['originalInstitution'],
                    normalizedInstitution=normalized(row['institutionName']), originalInstituteType=row['instituteType'],
                    state=row['state'], stateSource=row['stateSource'], exam='NEET PG',
                    course=course, courseCode=course_code, courseCodeSourceUrl=code_source, courseCodeMethod=code_method,
                    programType=program_type(course), originalCourse=row['originalCourse'],
                    normalizedCourse=normalized(course), normalizedState=normalized(row['state']), counselling='MCC', quota=row['originalQuota'],
                    originalQuota=row['originalQuota'], category=category, originalCategory=original_category,
                    year=2026, round='Round 1', recordKind='seat-matrix', matrixKind=source['key'],
                    openingRank=None, closingRank=None, seats=seats, annualFee=None, monthlyStipend=None,
                    bondYears=None, bondPenalty=None, previousSeats=None, dataStatus='verified',
                    sourceUrl=source['url'], sourceLabel=source['title'], sourcePage=row['sourcePage'],
                    snapshotDate='2026-10-15'))
    if len({record['id'] for record in records}) != len(records):
        raise ValueError('Duplicate output record IDs')
    if sum(record['seats'] for record in records) != sum(summary['publishedSeats'] for summary in source_summaries):
        raise ValueError('Output record seat sums do not equal the four published document totals')
    coverage = dict(label='MCC NEET PG 2026 Round 1 published seat matrices', exam='NEET PG', year=2026, round='Round 1',
        checkedAt='2026-10-19', snapshotDate='2026-10-15', snapshotType='Published seat matrix, not live vacancies',
        institutionCount=len(institutes), recordCount=len(records), originalRows=original_rows,
        publishedSeats=sum(record['seats'] for record in records), zeroSeatRecords=zero_categories,
        positiveSeatRecords=sum(record['seats'] > 0 for record in records), matrixCount=len(SOURCES),
        recordsWithoutCourseCode=sum(record['courseCode'] is None for record in records),
        institutionsWithoutState=sum(institute['state'] is None for institute in institutes.values()),
        programSeatCounts={program: sum(record['seats'] for record in records if record['programType'] == program) for program in sorted({record['programType'] for record in records})},
        allPublishedPagesParsed=True, printedDocumentTotalsReconciled=True,
        limitations=['These are the four MCC 2026 Round 1 final matrix PDFs listed on the official PG page on 19 October 2026; they are snapshots, not live vacancies.',
                    'Later MCC additions, removals and corrections may alter these seats. MCC currently asks institutions to report matrix discrepancies before Round 1 choice filling closes.',
                    'MCC matrices do not cover all state counselling seats or every postgraduate admission route.',
                    'Seat rows have no closing rank, fee, stipend or bond figures. Historical cutoffs must be read separately by source year, round, quota and category.',
                    'DNB state labels are extracted only from explicit address text; unknown addresses retain a null state. Cities are not inferred.',
                    'DNB course codes are attached only where the printed course label exactly matches the normalized official MCC glossary label. Unmatched labels retain a null code; no fuzzy course matching is applied.'])
    sources = [{key: value for key, value in summary.items() if key != 'pageReconciliation'} for summary in source_summaries]
    payload = dict(institutes=list(institutes.values()), records=records, coverage=coverage, sources=sources)
    DIST.mkdir(exist_ok=True)
    output = DIST / 'pg-seats.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
    summary = dict(coverage=coverage, sources=source_summaries, output=str(output.relative_to(BASE.parent)),
                   outputBytes=output.stat().st_size, outputSha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                   generatedAt=datetime.now(timezone.utc).isoformat())
    (BASE / 'pg-seats-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (BASE / 'pg-seat-institution-lookup.json').write_text(json.dumps(list(institutes.values()), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({**coverage, 'outputBytes': output.stat().st_size}, indent=2))


if __name__ == '__main__':
    main()
