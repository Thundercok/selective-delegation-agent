"""Time each stage of the dry-run ask path: tool steps, keyword translation, answer call (with Ollama phases).

    .venv/bin/python experiments/page_search/time_ask_stages.py SLIDES_DIR [ROUNDS]
"""
import sys, time, json
from pathlib import Path
repo = Path(__file__).resolve().parents[2]; slides = sys.argv[1]; rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 2
sys.path.insert(0, str(repo)); sys.path.insert(0, str(repo / 'experiments/page_search'))
import dry_run_ask
from rat.engine.assistant_runtime import AssistantRuntime
from rat.engine.selected_document_qa import answer_selected_document
from rat.engine import slm, page_keywords, page_match

events = []
T0 = [0.0]
def log(kind, **kw):
    events.append(dict(t=round(time.perf_counter() - T0[0], 2), kind=kind, **kw))

def ns(d, k):
    v = (d or {}).get(k); return round(v / 1e9, 2) if isinstance(v, (int, float)) else None

orig_chat = slm.SLMEngine.chat_with_meta
def chat(self, messages, tools, *a, **kw):
    s = time.perf_counter(); meta = orig_chat(self, messages, tools, *a, **kw)
    raw = meta.get('raw_response') or {}
    log('chat', model=self.model, wall=round(time.perf_counter() - s, 2), load=ns(raw, 'load_duration'),
        prompt_s=ns(raw, 'prompt_eval_duration'), prompt_tok=raw.get('prompt_eval_count'),
        gen_s=ns(raw, 'eval_duration'), gen_tok=raw.get('eval_count'), err=meta.get('error'),
        fmt=bool(kw.get('response_format')))
    return meta
slm.SLMEngine.chat_with_meta = chat

orig_gen = slm.SLMEngine.generate_with_meta
def gen(self, *a, **kw):
    s = time.perf_counter(); r = orig_gen(self, *a, **kw)
    log('generate', model=self.model, wall=round(time.perf_counter() - s, 2),
        prompt_tok=r.get('prompt_tokens'), gen_tok=r.get('completion_tokens'), err=r.get('error'))
    return r
slm.SLMEngine.generate_with_meta = gen

orig_kq = page_keywords.keyword_query
def kq(q, client, *a, **kw):
    s = time.perf_counter(); r = orig_kq(q, client, *a, **kw)
    log('keyword_query', wall=round(time.perf_counter() - s, 2), client=type(client).__name__,
        keywords=(r or {}).get('keywords'))
    return r
page_keywords.keyword_query = kq

with AssistantRuntime(active_tool_packs=[]) as runtime:
    print('document_model_client:', type(runtime.document_model_client).__name__,
          getattr(runtime.document_model_client, 'model', None))
    files = sorted(Path(slides).glob('*.pdf'))
    for r in range(1, rounds + 1):
        for case_id, name, question, pages in dry_run_ask.CASES:
            page_match._SLM_KEYWORD_CACHE.clear()
            path = str(next(f for f in files if f.name.startswith(name)))
            events.clear(); T0[0] = time.perf_counter()
            resp = answer_selected_document(runtime, question, path, selected_document_path=path,
                                            on_step=lambda st: log('step', tool=getattr(st, 'tool_name', None)))
            total = time.perf_counter() - T0[0]
            print(f'=== run {r} {case_id} total {total:.1f} s err={resp.error}')
            for e in events:
                print('  ', json.dumps(e, ensure_ascii=False))
