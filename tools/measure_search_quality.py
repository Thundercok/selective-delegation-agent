"""Measure whether meaning search puts the right file near the top, on a person's real files.

The questions name real files, so they live outside the repo:

    ~/.rat/search_quality.json   [{"query": "...", "expect": ["part of a file name"], "source": "user"}]

    python tools/measure_search_quality.py --build     index the configured folders first (slow)
    python tools/measure_search_quality.py             score the questions against the index
    python tools/measure_search_quality.py --db PATH   use another index

A question counts for its "source" separately: questions written by someone who has just read the
file reuse its words and score higher than what a person really types.

A question may also list "pages" (PDF pages, from 1) that answer it. With --files ROOT, the right file
is found under ROOT by name, and its page is picked the way the ask path does (page_match.best_page
on extract_document_content), whether or not search found the file:

    python tools/measure_search_quality.py --questions Q.json --files ROOT --pages-only   no index needed
"""
from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def state_directory():
    return Path(os.environ.get('RAT_STATE_DIR') or Path.home() / '.rat')


def rank_of(expected, paths):
    """1-based position of the first file whose name contains an expected part, or None."""
    wanted = [part.casefold() for part in expected]
    for position, path in enumerate(paths, 1):
        name = Path(path).name.casefold()
        if any(part in name for part in wanted):
            return position
    return None


def unique_files(rows):
    """Search returns one row per matching chunk; a person sees each file once."""
    return list(dict.fromkeys(row['file_path'] for row in rows))


def summarize(ranks):
    total = len(ranks)
    return {
        'questions': total,
        'top_1': sum(rank == 1 for rank in ranks),
        'top_3': sum(rank is not None and rank <= 3 for rank in ranks),
        'not_found': sum(rank is None for rank in ranks),
        'mean_reciprocal_rank': round(sum(1 / rank for rank in ranks if rank) / total, 3) if total else 0.0,
    }


def summarize_pages(lines):
    """Right page given the right file, and right page with the file in the top 3 (needs search)."""
    paged = [line for line in lines if 'page_ok' in line]
    summary = {'with_pages': len(paged), 'page_given_file': sum(line['page_ok'] for line in paged)}
    if any(line['rank'] is not None for line in paged):
        summary['page_top_3'] = sum(line['page_ok'] and line['rank'] is not None and line['rank'] <= 3
                                    for line in paged)
    return summary


def best_page_number(query, path):
    """The page the ask path would open for this question, or None."""
    from rat.crawler.extractors import extract_document_content
    from rat.engine.page_match import best_page, query_terms
    span = best_page(extract_document_content(str(path)), query_terms(query), question=query, slm_fallback=True)
    return span[0] if span else None


def score(cases, search, page_of=None, files=()):
    """Rank each question and summarize per source, plus everything together as 'all'."""
    lines, by_source = [], collections.defaultdict(list)
    files = list(files)
    for case in cases:
        paths = unique_files(search(case['query']))
        rank = rank_of(case['expect'], paths)
        line = {'query': case['query'], 'rank': rank, 'top': [Path(p).name for p in paths[:3]],
                'source': case.get('source', 'unknown')}
        if page_of and case.get('pages'):
            # The right file from the folder, not from search: this scores page picking on its own.
            position = rank_of(case['expect'], files)
            line['page'] = page_of(case['query'], files[position - 1]) if position else None
            line['page_ok'] = line['page'] in case['pages']
        by_source[case.get('source', 'unknown')].append(line)
        by_source['all'].append(line)
        lines.append(line)
    summary = {}
    for source, group in by_source.items():
        summary[source] = summarize([line['rank'] for line in group])
        if any('page_ok' in line for line in group):
            summary[source].update(summarize_pages(group))
    return lines, summary


def build_index(index, roots):
    index.start(roots)
    while index._thread and index._thread.is_alive():
        time.sleep(30)
        print(index.progress(), flush=True)
    print('Indexed', index.count(), 'chunks', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--db', type=Path, default=None, help='index file, default the app index')
    parser.add_argument('--questions', type=Path, default=None, help='default ~/.rat/search_quality.json')
    parser.add_argument('--build', action='store_true', help='index the configured folders into --db first')
    parser.add_argument('--files', type=Path, default=None, help='folder holding the expected files; scores pages')
    parser.add_argument('--pages-only', action='store_true', help='score pages with --files, without the index')
    parser.add_argument('--keywords', action='store_true',
                        help='when the question matches no page, ask the local model for English slide words')
    args = parser.parse_args()
    if args.pages_only and not args.files:
        parser.error('--pages-only needs --files')

    sys.path.insert(0, str(ROOT))
    if args.pages_only:
        search = lambda query: []
    else:
        from rat.engine.semantic_index import SemanticIndex
        index = SemanticIndex(args.db or state_directory() / 'semantic-index.sqlite')
        if args.build:
            from rat.config import config
            build_index(index, config.indexed_directories)
        search = index.search

    questions = args.questions or state_directory() / 'search_quality.json'
    if not questions.exists():
        print(f'No questions at {questions}')
        return 0
    files = sorted(str(p) for p in args.files.rglob('*') if p.is_file()) if args.files else ()
    page_of, rewrites = (best_page_number if args.files else None), {}
    if args.files and args.keywords:
        from rat.engine.page_keywords import keyword_query
        from rat.engine.selected_document_qa import MODEL
        from rat.engine.slm import SLMEngine
        client = SLMEngine(model=MODEL)
        keyword_query('warm up', client, timeout=120)  # load the model so timings are warm

        from rat.crawler.extractors import extract_document_content
        from rat.engine.page_match import best_page, query_terms

        def word_page(query, path):
            # Words only: this mode measures page_keywords, not page_match's own model fallback.
            span = best_page(extract_document_content(str(path)), query_terms(query))
            return span[0] if span else None

        def page_of(query, path):
            # The model is asked only when the question's own words match no page.
            page = word_page(query, path)
            if page is not None:
                return page
            rewrites[query] = keyword_query(query, client)
            return word_page(rewrites[query]['query'], path)
    lines, summary = score(json.loads(questions.read_text(encoding='utf-8')), search,
                           page_of=page_of, files=files)
    if args.pages_only:
        # Without search every rank is None; file scores would read as zero, not as unmeasured.
        summary = {source: {k: v for k, v in s.items() if k in ('with_pages', 'page_given_file')}
                   for source, s in summary.items()}
    for line in lines:
        rank = line['rank'] or '-'
        page = f"  page {line['page'] or '-'} {'ok' if line['page_ok'] else 'WRONG'}" if 'page_ok' in line else ''
        print(f"{rank!s:>2}  [{line['source']}] {line['query']}{page}\n      {' | '.join(line['top']) or '(no results)'}")
        if line['query'] in rewrites:
            rewrite = rewrites[line['query']]
            print(f"      keywords {rewrite['ms']:.0f} ms: {', '.join(rewrite['keywords']) or rewrite['error']}")
    if rewrites:
        summary['keyword_ms_median'] = statistics.median(r['ms'] for r in rewrites.values())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
