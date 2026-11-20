"""Built-in mechanical tools: document search and arithmetic."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any, Dict, List


def search_documents(db, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Mechanical FTS & candidate search: locates course slides and documents.
    """
    q = (query or "").strip()
    if not q:
        return []

    # Split into search tokens
    clean_tokens = [t.lower() for t in re.split(r"[\s\-_,.:]+", q) if len(t) >= 2]
    candidates = db.search_candidates(keywords=clean_tokens, limit=limit * 2)

    results = []
    for c in candidates[:limit]:
        results.append({
            "filename": c.get("file_name", ""),
            "path": c.get("file_path", ""),
            "extension": c.get("file_ext", ""),
            "snippet": (c.get("summary") or c.get("file_name") or "")[:200],
            "score": round(float(c.get("rank", 1.0)), 2),
        })
    return results


def calculate(expression):
    """Small arithmetic with bounded intermediate values and no code execution."""
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError("Expression is too large")
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
                  ast.Pow: operator.pow}

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            value = evaluate(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > 1000 or (isinstance(left, int) and right > 0 and left.bit_length() * right > 4096):
                    raise ValueError("Exponent exceeds the calculator budget")
            value = operations[type(node.op)](left, right)
        else:
            raise ValueError("Unsupported arithmetic expression")
        if type(value) not in (int, float) or (isinstance(value, int) and value.bit_length() > 4096) or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError("Result exceeds the calculator budget")
        return value

    return str(evaluate(tree.body))
