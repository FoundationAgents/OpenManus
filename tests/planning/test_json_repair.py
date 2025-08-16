import json

from app.planning.json_repair import (
    balance_braces_brackets,
    normalize_unicode_quotes,
    remove_json_comments,
    remove_trailing_commas,
    repair_json,
    strip_markdown_fences,
    trim_to_outermost_json,
)


def test_fenced_with_prose():
    payload = """```json
    {"a": 1, "b": 2,}
    ```
    trailing prose that should be ignored
    """
    s = strip_markdown_fences(payload)
    s = trim_to_outermost_json(s)
    s = remove_trailing_commas(s)
    obj = json.loads(s)
    assert obj == {"a": 1, "b": 2}


def test_smart_quotes_and_comments():
    raw = '{“name”: "Joao", /*coment*/ "age": 21,}'
    s = normalize_unicode_quotes(raw)
    s = remove_json_comments(s)
    s = remove_trailing_commas(s)
    obj = json.loads(s)
    assert obj == {"name": "Joao", "age": 21}


def test_balance_brace():
    raw = '{"a": 1'
    s = balance_braces_brackets(raw)
    obj = json.loads(s)
    assert obj == {"a": 1}


def test_full_repair_pipeline():
    raw = """```json
    {“x”: 1, "arr": [1,2,], // end
     "note": "linha
     quebrada"}
    ```"""
    repaired, notes = repair_json(raw)
    assert notes  # houve reparos
    obj = json.loads(repaired)
    assert obj["x"] == 1 and obj["arr"] == [1, 2]
