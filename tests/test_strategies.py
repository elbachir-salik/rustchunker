import pytest

from rustchunker import chunk


def test_sentence_strategy_respects_max_tokens():
    text = "Dr. Smith is here. He is a doctor. She agrees with him."
    result = chunk(text, max_tokens=6, strategy="sentence")
    for c in result:
        assert len(c.text.split()) <= 6
        assert text[c.start : c.end] == c.text


def test_sentence_strategy_keeps_abbreviation_attached():
    text = "Dr. Smith is here."
    result = chunk(text, max_tokens=100, strategy="sentence")
    assert len(result) == 1
    assert result[0].text == text


def test_sentence_strategy_handles_acronym():
    text = "I live in the U.S.A. It is nice."
    result = chunk(text, max_tokens=100, strategy="sentence")
    assert len(result) == 1
    assert result[0].text == text


def test_sentence_strategy_splits_multiple_sentences():
    text = "One sentence here. Another sentence here. A third one."
    result = chunk(text, max_tokens=3, strategy="sentence")
    assert len(result) > 1
    for c in result:
        assert len(c.text.split()) <= 3


def test_unknown_strategy_raises():
    with pytest.raises(NotImplementedError):
        chunk("some text", max_tokens=5, strategy="paragraph")
