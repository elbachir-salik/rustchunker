class Chunk:
    text: str
    start: int
    end: int
    index: int
    metadata: dict[str, str | int | None]

# strategy: one of "fixed", "sentence" (others raise NotImplementedError)
def chunk(
    text: str,
    max_tokens: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[Chunk]: ...

# supported extensions: .txt, .md, .html (others raise ValueError)
def chunk_files(
    paths: list[str],
    max_tokens: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[Chunk]: ...
