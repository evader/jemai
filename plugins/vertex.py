import json
from pathlib import Path

def vertex_parser(filepath):
    # Accept any JSON file that looks like a Vertex/Gemini export
    # Skip if not JSON or doesn't have expected keys
    if not filepath.lower().endswith('.json'):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            return []
    # Heuristic: must have "messages" (list) and "model" key
    if not (isinstance(data, dict) and "messages" in data and isinstance(data["messages"], list)):
        return []
    title = data.get("title") or "Vertex Conversation"
    model = data.get("model", "")
    out = []
    messages = data["messages"]
    # Merge messages into conversation, preserving author and order
    conversation_text = []
    for m in messages:
        author = m.get("author", "")
        content_obj = m.get("content", {})
        # For multi-part content (usual for Gemini export)
        parts = []
        if isinstance(content_obj, dict):
            for part in content_obj.get("parts", []):
                if isinstance(part, dict):
                    t = part.get("text", "")
                    if t:
                        parts.append(t)
        msg_text = "\n".join(parts)
        if msg_text.strip():
            conversation_text.append(f"{author.upper()}: {msg_text.strip()}")
    # Single chunk for whole conversation
    if conversation_text:
        out.append({
            "source": "vertex",
            "title": title,
            "text": "\n\n".join(conversation_text),
            "date": "",  # No clear timestamp in this format, add if present
            "metadata": {
                "model": model,
                "filename": str(Path(filepath).name)
            }
        })
    return out

def register(register_parser):
    register_parser(vertex_parser)
