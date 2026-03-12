from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


BASE_DIR = Path(__file__).resolve().parent
BOOKS_CSV = BASE_DIR / 'books_working.csv'
RAW_Q2_CSV = BASE_DIR / 'raw_q2_entries.csv'
Q2_POOL_CSV = BASE_DIR / 'q2_pool.csv'
Q1_CLUSTERS_CSV = BASE_DIR / 'q1_clusters.csv'
METADATA_PROGRESS_JSON = BASE_DIR / 'metadata_progress.json'

OUTPUT_FIELDS = [
    'book_id',
    'title',
    'author',
    'reading_status',
    'metadata_status',
    'metadata_confidence',
    'matched_title',
    'matched_author',
    'douban_url',
    'isbn',
    'rating',
    'notes',
]

RAW_Q2_FIELDS = [
    'raw_q2_id',
    'book_id',
    'title',
    'author',
    'q2_text',
    'q2_status',
    'source_basis',
    'notes',
]

Q2_POOL_FIELDS = [
    'pool_id',
    'pool_question',
    'related_raw_q2_ids',
    'book_ids',
    'status',
    'notes',
]

Q1_CLUSTER_FIELDS = [
    'q1_id',
    'q1_question',
    'evidence_raw_q2_ids',
    'book_ids',
    'status',
    'notes',
]

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36'
)
REQUEST_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_GAP_SECONDS = 0.35
MAX_CANDIDATES = 3
DETAIL_CHECK_LIMIT = 2
SEARCH_CACHE: Dict[str, str] = {}
DETAIL_CACHE: Dict[str, str] = {}

TITLE_REPLACEMENTS = {
    'what if？': 'what if?',
    'what if？那些古怪又让人忧心的问题': 'what if?',
    '人的行动': 'human action',
    '红书': 'the red book',
    '项塔兰': 'shantaram',
}

AUTHOR_REPLACEMENTS = {
    '詹姆斯c斯科特': '詹姆斯c.斯科特',
    'c赖特米尔斯': 'c.赖特米尔斯',
    '尤瓦尔赫拉利': '尤瓦尔赫拉利',
    '卡尔古斯塔夫荣格': '荣格',
    '奥斯卡王尔德': '王尔德',
    '约翰斯坦贝克': '斯坦贝克',
    '兰道尔门罗': '兰道尔门罗',
}


@dataclass
class Candidate:
    title: str
    author: str
    url: str
    rating: str
    isbn: str
    score: float
    title_score: float
    author_score: float


def fetch_text(url: str) -> str:
    cache = DETAIL_CACHE if '/subject/' in url else SEARCH_CACHE
    if url in cache:
        return cache[url]
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        text = response.read().decode('utf-8', errors='ignore')
    cache[url] = text
    return text


def strip_html(value: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', value)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize_text(value: str) -> str:
    value = html.unescape(value or '').lower()
    value = re.sub(r"[《》“”\"'：:？?！!,，。.()（）\[\]【】/\\+\-·]", '', value)
    value = value.replace('&', 'and')
    value = re.sub(r'\s+', '', value)
    for old, new in TITLE_REPLACEMENTS.items():
        value = value.replace(old, new)
    return value


def normalize_author(value: str) -> str:
    value = strip_html(value).lower().replace(' ', '')
    value = re.sub(r'著|编著|主编|译|译者|原著', '', value)
    value = re.sub(r'[\[\]()（）,，/\\·・.:：]', '', value)
    for old, new in AUTHOR_REPLACEMENTS.items():
        value = value.replace(old, new)
    return value


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return min(len(left), len(right)) / max(len(left), len(right))
    left_counter = Counter(left)
    right_counter = Counter(right)
    overlap = sum((left_counter & right_counter).values())
    return (2 * overlap) / (len(left) + len(right))


def title_variants(value: str) -> List[str]:
    raw = html.unescape(value or '').strip()
    variants = [raw]
    for separator in ['：', ':', ' - ', '｜', '|', '·']:
        if separator in raw:
            head = raw.split(separator, 1)[0].strip()
            if head:
                variants.append(head)

    result = []
    seen = set()
    for item in variants:
        key = normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


def title_similarity(left: str, right: str) -> float:
    best = 0.0
    for l_item in title_variants(left):
        for r_item in title_variants(right):
            best = max(best, similarity(l_item, r_item))
    return best


def parse_search_candidates(html_text: str) -> List[Tuple[str, str, str]]:
    section_match = re.search(r'<ul class="search_results_subjects">([\s\S]*?)</ul>', html_text, re.I)
    section = section_match.group(1) if section_match else html_text

    item_pattern = re.compile(r'<li>([\s\S]*?)</li>', re.I)
    href_pattern = re.compile(r'href="([^"]*?/book/subject/\d+/?)"', re.I)
    title_pattern = re.compile(r'<span[^>]*class="subject-title"[^>]*>(.*?)</span>', re.I)
    rating_pattern = re.compile(r'<p[^>]*class="rating"[^>]*>[\s\S]*?<span>([^<]+)</span>', re.I)

    results = []
    seen = set()
    for item_html in item_pattern.findall(section):
        href_match = href_pattern.search(item_html)
        title_match = title_pattern.search(item_html)
        if not href_match or not title_match:
            continue

        subject_match = re.search(r'/book/subject/(\d+)/?', href_match.group(1))
        if not subject_match:
            continue

        url = f'https://book.douban.com/subject/{subject_match.group(1)}/'
        title = strip_html(title_match.group(1))
        rating_match = rating_pattern.search(item_html)
        rating = strip_html(rating_match.group(1)) if rating_match else ''

        key = (title, rating, url)
        if key not in seen:
            seen.add(key)
            results.append(key)
    return results


def parse_detail_metadata(html_text: str, fallback_url: str) -> Dict[str, str]:
    info_match = re.search(r'<div id="info"[\s\S]*?</div>', html_text, re.I)
    info_text = strip_html(info_match.group(0)) if info_match else ''

    def info_field(name: str) -> str:
        pattern = re.compile(
            rf'{name}\s*[:：]\s*(.*?)(?=作者\s*[:：]|出版社\s*[:：]|副标题\s*[:：]|原作名\s*[:：]|译者\s*[:：]|出版年\s*[:：]|页数\s*[:：]|定价\s*[:：]|装帧\s*[:：]|isbn\s*[:：]|$)',
            re.I,
        )
        match = pattern.search(info_text)
        return match.group(1).strip() if match else ''

    def meta(property_name: str) -> str:
        pattern = re.compile(rf'<meta[^>]+property=["\']{property_name}["\'][^>]+content=["\']([^"\']+)["\']', re.I)
        match = pattern.search(html_text)
        return strip_html(match.group(1)) if match else ''

    rating_match = re.search(r'<strong[^>]*class="ll rating_num"[^>]*>([^<]+)</strong>', html_text, re.I)

    return {
        'title': meta('og:title'),
        'author': info_field('作者'),
        'isbn': meta('book:isbn') or info_field('ISBN'),
        'rating': strip_html(rating_match.group(1)) if rating_match else '',
        'url': meta('og:url') or fallback_url,
    }


def choose_candidate(title: str, author: str, candidates: Sequence[Tuple[str, str, str]]) -> Tuple[str, float, Optional[Candidate], List[Candidate]]:
    normalized_author = normalize_author(author)
    ranked = sorted(candidates[:MAX_CANDIDATES], key=lambda item: title_similarity(title, item[0]), reverse=True)

    scored: List[Candidate] = []
    for candidate_title, candidate_rating, candidate_url in ranked[:DETAIL_CHECK_LIMIT]:
        detail_html = fetch_text(candidate_url)
        detail = parse_detail_metadata(detail_html, candidate_url)
        detail_title = detail['title'] or candidate_title
        detail_author = detail['author']
        title_score = title_similarity(title, detail_title)
        author_score = similarity(normalized_author, normalize_author(detail_author)) if normalized_author else 0.55
        score = (title_score * 0.72) + (author_score * 0.28)

        scored.append(
            Candidate(
                title=detail_title,
                author=detail_author,
                url=detail['url'] or candidate_url,
                rating=detail['rating'] or candidate_rating,
                isbn=detail['isbn'],
                score=score,
                title_score=title_score,
                author_score=author_score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    if not scored:
        return 'no-match', 0.0, None, []

    best = scored[0]
    second = scored[1] if len(scored) > 1 else None

    if best.title_score < 0.72:
        return 'no-match', best.score, None, scored

    if second and best.score - second.score < 0.08 and second.title_score > 0.75:
        author_gap = similarity(normalize_author(best.author), normalize_author(second.author))
        if author_gap < 0.72:
            return 'ambiguous-match', best.score, None, scored

    return 'matched', best.score, best, scored


def search_book(title: str, author: str) -> Tuple[str, float, Optional[Candidate], List[Candidate]]:
    query_text = title.strip()
    if author.strip():
        query_text = f'{query_text} {author.strip()}'

    search_url = f'https://m.douban.com/search/?query={urllib.parse.quote(query_text)}'
    html_text = fetch_text(search_url)
    candidates = parse_search_candidates(html_text)[:MAX_CANDIDATES]

    if not candidates and author.strip():
        fallback_url = f'https://m.douban.com/search/?query={urllib.parse.quote(title)}'
        html_text = fetch_text(fallback_url)
        candidates = parse_search_candidates(html_text)[:MAX_CANDIDATES]

    return choose_candidate(title, author, candidates)


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: Sequence[str]) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_existing_row(row: Dict[str, str]) -> Dict[str, str]:
    metadata_status = (row.get('metadata_status') or '').strip()
    if metadata_status == 'matched':
        reading_status = 'metadata-ready'
    elif metadata_status in {'no-match', 'ambiguous-match'}:
        reading_status = 'metadata-review'
    else:
        reading_status = 'pending-metadata'

    return {
        'book_id': (row.get('book_id') or '').strip(),
        'title': (row.get('title') or '').strip(),
        'author': (row.get('author') or '').strip(),
        'reading_status': reading_status,
        'metadata_status': metadata_status,
        'metadata_confidence': (row.get('metadata_confidence') or '').strip(),
        'matched_title': (row.get('matched_title') or '').strip(),
        'matched_author': (row.get('matched_author') or '').strip(),
        'douban_url': (row.get('douban_url') or '').strip(),
        'isbn': (row.get('isbn') or '').strip(),
        'rating': (row.get('rating') or '').strip(),
        'notes': (row.get('notes') or '').strip(),
    }


def row_has_metadata(row: Dict[str, str]) -> bool:
    return row.get('metadata_status', '').strip() in {'matched', 'no-match', 'ambiguous-match'}


def enrich_row(row: Dict[str, str]) -> Dict[str, str]:
    status, confidence, best, scored = search_book(row['title'], row.get('author', ''))

    updated = dict(row)
    updated['metadata_status'] = status
    updated['metadata_confidence'] = f'{confidence:.2f}'
    updated['matched_title'] = ''
    updated['matched_author'] = ''
    updated['douban_url'] = ''
    updated['isbn'] = ''
    updated['rating'] = ''

    notes = updated.get('notes', '').strip()
    if status != 'matched' or not best:
        preview = ' | '.join(f'{item.title} / {item.author}' for item in scored[:3])
        updated['notes'] = f'{notes} | search_preview: {preview}'.strip(' |')
        updated['reading_status'] = 'metadata-review'
        return updated

    updated['matched_title'] = best.title
    updated['matched_author'] = best.author
    updated['douban_url'] = best.url
    updated['isbn'] = best.isbn
    updated['rating'] = best.rating
    updated['notes'] = notes
    updated['reading_status'] = 'metadata-ready'
    return updated


def mark_row_error(row: Dict[str, str], error: Exception) -> Dict[str, str]:
    updated = dict(row)
    notes = updated.get('notes', '').strip()
    updated['metadata_status'] = 'no-match'
    updated['metadata_confidence'] = '0.00'
    updated['matched_title'] = ''
    updated['matched_author'] = ''
    updated['douban_url'] = ''
    updated['isbn'] = ''
    updated['rating'] = ''
    updated['reading_status'] = 'metadata-review'
    updated['notes'] = f'{notes} | processor_error: {type(error).__name__}: {error}'.strip(' |')
    return updated


def sort_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rank = {'matched': 0, 'ambiguous-match': 1, 'no-match': 2, '': 3}
    return sorted(rows, key=lambda row: (rank.get(row.get('metadata_status', ''), 9), int(row['book_id'] or '0')))


def summarize(rows: Sequence[Dict[str, str]]) -> Dict[str, object]:
    counter = Counter(row.get('metadata_status', '') or 'pending' for row in rows)
    return {
        'total_rows': len(rows),
        'metadata_status': dict(counter),
        'metadata_ready_rows': sum(1 for row in rows if row.get('reading_status') == 'metadata-ready'),
        'metadata_review_rows': sum(1 for row in rows if row.get('reading_status') == 'metadata-review'),
        'pending_metadata_rows': sum(1 for row in rows if row.get('reading_status') == 'pending-metadata'),
    }


def initialize_derived_files() -> None:
    write_csv(RAW_Q2_CSV, [], RAW_Q2_FIELDS)
    write_csv(Q2_POOL_CSV, [], Q2_POOL_FIELDS)
    write_csv(Q1_CLUSTERS_CSV, [], Q1_CLUSTER_FIELDS)


def cleanup_obsolete_reports() -> None:
    for path in [
        BASE_DIR / 'sample_run_report.json',
        BASE_DIR / 'full_run_report.json',
        BASE_DIR / 'processing_progress.json',
    ]:
        if path.exists():
            path.unlink()


def persist_books(rows: List[Dict[str, str]], final: bool = False) -> Dict[str, object]:
    materialized = sort_rows(rows)
    write_csv(BOOKS_CSV, materialized, OUTPUT_FIELDS)
    report = summarize(materialized)
    report['finalized'] = final
    report['processed_rows'] = sum(1 for row in materialized if row_has_metadata(row))
    METADATA_PROGRESS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def reset_derived_state() -> Dict[str, object]:
    rows = [normalize_existing_row(row) for row in load_rows(BOOKS_CSV)]
    initialize_derived_files()
    cleanup_obsolete_reports()
    report = persist_books(rows, final=True)
    report['action'] = 'reset-derived-state'
    return report


def process(sample_size: Optional[int] = None, max_new_rows: Optional[int] = None) -> Dict[str, object]:
    started_at = time.time()
    rows = [normalize_existing_row(row) for row in load_rows(BOOKS_CSV)]

    if sample_size:
        sample_rows = []
        for row in rows[:sample_size]:
            if row_has_metadata(row):
                sample_rows.append(row)
                continue
            try:
                sample_rows.append(enrich_row(row))
            except Exception as error:
                sample_rows.append(mark_row_error(row, error))
        report = summarize(sample_rows)
        report['sample_titles'] = [row['title'] for row in sample_rows]
        report['elapsed_seconds'] = round(time.time() - started_at, 2)
        return report

    total = len(rows)
    newly_processed = 0
    for index, row in enumerate(rows, 1):
        if row_has_metadata(row):
            continue
        if max_new_rows is not None and newly_processed >= max_new_rows:
            break

        try:
            rows[index - 1] = enrich_row(row)
        except Exception as error:
            rows[index - 1] = mark_row_error(row, error)

        newly_processed += 1
        persist_books(rows, final=False)
        print(f'[{index}/{total}] {row["title"]} -> {rows[index - 1]["metadata_status"]}', flush=True)
        time.sleep(REQUEST_GAP_SECONDS)

    report = persist_books(rows, final=True)
    report['newly_processed_rows'] = newly_processed
    report['remaining_incomplete_rows'] = sum(1 for row in rows if not row_has_metadata(row))
    report['elapsed_seconds'] = round(time.time() - started_at, 2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample-size', type=int, default=None)
    parser.add_argument('--max-new-rows', type=int, default=None)
    parser.add_argument('--reset-derived', action='store_true')
    args = parser.parse_args()

    if args.reset_derived:
        report = reset_derived_state()
    else:
        report = process(sample_size=args.sample_size, max_new_rows=args.max_new_rows)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
