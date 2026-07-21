import os

import pytest

from rustchunker import chunk_files

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_path(name):
    return os.path.join(FIXTURES, name)


def test_chunk_files_reads_txt_md_html():
    paths = [fixture_path("sample.txt"), fixture_path("sample.md"), fixture_path("sample.html")]
    result = chunk_files(paths, max_tokens=8)
    assert len(result) > 0
    source_files = {c.metadata["source_file"] for c in result}
    assert source_files == set(paths)


def test_chunk_files_strips_markdown():
    result = chunk_files([fixture_path("sample.md")], max_tokens=100)
    combined = " ".join(c.text for c in result)
    assert "**" not in combined
    assert "[link]" not in combined
    assert "markdown" in combined


def test_chunk_files_strips_html_tags_and_scripts():
    result = chunk_files([fixture_path("sample.html")], max_tokens=100)
    combined = " ".join(c.text for c in result)
    assert "<" not in combined
    assert "console.log" not in combined
    assert "Sample HTML" in combined


def test_chunk_files_metadata_fields():
    result = chunk_files([fixture_path("sample.txt")], max_tokens=8, strategy="sentence")
    total_chunks = len(result)
    for c in result:
        assert c.metadata["source_file"] == fixture_path("sample.txt")
        assert c.metadata["total_chunks"] == total_chunks
        assert c.metadata["strategy_used"] == "sentence"
        # page_number was removed in 1.0 (never populated); the key must be
        # gone from the schema, not present-and-None.
        assert "page_number" not in c.metadata
        assert set(c.metadata.keys()) == {"source_file", "total_chunks", "strategy_used"}


def test_chunk_files_unsupported_extension_raises():
    with pytest.raises(ValueError):
        chunk_files([fixture_path("nonexistent.pdf")], max_tokens=8)


def test_chunk_files_missing_file_raises():
    with pytest.raises(OSError):
        chunk_files([fixture_path("does_not_exist.txt")], max_tokens=8)


def test_chunk_files_plain_chunk_has_no_source_file():
    from rustchunker import chunk

    result = chunk("hello world this is a test", max_tokens=3)
    assert result[0].metadata["source_file"] is None
    assert result[0].metadata["strategy_used"] == "fixed"


def test_chunk_files_accepts_pathlib_path():
    from pathlib import Path

    # pathlib.Path (os.PathLike), not str -- must be accepted.
    paths = [Path(fixture_path("sample.txt")), Path(fixture_path("sample.md"))]
    result = chunk_files(paths, max_tokens=8)
    assert len(result) > 0
    # source_file comes back as the string form of each path.
    assert {c.metadata["source_file"] for c in result} == {str(p) for p in paths}


def test_chunk_files_empty_path_list_returns_no_chunks():
    assert chunk_files([], max_tokens=8) == []


def test_chunk_files_on_error_raise_is_default():
    # Default on_error="raise": one bad file aborts the whole batch.
    paths = [fixture_path("sample.txt"), fixture_path("bad.pdf")]
    with pytest.raises(ValueError):
        chunk_files(paths, max_tokens=8)


def test_chunk_files_on_error_skip_drops_bad_files():
    # on_error="skip": the unsupported .pdf is dropped, the good .txt survives.
    paths = [fixture_path("sample.txt"), fixture_path("bad.pdf")]
    result = chunk_files(paths, max_tokens=8, on_error="skip")
    assert len(result) > 0
    assert {c.metadata["source_file"] for c in result} == {fixture_path("sample.txt")}


def test_chunk_files_on_error_skip_missing_file():
    paths = [fixture_path("sample.txt"), fixture_path("does_not_exist.txt")]
    result = chunk_files(paths, max_tokens=8, on_error="skip")
    assert {c.metadata["source_file"] for c in result} == {fixture_path("sample.txt")}


def test_chunk_files_invalid_on_error_value_raises():
    with pytest.raises(ValueError):
        chunk_files([fixture_path("sample.txt")], max_tokens=8, on_error="ignore")


def test_chunk_files_bad_max_tokens_raises_even_when_skipping():
    # A config error must fail loudly regardless of on_error, rather than
    # being silently swallowed into an empty result.
    with pytest.raises(ValueError):
        chunk_files([fixture_path("sample.txt")], max_tokens=0, on_error="skip")


def test_chunk_files_strips_utf8_bom(tmp_path):
    # A leading BOM must not leak into the first chunk's text.
    p = tmp_path / "bom.txt"
    p.write_text("﻿Hello world. Bye now.", encoding="utf-8")
    result = chunk_files([p], max_tokens=8)
    assert len(result) > 0
    assert not result[0].text.startswith("﻿")
    assert result[0].text.startswith("Hello")


def test_chunk_files_index_is_per_file_not_global():
    # index restarts at 0 for each file; the flat list therefore repeats
    # index values across files. Documented behavior -- lock it in.
    paths = [fixture_path("sample.txt"), fixture_path("sample.md")]
    result = chunk_files(paths, max_tokens=5, strategy="sentence")
    by_file = {}
    for c in result:
        by_file.setdefault(c.metadata["source_file"], []).append(c.index)
    assert len(by_file) == 2
    for indices in by_file.values():
        assert indices == list(range(len(indices)))  # each file: 0,1,2,...
