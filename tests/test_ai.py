from app.ai import call_openai


def test_call_openai_mocks(mocker: object) -> None:
    """Mock OpenAI so we don't spend tokens in CI."""
    mocked = mocker.patch("app.ai.client.responses.create")
    mocked.return_value = type(
        "FakeResponse",
        (),
        {
            "output_text": "Hello!",
            "usage": type("U", (), {"input_tokens": 5, "output_tokens": 7}),
            "id": "resp_Y",
        },
    )()

    txt, input_tokens, output_tokens, response_id = call_openai("Hi?")
    assert txt == "Hello!"
    assert (input_tokens, output_tokens) == (5, 7)
    assert response_id == "resp_Y"
    mocked.assert_called_once()
