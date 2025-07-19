import sys
from google import genai
from google.generativeai import types # Updated import for common usage

# --- Configuration (Use your project details) ---
PROJECT_ID = "vertex-465223"
LOCATION = "global"  # Or "us-central1" if you prefer
MODEL_NAME = "gemini-2.5-flash"

# --- Initialize the client ---
# The 'vertexai=True' flag tells it to use the Vertex AI endpoint
# for Gemini models, allowing you to use your GCP project and credentials.
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

# Set up generation config
generation_config = types.GenerateContentConfig(
    max_output_tokens=65535,
    temperature=1,
    top_p=1,
    seed=0,
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    ],
    # thinking_config is specific to some advanced models/features and might not be
    # directly supported for all calls, or might be for specific internal uses.
    # It caused an issue in my testing of your code, so I'm commenting it out for a general example.
    # If the model errors without it, uncomment.
    # thinking_config=types.ThinkingConfig(thinking_budget=-1),
)

# --- Define the chat history (the context you want to provide) ---
# This recreates the conversation pieces you pasted.
# For a simple "ask.py" that takes NEW input, we'll just put the user's new message.
# If you want to replicate the *full history* like in your example code,
# you would uncomment and use ALL these 'msgX_textX' parts.
# For now, let's keep it simple for a single new query.

# In your example, you defined all these message parts.
# For a simple 'ask.py', we'll only provide the current user query.
# If you eventually want to create a chat with memory,
# you'd collect these history items dynamically.

# Get the message from command line arguments
if len(sys.argv) > 1:
    user_message_text = sys.argv[1]
else:
    user_message_text = "Hello, AI! Please introduce yourself, and confirm your name is Em." # Default message

# The 'contents' array will contain just the user's new message for simplicity
# This makes it a single-turn request.
contents = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message_text)]
    ),
]

# --- Send the message and get a streamed response ---
try:
    print(f"Sending message to {MODEL_NAME}: '{user_message_text}'\n")

    # The generate_content_stream method returns an iterator
    for chunk in client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=contents,
        config=generation_config,
    ):
        print(chunk.text, end="") # Print each chunk as it arrives
    print("\n") # New line after the streamed response finishes

except genai.types.APIError as e:
    print(f"\nAPI Error: {e.args[0]}")
    print(f"Error Code: {e.args[1].code}")
    print(f"Error Message: {e.args[1].message}")
    if e.args[1].details:
        print(f"Error Details: {e.args[1].details}")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")