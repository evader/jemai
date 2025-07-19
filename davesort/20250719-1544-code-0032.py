try:
  genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
  NEXUS_MODEL = genai.GenerativeModel('gemini-2.0-flash')
  print("Nexus (Gemini) API configured successfully.")
except Exception as e:
  print(f"WARNING: Could not configure Nexus (Gemini) API. Is GOOGLE_API_KEY set? Error: {e}", file=sys.stderr)
  NEXUS_MODEL = None