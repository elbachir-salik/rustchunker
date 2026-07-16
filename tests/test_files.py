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
        assert c.metadata["page_number"] is None


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
