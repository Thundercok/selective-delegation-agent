"""Deterministic reading inputs: supplied cards and recalculated natal profiles."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def key(text):
    value = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


MAJORS = ('fool', 'magician', 'high priestess', 'empress', 'emperor', 'hierophant',
          'lovers', 'chariot', 'strength', 'hermit', 'wheel of fortune', 'justice',
          'hanged man', 'death', 'temperance', 'devil', 'tower', 'star', 'moon',
          'sun', 'judgement', 'world')
SUITS = {'pent': 'Pentacles', 'pentacles': 'Pentacles', 'pentacle': 'Pentacles',
         'cups': 'Cups', 'cup': 'Cups', 'wands': 'Wands', 'wand': 'Wands',
         'swords': 'Swords', 'sword': 'Swords'}
RANKS = {**{str(i): str(i) for i in range(2, 11)}, '1': 'Ace', 'a': 'Ace', 'ace': 'Ace',
         'page': 'Page', 'knight': 'Knight', 'queen': 'Queen', 'king': 'King'}


def parse_cards(text):
    """Atomic manual entry, preserving jumper/reversal and reading order."""
    if len(text) > 2000:
        raise ValueError('Nhập tối đa 2.000 ký tự và 12 lá mỗi lần.')
    entries = [s.strip() for s in re.split(r'[,;\n]+', text) if s.strip()]
    if len(entries) > 12:
        raise ValueError('Bàn xem hiện hỗ trợ tối đa 12 lá.')
    result, seen, position = [], set(), 0
    for raw in entries:
        value = key(raw)
        jumper = bool(re.match(r'^(?:roi|la roi|jumper)\s*:\s*', value))
        value = re.sub(r'^(?:roi|la roi|jumper)\s*:\s*', '', value)
        reversed_card = bool(re.search(r'\s+(?:rev|reversed|nguoc)$', value))
        value = re.sub(r'\s+(?:rev|reversed|nguoc|upright|xuoi)$', '', value)
        value = re.sub(r'^the\s+', '', value)
        if value == 'judgment':
            value = 'judgement'
        if value in MAJORS:
            title, suit = value.title(), 'Major'
            numeral = str(MAJORS.index(value))
        else:
            parts = value.replace(' of ', ' ').split()
            if len(parts) != 2 or parts[0] not in RANKS or parts[1] not in SUITS:
                raise ValueError(f'Chưa nhận ra “{raw}”. Ví dụ: 4 pent, 8 cups, devil rev.')
            numeral, suit = RANKS[parts[0]], SUITS[parts[1]]
            title = f'{numeral} of {suit}'
        if title in seen:
            raise ValueError(f'“{title}” đang lặp. Kiểm tra lại các lá đã nhập.')
        seen.add(title)
        if not jumper:
            position += 1
        result.append({'title': title, 'suit': suit, 'numeral': numeral,
                       'reversed': reversed_card, 'jumper': jumper,
                       'position': 0 if jumper else position})
    return result


def load_natal_profile(path):
    """Load explicit saved birth inputs; natal calculation is removed."""
    raise ValueError('Tính năng bản đồ sao đã được gỡ bỏ khỏi bản phân phối này.')
