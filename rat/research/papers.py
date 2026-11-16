"""Paper desk: a folder of arXiv PDFs, indexed and questioned with page citations.

No parallel stack: PDFs go into RAT's own index (``Indexer.index_single_file``) so
the hybrid search finds them; pages come from ``document_intake.pdf.read_pdf``; page
passages are ranked with ``qa_engine.extract_relevant_paragraphs`` and answered by
``qa_engine.answer_question`` with the cloud turned off. Citations are the extracted
page text the answer was given, not model prose.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional


def papers_dir() -> Path:
    from rat.config import RAT_DIR
    return RAT_DIR / "papers"


def add_papers(paths: Iterable[str], folder: Optional[Path] = None, *, index_file=None) -> List[Dict]:
    """Copy PDFs into the paper folder and index each one in RAT's database."""
    folder = folder or papers_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if index_file is None:
        from rat.crawler.indexer import Indexer
        index_file = Indexer().index_single_file
    added = []
    for raw in paths:
        source = Path(raw.removeprefix("file://")).expanduser()
        if source.suffix.lower() != ".pdf" or not source.is_file():
            added.append({"file": source.name, "status": "bỏ qua: không phải tệp PDF"})
            continue
        target = folder / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        indexed = index_file(str(target))
        added.append({"file": target.name, "status": "đã lập chỉ mục" if indexed else "đã có trong chỉ mục"})
    return added


def list_papers(folder: Optional[Path] = None) -> List[Path]:
    folder = folder or papers_dir()
    return sorted(folder.glob("*.pdf")) if folder.is_dir() else []


def _hybrid_candidates(question: str, papers: List[Path]) -> List[Path]:
    from rat.engine.hybrid_search import SearchEngine
    wanted = {str(p.resolve()): p for p in papers}
    results = SearchEngine().search(question, limit=30)["results"]
    ranked = [wanted[str(Path(r.file_path).resolve())] for r in results
              if str(Path(r.file_path).resolve()) in wanted]
    return list(dict.fromkeys(ranked))


def _read_pages(path: Path) -> List[Dict]:
    from document_intake.pdf import read_pdf
    return read_pdf(path)["pages"]


def ask_papers(question: str, folder: Optional[Path] = None, *, max_papers: int = 3, max_passages: int = 4,
               candidates: Optional[Callable[[str, List[Path]], List[Path]]] = None,
               read_pages: Callable[[Path], List[Dict]] = _read_pages,
               score: Optional[Callable] = None, answer: Optional[Callable] = None) -> Dict:
    papers = list_papers(folder)
    if not papers:
        raise ValueError("Bàn bài báo đang trống. Thả PDF vào hoặc chạy: rat papers add <tệp.pdf>.")
    if score is None or answer is None:
        from rat.engine.qa_engine import qa_engine
        score = score or qa_engine.extract_relevant_paragraphs
        answer = answer or (lambda text, q: qa_engine.answer_question(
            text, q, file_name="bàn bài báo", use_cloud_if_available=False))
    try:
        chosen = (candidates or _hybrid_candidates)(question, papers)
    except Exception:
        chosen = []
    chosen = (chosen or papers)[:max_papers]
    passages = []
    for paper in chosen:
        for page in read_pages(paper):
            text = page["text_content"].strip()
            if not text:
                continue
            best = score(text, question, max_paragraphs=1)
            if best and best[0][1] > 0:
                passages.append({"file": paper.name, "page": page["page_num"],
                                 "snippet": best[0][0].strip()[:600], "score": best[0][1]})
    passages.sort(key=lambda p: -p["score"])
    passages = passages[:max_passages]
    if not passages:
        return {"question": question, "answer": "Không tìm thấy trang nào khớp câu hỏi trong các bài đã chọn.",
                "engine": "none", "citations": [], "papers": [p.name for p in chosen]}
    context = "\n\n".join(f"[{i}] {p['file']}, trang {p['page']}:\n{p['snippet']}"
                          for i, p in enumerate(passages, 1))
    result = answer(context, question)
    return {"question": question, "answer": result.get("answer", ""), "engine": result.get("engine", ""),
            "citations": [{"n": i, **{k: p[k] for k in ("file", "page", "snippet")}}
                          for i, p in enumerate(passages, 1)],
            "papers": [p.name for p in chosen]}
