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


def test_sentence_strategy_keeps_abbreviation_attached_with_small_budget():
    # max_tokens=100 above is generous enough that greedy packing would glue
    # everything into one chunk regardless of whether "Dr." is actually
    # merged with the following sentence at the boundary-detection level --
    # that test alone wouldn't have caught a real bug where "Dr." was
    # produced as its own isolated 1-token "sentence". max_tokens=2 is just
    # enough to hold "Dr." + "Smith" together but not the whole sentence, so
    # it exercises the oversized-sentence fallback on the correctly-merged
    # span instead of masking the issue.
    text = "Dr. Smith is here."
    result = chunk(text, max_tokens=2, strategy="sentence")
    assert result[0].text.startswith("Dr. Smith")


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
