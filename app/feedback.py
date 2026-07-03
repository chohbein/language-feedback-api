"""System prompt and LLM interaction for language feedback."""

import json
from pathlib import Path

import anthropic

from app.models import FeedbackRequest, FeedbackResponse

cache={}  # In-memory caching. Resets on server restart. Redis for production?

SYSTEM_PROMPT = """\
You are a language-learning assistant. A student is practicing writing in their \
target language. Your job is to analyze their sentence, find errors, and provide \
helpful feedback.

RULES:
1. If the sentence is already correct, return is_correct=true, an empty errors \
array, and set corrected_sentence to the original sentence exactly.
2. For each error, identify the original text, provide the correction, classify \
the error type, and explain the error in the learner's NATIVE language so they \
can understand.
3. Error types must be one of: grammar, spelling, word_choice, punctuation, \
word_order, missing_word, extra_word, conjugation, gender_agreement, \
number_agreement, tone_register, other.
4. Assign a CEFR difficulty level (A1–C2) based on the complexity of the \
sentence (vocabulary, grammar structures used), NOT based on whether it has errors.
5. The corrected_sentence should be the minimal correction -- preserve the \
learner's original meaning and style as much as possible.
6. Explanations should be concise (1–2 sentences), friendly, and educational.
7. When the sentence has many errors and the intended meaning is unclear, \
make reasonable assumptions about what the learner meant and state your assumption in the explanation.
8. Each error should identify the most specific span of text that contains the issue. \
Avoid flagging the entire sentence as an error unless the problem truly affects the whole sentence.

Respond with valid JSON matching this exact schema:
{
  "corrected_sentence": "string",
  "is_correct": boolean,
  "errors": [
    {
      "original": "string",
      "correction": "string",
      "error_type": "string",
      "explanation": "string (in native language)"
    }
  ],
  "difficulty": "A1|A2|B1|B2|C1|C2"
}
"""

def load_tool_schema():
    raw = json.loads(Path("schema/response.schema.json").read_text())
    return {k: v for k, v in raw.items() if k not in ("$schema", "title", "description")}

FEEDBACK_TOOL = {
      "name": "submit_feedback",
      "description": "Submit structured language feedback for the learner's sentence.",
      "input_schema": load_tool_schema()
    }

async def get_feedback(request: FeedbackRequest) -> FeedbackResponse:
    client = anthropic.AsyncAnthropic()

    # Return cached result if available
    cache_key = f"{request.sentence}:{request.target_language}:{request.native_language}"
    if cache_key in cache:
        return cache[cache_key]
    
    user_message = (
        f"Target language: {request.target_language}\n"
        f"Native language: {request.native_language}\n"
        f"Sentence: {request.sentence}"
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[FEEDBACK_TOOL],
        tool_choice={"type": "tool", "name": "submit_feedback"},
        messages=[
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")

    result = FeedbackResponse(**tool_block.input)
    cache[cache_key] = result

    return result
