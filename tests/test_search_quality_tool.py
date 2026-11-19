"""The quality score must count files as a person sees them and keep question sources apart."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'measure_search_quality', Path(__file__).resolve().parents[1] / 'tools/measure_search_quality.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def rows(*paths):
    return [{'file_path': path} for path in paths]


def test_rank_matches_part_of_the_file_name_ignoring_case_and_folder():
    assert tool.rank_of(['invoice'], ['/a/invoice_dir/note.txt', '/b/Invoice-1.pdf']) == 2
    assert tool.rank_of(['invoice'], ['/a/note.txt']) is None


def test_several_chunks_of_one_file_count_as_one_result():
    assert tool.unique_files(rows('/a.pdf', '/a.pdf', '/b.pdf')) == ['/a.pdf', '/b.pdf']


def test_summary_counts_top_positions_and_misses():
    summary = tool.summarize([1, 2, 4, None])
    assert summary == {'questions': 4, 'top_1': 1, 'top_3': 2, 'not_found': 1,
                       'mean_reciprocal_rank': round((1 + 1 / 2 + 1 / 4) / 4, 3)}


def test_sources_are_scored_apart_and_together():
    results = {'q1': rows('/right.pdf'), 'q2': rows('/wrong.pdf')}
    cases = [{'query': 'q1', 'expect': ['right'], 'source': 'draft'},
             {'query': 'q2', 'expect': ['right'], 'source': 'user'}]
    lines, summary = tool.score(cases, results.__getitem__)
    assert [line['rank'] for line in lines] == [1, None]
    assert summary['draft']['top_1'] == 1 and summary['user']['top_1'] == 0
    assert summary['all']['questions'] == 2


def test_empty_question_set_does_not_divide_by_zero():
    assert tool.summarize([])['mean_reciprocal_rank'] == 0.0


def test_page_is_scored_on_the_right_file_even_when_search_misses_it():
    files = ['/c/Chapter 12 - Pipelining.pdf', '/c/Chapter 13.1 - Cache Part I.pdf']
    picked = {'/c/Chapter 12 - Pipelining.pdf': 47, '/c/Chapter 13.1 - Cache Part I.pdf': 3}
    cases = [{'query': 'hazards', 'expect': ['Pipelining'], 'pages': [47], 'source': 'term'},
             {'query': 'locality', 'expect': ['Cache Part I'], 'pages': [18], 'source': 'term'}]
    results = {'hazards': rows('/elsewhere.pdf'), 'locality': rows('/c/Chapter 13.1 - Cache Part I.pdf')}
    lines, summary = tool.score(cases, results.__getitem__,
                                page_of=lambda query, path: picked[path], files=files)
    assert [(line['rank'], line['page'], line['page_ok']) for line in lines] == [(None, 47, True), (1, 3, False)]
    # Right page given the file counts the first; right page in the top 3 needs the file found too.
    assert summary['term']['page_given_file'] == 1 and summary['term']['page_top_3'] == 0


def test_no_page_picked_or_no_file_found_counts_as_wrong():
    cases = [{'query': 'q', 'expect': ['missing'], 'pages': [2]},
             {'query': 'r', 'expect': ['here'], 'pages': [2]}]
    lines, summary = tool.score(cases, lambda query: [], page_of=lambda query, path: None,
                                files=['/x/here.pdf'])
    assert [line['page_ok'] for line in lines] == [False, False]
    assert summary['all']['page_given_file'] == 0 and 'page_top_3' not in summary['all']


def test_questions_without_pages_keep_the_file_only_summary():
    lines, summary = tool.score([{'query': 'q', 'expect': ['a']}], lambda query: rows('/a.pdf'),
                                page_of=lambda query, path: 1, files=['/a.pdf'])
    assert 'page_ok' not in lines[0] and 'page_given_file' not in summary['all']
