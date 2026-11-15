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
        chunk_files([fixture_path("nonexistent.doc")], max_tokens=8)


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
    paths = [fixture_path("sample.txt"), fixture_path("bad.doc")]
    with pytest.raises(ValueError):
        chunk_files(paths, max_tokens=8)


def test_chunk_files_on_error_skip_drops_bad_files():
    # on_error="skip": the unsupported .doc is dropped, the good .txt survives.
    paths = [fixture_path("sample.txt"), fixture_path("bad.doc")]
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


@pytest.mark.parametrize("on_error", ["raise", "skip"])
@pytest.mark.parametrize("names", [[], ["sample.txt"], ["does_not_exist.txt"]])
def test_chunk_files_rejects_unknown_strategy_before_reading(names, on_error):
    with pytest.raises(ValueError, match="unknown strategy"):
        chunk_files(
            [fixture_path(name) for name in names],
            max_tokens=8,
            strategy="sentance",
            on_error=on_error,
        )


@pytest.mark.parametrize("on_error", ["raise", "skip"])
def test_chunk_files_invalid_utf8(tmp_path, on_error):
    bad = tmp_path / "invalid.txt"
    bad.write_bytes(bytes([255, 254]))
    good = fixture_path("sample.txt")
    if on_error == "raise":
        with pytest.raises(OSError):
            chunk_files([good, bad], max_tokens=4, on_error=on_error)
    else:
        result = chunk_files([good, bad], max_tokens=4, on_error=on_error)
        assert result
        assert {c.metadata["source_file"] for c in result} == {good}


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
@pytest.mark.parametrize("overlap", [0, 1, 3])
def test_chunk_files_matches_individual_documents(tmp_path, strategy, overlap):
    from rustchunker import chunk

    texts = ["你好。世界。再见。", "", "  café 🎉. Next sentence. More words here."]
    paths = [tmp_path / f"document_{i}.txt" for i in range(len(texts))]
    expected = []
    for path, text in zip(paths, texts):
        path.write_text(text, encoding="utf-8")
        for c in chunk(text, max_tokens=4, overlap=overlap, strategy=strategy):
            expected.append((
                c.text, c.start, c.end, c.index,
                {**c.metadata, "source_file": str(path)},
            ))
    result = chunk_files(paths, max_tokens=4, overlap=overlap, strategy=strategy)
    assert [(c.text, c.start, c.end, c.index, c.metadata) for c in result] == expected
