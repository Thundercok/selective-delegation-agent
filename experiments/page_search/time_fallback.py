"""Extra wait that slm_fallback adds to picking a page on the ask path (RESULTS.md, "Thời gian chờ thêm").

    .venv/bin/python experiments/page_search/time_fallback.py QUESTIONS.json SLIDES_DIR
"""
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rat.crawler.extractors import extract_document_content  # noqa: E402
from rat.engine import page_match  # noqa: E402
from rat.engine.page_match import page_window, query_terms  # noqa: E402
from rat.engine.selected_document_qa import MAX_READ_CHARS, MODEL  # noqa: E402
from rat.engine.slm import SLMEngine  # noqa: E402


def timed(content, question, fallback, client):
    page_match._SLM_KEYWORD_CACHE.clear()
    calls = []
    original = page_match.translate_query_terms_slm

    def counting(q, model_client=None):
        calls.append(q)
        return original(q, model_client=model_client)

    page_match.translate_query_terms_slm = counting
    try:
        started = time.perf_counter()
        window = page_window(content, query_terms(question), MAX_READ_CHARS,
                             question=question, slm_fallback=fallback, model_client=client)
        return time.perf_counter() - started, window and window['page'], bool(calls)
    finally:
        page_match.translate_query_terms_slm = original


def main(questions_path, slides_dir):
    files = sorted(str(p) for p in Path(slides_dir).iterdir() if p.suffix.lower() == '.pdf')
    client = SLMEngine(model=MODEL)
    page_match.translate_query_terms_slm('warm up', model_client=client)  # the answer call keeps it loaded
    extra, rows = [], []
    for case in json.loads(Path(questions_path).read_text(encoding='utf-8')):
        path = next(f for f in files if any(part in Path(f).name for part in case['expect']))
        content = extract_document_content(path)
        off, page_off, _ = timed(content, case['query'], False, client)
        on, page_on, called = timed(content, case['query'], True, client)
        extra.append(on - off)
        rows.append((case['id'], called, page_off, page_on, round(on - off, 3)))
    for row in rows:
        print('%-4s model=%-5s page off=%-4s on=%-4s extra %.3f s' % row)
    ordered = sorted(extra)
    print(json.dumps({'questions': len(extra), 'model_called': sum(r[1] for r in rows),
                      'extra_median_s': round(statistics.median(extra), 3),
                      'extra_p90_s': round(ordered[int(0.9 * (len(ordered) - 1))], 3),
                      'extra_max_s': round(ordered[-1], 3)}, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:3])
