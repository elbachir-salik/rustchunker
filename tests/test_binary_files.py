"""Binary document fixtures use only Python's standard library."""
import zlib
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from rustchunker import chunk_files

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def write_docx(path, body, namespace=WORD_NS):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{namespace}"><w:body>{body}</w:body></w:document>')
    return path


def write_pdf(path, pages, media_box=True):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    box = "/MediaBox [0 0 612 792]" if media_box else ""
    for text in pages:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R {box} /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode())
        stream = zlib.compress(b"BT /F1 12 Tf 72 720 Td <" + text.encode("cp1252").hex().encode() + b"> Tj ET")
        objects.append(f"<< /Length {len(stream)} /Filter /FlateDecode >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
@pytest.mark.parametrize("overlap", [0, 1])
@pytest.mark.parametrize("extension", ["pdf", "PDF", "docx", "DOCX"])
def test_binary_files_content_budget_offsets_and_metadata(tmp_path, extension, strategy, overlap):
    path = tmp_path / f"sample.{extension}"
    if extension.lower() == "pdf":
        write_pdf(path, ["Hello caf\u00e9.", "Second page words here."])
    else:
        write_docx(path, '<w:p><w:r><w:t>Hello caf\u00e9.</w:t></w:r></w:p><w:p><w:r><w:t>Second page words here.</w:t></w:r></w:p>')
    whole = chunk_files([path], max_tokens=100, strategy=strategy)[0]
    full = " " * whole.start + whole.text
    assert " ".join(full.split()) == "Hello caf\u00e9. Second page words here."
    chunks = chunk_files([path], max_tokens=3, overlap=overlap, strategy=strategy)
    end = 0
    for index, c in enumerate(chunks):
        assert c.text == full[c.start:c.end]
        assert 0 < len(c.text.split()) <= 3
        assert not full[end:c.start].strip()
        assert c.end > end
        assert c.index == index
        assert c.metadata == {"source_file": str(path), "total_chunks": len(chunks), "strategy_used": strategy}
        end = c.end
    assert not full[end:].strip()


def test_docx_preserves_runs_entities_breaks_and_tables(tmp_path):
    path = write_docx(tmp_path / "parts.docx", '<w:p><w:r><w:t>hel</w:t></w:r><w:r><w:t>lo &amp; world</w:t><w:tab/><w:t>tab</w:t><w:br/><w:t>next</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>cell one</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>cell two</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    text = chunk_files([path], max_tokens=100)[0].text
    assert text.startswith("hello & world\ttab\nnext")
    assert " ".join(text.split()) == "hello & world tab next cell one cell two"


def test_strict_docx_namespace(tmp_path):
    path = write_docx(tmp_path / "strict.docx", '<w:p><w:r><w:t>Strict text.</w:t></w:r></w:p>', namespace="http://purl.oclc.org/ooxml/wordprocessingml/main")
    assert chunk_files([path], max_tokens=10)[0].text.strip() == "Strict text."


@pytest.mark.parametrize("extension", ["pdf", "docx"])
def test_malformed_binary_raise_and_skip(tmp_path, extension):
    bad = tmp_path / f"bad.{extension}"
    bad.write_bytes(b"not a document")
    good = tmp_path / "good.txt"
    good.write_text("Keep these words.", encoding="utf-8")
    with pytest.raises(ValueError, match="failed to extract"):
        chunk_files([bad], max_tokens=10)
    result = chunk_files([good, bad], max_tokens=10, on_error="skip")
    assert [c.metadata["source_file"] for c in result] == [str(good)]


@pytest.mark.parametrize("extension", ["pdf", "docx"])
def test_missing_binary_is_io_error(tmp_path, extension):
    with pytest.raises(OSError):
        chunk_files([tmp_path / f"missing.{extension}"], max_tokens=10)


@pytest.mark.parametrize("xml", [None, "<broken>", "<other/>"])
def test_invalid_docx_main_part(tmp_path, xml):
    path = tmp_path / "invalid.docx"
    with ZipFile(path, "w") as archive:
        if xml is not None:
            archive.writestr("word/document.xml", xml)
    with pytest.raises(ValueError, match="failed to extract"):
        chunk_files([path], max_tokens=10)


def test_empty_docx_and_pdf_without_text(tmp_path):
    empty_docx = write_docx(tmp_path / "empty.docx", "<w:p/>")
    assert chunk_files([empty_docx], max_tokens=10) == []
    empty_pdf = write_pdf(tmp_path / "empty.pdf", [""])
    with pytest.raises(ValueError, match="no extractable text"):
        chunk_files([empty_pdf], max_tokens=10)
    assert chunk_files([empty_pdf], max_tokens=10, on_error="skip") == []


def test_mixed_file_batch_preserves_order(tmp_path):
    pdf = write_pdf(tmp_path / "one.pdf", ["PDF words."])
    docx = write_docx(tmp_path / "two.docx", "<w:p><w:r><w:t>Word text.</w:t></w:r></w:p>")
    text = tmp_path / "three.txt"
    text.write_text("Plain text.", encoding="utf-8")
    chunks = chunk_files([pdf, docx, text], max_tokens=10)
    assert [c.metadata["source_file"] for c in chunks] == [str(pdf), str(docx), str(text)]
    assert [c.index for c in chunks] == [0, 0, 0]


def test_docx_rejects_oversized_main_part(tmp_path):
    path = tmp_path / "oversized.docx"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b" " * (64 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="64 MiB"):
        chunk_files([path], max_tokens=10)


def test_docx_rejects_external_entities(tmp_path):
    path = tmp_path / "entity.docx"
    xml = '<!DOCTYPE w:document [<!ENTITY data SYSTEM "file:///not-read">]><w:document xmlns:w="' + WORD_NS + '"><w:body><w:p><w:r><w:t>&data;</w:t></w:r></w:p></w:body></w:document>'
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
    with pytest.raises(ValueError, match="failed to extract"):
        chunk_files([path], max_tokens=10)


def test_pdf_parser_panic_is_a_skippable_value_error(tmp_path):
    path = write_pdf(tmp_path / "missing-media-box.pdf", ["Text."], media_box=False)
    with pytest.raises(ValueError, match="PDF parser failed"):
        chunk_files([path], max_tokens=10)
    assert chunk_files([path], max_tokens=10, on_error="skip") == []


@pytest.mark.parametrize("namespace", [WORD_NS, "http://purl.oclc.org/ooxml/wordprocessingml/main"])
@pytest.mark.parametrize("branches,expected", [
    ('<c:Choice Requires="w"><w:p><w:r><w:t>Selected.</w:t></w:r></w:p></c:Choice><c:Fallback><w:p><w:r><w:t>Selected.</w:t></w:r></w:p></c:Fallback>', "Before. Selected. After."),
    ('<c:Choice Requires="w"><w:p><w:r><w:t>Selected.</w:t></w:r></w:p></c:Choice><c:Fallback><w:p><w:r><w:t>Old version.</w:t></w:r></w:p></c:Fallback>', "Before. Selected. After."),
    ('<c:Choice Requires="w"><w:p><w:r><w:t>First.</w:t></w:r></w:p></c:Choice><c:Choice Requires="w"><w:p><w:r><w:t>Second.</w:t></w:r></w:p></c:Choice><c:Fallback><w:p><w:r><w:t>Fallback.</w:t></w:r></w:p></c:Fallback>', "Before. First. After."),
    ('<c:Fallback><w:p><w:r><w:t>Fallback.</w:t></w:r></w:p></c:Fallback>', "Before. Fallback. After."),
    ('<c:Choice Requires="w"/><c:Fallback><w:p><w:r><w:t>Hidden.</w:t></w:r></w:p></c:Fallback>', "Before. After."),
    ('<c:Choice Requires="w"><c:AlternateContent><c:Choice Requires="w"><w:p><w:r><w:t>Nested.</w:t></w:r></w:p></c:Choice><c:Fallback><w:p><w:r><w:t>Hidden inner.</w:t></w:r></w:p></c:Fallback></c:AlternateContent></c:Choice><c:Fallback><w:p><w:r><w:t>Hidden outer.</w:t></w:r></w:p></c:Fallback>', "Before. Nested. After."),
], ids=["duplicate", "different-fallback", "multiple-choices", "fallback-only", "empty-choice", "nested"])
def test_docx_extracts_one_alternate_content_branch(tmp_path, namespace, branches, expected):
    body = ('<w:p><w:r><w:t>Before.</w:t></w:r></w:p>'
            '<c:AlternateContent xmlns:c="http://schemas.openxmlformats.org/markup-compatibility/2006">'
            + branches + '</c:AlternateContent>'
            '<w:p><w:r><w:t>After.</w:t></w:r></w:p>')
    path = write_docx(tmp_path / "alternatives.docx", body, namespace=namespace)
    chunks = chunk_files([path], max_tokens=100)
    assert " ".join(c.text for c in chunks).split() == expected.split()


def test_docx_preserves_repeated_text_outside_alternate_content(tmp_path):
    paragraph = '<w:p><w:r><w:t>Repeated text.</w:t></w:r></w:p>'
    path = write_docx(tmp_path / "repeated.docx", paragraph + paragraph)
    assert chunk_files([path], max_tokens=100)[0].text.split() == ["Repeated", "text."] * 2
