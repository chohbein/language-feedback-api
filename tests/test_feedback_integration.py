"""Integration tests -- require OPENAI_API_KEY to be set.

Run with: pytest tests/test_feedback_integration.py -v

These tests make real API calls. Skip them in CI or when no key is available.
"""

import os

import pytest
from app.feedback import get_feedback
from app.models import FeedbackRequest

#   Load env for anthropic api key
from dotenv import load_dotenv
load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="API_KEY not set -- skipping integration tests",
)

VALID_ERROR_TYPES = {
    "grammar",
    "spelling",
    "word_choice",
    "punctuation",
    "word_order",
    "missing_word",
    "extra_word",
    "conjugation",
    "gender_agreement",
    "number_agreement",
    "tone_register",
    "other",
}
VALID_DIFFICULTIES = {"A1", "A2", "B1", "B2", "C1", "C2"}


@pytest.mark.asyncio
async def test_spanish_error():
    result = await get_feedback(
        FeedbackRequest(
            sentence="Yo soy fue al mercado ayer.",
            target_language="Spanish",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert len(result.errors) >= 1
    assert result.difficulty in VALID_DIFFICULTIES
    for error in result.errors:
        assert error.error_type in VALID_ERROR_TYPES
        assert len(error.explanation) > 0


@pytest.mark.asyncio
async def test_correct_german():
    result = await get_feedback(
        FeedbackRequest(
            sentence="Ich habe gestern einen interessanten Film gesehen.",
            target_language="German",
            native_language="English",
        )
    )
    assert result.is_correct is True
    assert result.errors == []
    assert result.difficulty in VALID_DIFFICULTIES


@pytest.mark.asyncio
async def test_french_gender_errors():
    result = await get_feedback(
        FeedbackRequest(
            sentence="La chat noir est sur le table.",
            target_language="French",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert len(result.errors) >= 1


@pytest.mark.asyncio
async def test_japanese_particle():
    result = await get_feedback(
        FeedbackRequest(
            sentence="私は東京を住んでいます。",
            target_language="Japanese",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert any("に" in e.correction for e in result.errors)


#========   Custom test cases covering edge cases   ========

#   General assertions for each test
#       These should pass in any situation.
def assert_valid_response(result):
    assert result.difficulty in VALID_DIFFICULTIES
    assert len(result.corrected_sentence) > 0
    for error in result.errors:
        assert error.error_type in VALID_ERROR_TYPES
        assert len(error.explanation) > 0

#   Multiple errors detection
#       - Tests detection of multiple errors in a phrase
@pytest.mark.asyncio
async def test_russian_multierr():
    result = await get_feedback(
        FeedbackRequest(
            sentence="Я очень хочет купить новый машину вчера в магазин.",
            target_language="Russian",
            native_language="English",
        )
    )
    assert_valid_response(result)
    assert result.is_correct is False
    assert len(result.errors) >= 4  #   Test that all 4 intended errors are found


#   High difficulty identification on Arabic (non-latin)
#       - Tests that correct sentences return no errors
#       - Tests accurate difficulty rating on complex sentences, despite it's short length.
@pytest.mark.asyncio
async def test_arabic_difficult():
    result = await get_feedback(
        FeedbackRequest(
            sentence="لو كنتُ قد درستُ أكثر، لنجحتُ.",
            target_language="Arabic",
            native_language="English",
        )
    )
    assert_valid_response(result)
    assert result.is_correct is True
    assert result.errors == []
    assert result.difficulty in {"B2","C1","C2"}    # Ensure we capture difficult nature, should be higher on the scale.


#   Low difficulty identification
#       - Tests accurate difficulty on simple sentences, despite a long length.
@pytest.mark.asyncio
async def test_low_diff():
    result = await get_feedback(
        FeedbackRequest(
            sentence="Me llamo Cristian y tengo veinte años. Vivo en Nueva York con mi familia.",
            target_language="Spanish",
            native_language="English",
        )
    )
    assert_valid_response(result)
    assert result.is_correct is True
    assert result.errors == []
    assert result.difficulty == "A1"    #   Is it correctly identified as simple


#   Specific error_type detection
#       - Tests if the model correctly classifies error as "missing_word" 
@pytest.mark.asyncio
async def test_missing_word():
    result = await get_feedback(
        FeedbackRequest(
            sentence="我昨天去了图书馆借了一些很有用书。",
            target_language="Chinese",
            native_language="English",
        )
    )
    assert_valid_response(result)
    assert result.is_correct is False
    assert any(e.error_type == "missing_word" for e in result.errors)   #   Asserts that "missing_word" is a recognized error


#   Specificity of error
#       - Tests the model's rule #8. Can we identify the specific point of error and exclude fluff.
@pytest.mark.asyncio
async def test_error_specificity():
    result = await get_feedback(
        FeedbackRequest(
            sentence="Je suis allé au marché hier et j'ai acheté des légume frais.",
            target_language="French",
            native_language="English",
        )
    )
    assert_valid_response(result)
    #   Ensure the model only returns AT MOST 2 words ("des légume") as erroneous.
    assert all(len(e.original.split()) <= 2 for e in result.errors)
    