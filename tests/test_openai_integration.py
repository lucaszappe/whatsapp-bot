import os

import pytest

from app.ai import call_openai


@pytest.mark.integration
def test_openai_live_response() -> None:
    """Calls the real OpenAI Responses API to verify end-to-end functionality."""
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("OPENAI_API_KEY not set.")

    question = "What is the capital of Brazil?"
    answer, input_tokens, output_tokens, response_id = call_openai(question)

    assert "Brasília" in answer or "Brazil" in answer
    assert input_tokens > 0
    assert output_tokens > 0
    assert response_id is not None
