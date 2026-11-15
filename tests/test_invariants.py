import random

import pytest

from rustchunker import chunk


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
@pytest.mark.parametrize(
    "max_tokens,overlap",
    [(budget, overlap) for budget in (1, 2, 4, 8) for overlap in range(budget)],
)
def test_chunk_preserves_content_offsets_and_budget(strategy, max_tokens, overlap):
    rng = random.Random(42)
    pieces = [
        "Hello.", "Dr. Smith", "你好。", "再见！", "العربية",
        "café", "e\u0301", "🎉", " ", "\n", "\t", "\u00a0", "\u2003",
    ]
    texts = [
        "", " \n\t\u2003", "x" * 10000, "你好。世界。再见。 tail",
        "  Dr. Smith is here. Bye!  ",
    ]
    texts += ["".join(rng.choices(pieces, k=40)) for _ in range(50)]

    for text in texts:
        result = chunk(text, max_tokens=max_tokens, overlap=overlap, strategy=strategy)
        end = 0
        for index, c in enumerate(result):
            assert 0 <= c.start < c.end <= len(text)
            assert c.text == text[c.start : c.end]
            assert 0 < len(c.text.split()) <= max_tokens
            assert c.index == index
            assert c.metadata == {
                "source_file": None,
                "strategy_used": strategy,
                "total_chunks": len(result),
            }
            assert not text[end : c.start].strip(), "content lost between chunks"
            assert c.end > end, "chunk must advance through the document"
            if overlap == 0:
                assert c.start >= end, "content duplicated without overlap"
            end = c.end
        assert not text[end:].strip(), "trailing content lost"
