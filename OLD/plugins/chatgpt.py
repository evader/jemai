import json
def chatgpt_parser(filepath):
    if not filepath.endswith("conversations.json"):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    conversations = []
    for conv in data.get("conversations", []):
        title = conv.get("title") or "ChatGPT Conversation"
        messages = [msg.get("content", "") for msg in conv.get("mapping", {}).values() if msg.get("content")]
        whole = "\n\n".join(messages)
        conversations.append({
            "source": "chatgpt",
            "title": title,
            "text": whole,
            "date": conv.get("create_time") or "",
            "metadata": {"id": conv.get("id")}
        })
    return conversations

def register(register_parser):
    register_parser(chatgpt_parser)
