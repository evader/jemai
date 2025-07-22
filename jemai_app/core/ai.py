import logging
import openai
from ..config import OPENAI_API_KEY, SYSTEM_PROMPT

# Check for OpenAI library during import
try:
    import openai
    HAS_OPENAI = True
    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-...":
        openai.api_key = OPENAI_API_KEY
    else:
        logging.warning("OpenAI API key not found in .env file.")
        HAS_OPENAI = False
except ImportError:
    HAS_OPENAI = False

def call_llm(messages, model="gpt-4o"):
    if not HAS_OPENAI:
        return "OpenAI library not installed or API key not configured."

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        logging.info(f"LLM: Calling {model} with {len(messages)} messages.")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048
        )
        response_text = completion.choices[0].message.content
        logging.info("LLM: Received response.")
        return response_text
    except Exception as e:
        logging.error(f"LLM: API call failed: {e}")
        return f"Error connecting to OpenAI: {e}"
