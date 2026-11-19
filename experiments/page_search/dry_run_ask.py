"""Ask three tuning questions through the app's selected-document path (RESULTS.md, "Chạy thử").

    .venv/bin/python experiments/page_search/dry_run_ask.py SLIDES_DIR
"""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rat.engine.assistant_runtime import AssistantRuntime  # noqa: E402
from rat.engine.selected_document_qa import answer_selected_document  # noqa: E402

CASES = [
    ('t04', 'Chapter 14.1 - Virtual memory', 'TLB là gì, nằm ở slide nào?', [11, 12]),
    ('p04', 'Chapter 12 - Pipelining',
     'Đoán trước lệnh rẽ nhánh có nhảy hay không để khỏi phải chờ được nói ở slide nào?', [84, 85]),
    ('p05', 'Chapter 13.2 - Cache Part II',
     'Bộ nhớ đệm cho phép một khối dữ liệu nằm ở vài chỗ cố định trong một nhóm được nói ở slide nào?', [9, 10]),
]


def main(slides_dir):
    files = sorted(Path(slides_dir).glob('*.pdf'))
    with AssistantRuntime(active_tool_packs=[]) as runtime:
        for case_id, name, question, pages in CASES:
            path = str(next(f for f in files if f.name.startswith(name)))
            steps = []
            started = time.perf_counter()
            response = answer_selected_document(runtime, question, path, selected_document_path=path,
                                                on_step=lambda step: steps.append(step))
            seconds = time.perf_counter() - started
            print(f'=== {case_id} accepted pages {pages}  {seconds:.1f} s  error={response.error}')
            for step in steps:
                name_ = getattr(step, 'tool_name', None) or (step.get('tool_name') if isinstance(step, dict) else None)
                result = getattr(step, 'tool_result', None) or {}
                if name_:
                    print(f'  step {name_} page={result.get("page") if isinstance(result, dict) else None}')
            for source in response.sources:
                print(f'  source page={source.get("page")} read={source.get("read")} '
                      f'start={source.get("start_offset")} truncated={source.get("truncated")}')
            print('  answer:', (response.answer or '').strip().replace('\n', ' / ')[:700])


if __name__ == '__main__':
    main(sys.argv[1])
