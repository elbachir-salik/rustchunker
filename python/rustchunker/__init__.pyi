from os import PathLike
from typing import Literal, Union

class Chunk:
    """A single chunk of a document (produced by chunk()/chunk_files(), not
    constructible directly).

    start/end are character offsets into the input string for chunk(), or
    the extracted text for chunk_files(). They are not byte offsets, PDF
    page coordinates, or positions in the original markup/binary file.

    index is the chunk's position within its OWN source document (0-based).
    For chunk_files, the returned list concatenates every file's chunks, so
    index restarts at 0 per file and is not the position in the returned
    list -- disambiguate with metadata["source_file"].
    """

    text: str
    start: int
    end: int
    index: int
    # keys: source_file (str | None -- None for non-UTF-8 paths and for
    # chunk() on a raw string), total_chunks (int, within this file),
    # strategy_used (str)
    metadata: dict[str, str | int | None]

# NOTE ON "tokens": a token here is a whitespace-delimited word, NOT a model
# / BPE token (tiktoken, SentencePiece, ...). max_tokens caps the number of
# whitespace words per chunk. Word count is only an approximation of an
# embedding model's token budget (typically ~0.75x), so leave headroom if you
# are sizing chunks against a hard model limit.
#
# strategy: "fixed" (every N words, exact) or "sentence" (splits on real
# Unicode sentence boundaries, never exceeding max_tokens). Any other value
# raises ValueError.
def chunk(
    text: str,
    max_tokens: int,
    overlap: int = 0,
    strategy: Literal["fixed", "sentence"] = "fixed",
) -> list[Chunk]: ...

# paths accepts str or any os.PathLike (e.g. pathlib.Path).
# supported extensions: .txt, .md, .markdown, .html, .htm, .pdf, .docx.
# Text/markup files must be UTF-8 (a leading BOM is stripped automatically).
# PDF requires embedded text (no OCR); DOCX reads the main document body
# including tables. Legacy .doc is unsupported. No page metadata is returned.
#
# on_error controls what happens when a file can't be read or chunked
# (unsupported extension, I/O error, invalid UTF-8, extraction failure):
#   "raise" (default) -- the first failing file aborts the whole call
#                        (raises ValueError / OSError).
#   "skip"            -- failing files are omitted and the rest still return.
# A bad max_tokens/overlap/strategy always raises, even under "skip".
def chunk_files(
    paths: list[Union[str, PathLike[str]]],
    max_tokens: int,
    overlap: int = 0,
    strategy: Literal["fixed", "sentence"] = "fixed",
    on_error: Literal["raise", "skip"] = "raise",
) -> list[Chunk]: ...
