from rat.engine import page_keywords
from rat.engine.page_keywords import keyword_query, parse_keywords


class FakeClient:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def chat_with_meta(self, messages, tools, **options):
        self.calls.append((messages, options))
        return {'message': {'content': self.reply} if self.reply is not None else {},
                'error': self.error, 'duration_ms': 812.34}


def test_parse_keywords_splits_strips_and_caps():
    reply = '"stored program", von Neumann;\n- memory , memory, ' + ', '.join(f'w{n}' for n in range(10))
    assert parse_keywords(reply) == ['stored program', 'von Neumann']
    assert parse_keywords('memory , memory') == ['memory']
    assert parse_keywords('') == []


def test_keywords_are_appended_to_the_question(monkeypatch):
    monkeypatch.setattr(page_keywords, 'keyword_messages', lambda q: [{'role': 'user', 'content': q}])
    client = FakeClient('TLB, translation lookaside buffer, cache')

    result = keyword_query('Bảng đổi địa chỉ ảo?', client)

    assert result['query'] == 'Bảng đổi địa chỉ ảo? TLB translation lookaside buffer'
    assert result['keywords'] == ['TLB', 'translation lookaside buffer'] and result['ms'] == 812.3
    assert client.calls[0][1]['thinking'] is False


def test_a_failed_model_call_leaves_the_question_alone(monkeypatch):
    monkeypatch.setattr(page_keywords, 'keyword_messages', lambda q: [{'role': 'user', 'content': q}])

    result = keyword_query('Full adder?', FakeClient('ignored', error='timeout'))

    assert result['query'] == 'Full adder?' and result['keywords'] == [] and result['error'] == 'timeout'
