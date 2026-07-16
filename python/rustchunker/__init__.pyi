class Chunk:
    text: str
    start: int
    end: int
    index: int

# strategy: one of "fixed", "sentence" (others raise NotImplementedError)
def chunk(
    text: str,
    max_tokens: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[Chunk]: ...
