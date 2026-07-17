from os import PathLike
from typing import Union

class Chunk:
    """A single chunk of a document (produced by chunk()/chunk_files(), not
    constructible directly).

    start/end are character offsets into the source document, so
    ``source[chunk.start:chunk.end] == chunk.text`` holds even for non-ASCII
    text.

    index is the chunk's position within its OWN source document (0-based).
    For chunk_files, the returned list concatenates every file's chunks, so
    index restarts at 0 per file and is not the position in the returned
    list -- disambiguate with metadata["source_file"].
    """

    text: str
    start: int
    end: int
    index: int
    # keys: source_file (str|None), page_number (None for now),
    # total_chunks (int, within this file), strategy_used (str)
    metadata: dict[str, str | int | None]

# strategy: one of "fixed", "sentence" (others raise NotImplementedError)
def chunk(
    text: str,
    max_tokens: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[Chunk]: ...

# paths accepts str or any os.PathLike (e.g. pathlib.Path).
# supported extensions: .txt, .md, .markdown, .html, .htm (others raise ValueError)
def chunk_files(
    paths: list[Union[str, PathLike[str]]],
    max_tokens: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[Chunk]: ...
