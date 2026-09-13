import openai

from app.config import settings

client = openai.OpenAI()

LLM_MODEL = "gpt-4o-mini"
SYS_INSTRUCTIONS = """
    Você é um assistente que ajuda produtores rurais com perguntas relacionadas à agricultura.
    - Se não houver arquivos relevantes, responda com base no conhecimento geral.
    - Se não souber a resposta, diga que não sabe.
    - Responda de forma sucinta e amigável.
    """


def call_openai(
    user_text: str,
    previous_response_id: str | None = None,
) -> tuple[str, int, int, str]:
    """Send user_text to OpenAI Responses API with vector-store retrieval.
    Returns: (output_text, input_tokens, output_tokens, response_id)
    """
    response = client.responses.create(
        model=LLM_MODEL,
        input=user_text,
        previous_response_id=previous_response_id,
        tools=[{"type": "file_search", "vector_store_ids": [settings.VECTOR_STORE_ID]}],
        instructions=SYS_INSTRUCTIONS,
    )
    usage = response.usage
    input_tokens = usage.input_tokens if usage else 0
    output_tokens = usage.output_tokens if usage else 0
    response_id = response.id
    return response.output_text, input_tokens, output_tokens, response_id
