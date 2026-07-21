from importlib.metadata import PackageNotFoundError, version

from ._rustchunker import Chunk, chunk, chunk_files

try:
    __version__ = version("rustchunker")
except PackageNotFoundError:  # not installed (e.g. running from a source tree)
    __version__ = "unknown"

__all__ = ["chunk", "chunk_files", "Chunk", "__version__"]
