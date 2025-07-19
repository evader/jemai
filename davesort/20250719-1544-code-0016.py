import sys
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# --- Configuration (Use your project details) ---
PROJECT_ID = \"vertex-465223\"
# LOCATION can be 'global' for models like Gemini Flash,
# or a specific region like 'us-central1' if required by other models/features.
# Your Node.js code used 'global', so we'll stick to that.
LOCATION = \"global\"
MODEL_NAME = \"gemini-2.5-flash\"

# --- Initialize Vertex AI ---
vertexai.init(project=PROJECT_ID, location=LOCATION)

# --- Select the model ---
model = GenerativeModel(MODEL_NAME)

# --- Get the message from command line arguments ---
# Usage: python ask.py \"Your message here\"
# If no argument is provided, it will use a default message.
if len(sys.argv) > 1:
  user_message = sys.argv[1]
else:
  user_message = \"Hello, AI! Please introduce yourself.\" # Default message

# --- Send the message and get a response ---
try:
  print(f\"Sending message: '{user_message}'\")
  response = model.generate_content(user_message)

  # Print the model's response
  if response.text:
    print(\"\
AI Response:\")
    print(response.text)
  else:
    print(\"\
AI Response: (No text content received)\")
    print(response) # Print raw response for debugging if no text
except Exception as e:
  print(f\"\
An error occurred: {e}\")
  # Google API errors often have more details in the error object:
  if hasattr(e, 'response') and hasattr(e.response, 'text'):
    print(f\"API Error Details: {e.response.text()}\")