import os, re, json, datetime
from pathlib import Path

OUT_DIR = Path(r"C:\jemai_hub\davesort")
OUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = OUT_DIR / "davesort_index.json"
MASTER_FILE = OUT_DIR / "davesort_masterlog.json"
index_log = []
master_log = []

# Sentiment: very basic! (upgradeable)
POSITIVE_WORDS = set("love yay happy good great fantastic excited awesome brilliant sweet wow nice amazing success win".split())
NEGATIVE_WORDS = set("fuck hate shit pissed off angry frustrated annoyed tired lazy bored broken no pointless sad regret".split())

def guess_sentiment(text):
    pos = sum(w in POSITIVE_WORDS for w in text.lower().split())
    neg = sum(w in NEGATIVE_WORDS for w in text.lower().split())
    if pos-neg > 2: return "very positive"
    if pos-neg > 0: return "positive"
    if neg-pos > 2: return "very negative"
    if neg-pos > 0: return "negative"
    return "neutral"

def extract_code_blocks(text):
    CODE_BLOCK_REGEX = re.compile(r"```(\w+)?\s*([\s\S]*?)```", re.MULTILINE)
    blocks = []
    for match in CODE_BLOCK_REGEX.finditer(text):
        lang = match.group(1) or "txt"
        code = match.group(2).strip()
        blocks.append( (lang, code) )
    return blocks

def safe_filename(dt, n, lang):
    dt_str = dt.strftime("%Y%m%d-%H%M")
    ext = ".py" if lang in ("python", "py") else ".txt"
    return f"{dt_str}-code-{n:04d}{ext}"

def process_chat_file(filepath):
    n_found = 0
    print(f"Processing: {filepath}")
    dt = datetime.datetime.now()
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    try:
        data = json.loads(content)
        if "conversations" in data:  # ChatGPT
            for conv in data["conversations"]:
                dt_conv = datetime.datetime.fromtimestamp(conv.get("create_time", dt.timestamp()))
                chat_title = conv.get("title", "Untitled")
                all_msgs = conv.get("mapping", {}).values() if "mapping" in conv else []
                session_words = 0
                code_blocks = 0
                moods = []
                for msg in all_msgs:
                    if not msg or "content" not in msg: continue
                    who = msg.get("author", "unknown")
                    msg_txt = msg["content"]
                    moods.append(guess_sentiment(msg_txt))
                    session_words += len(msg_txt.split())
                    blocks = extract_code_blocks(msg_txt)
                    for lang, code in blocks:
                        fn = safe_filename(dt_conv, n_found, lang)
                        path = OUT_DIR / fn
                        with open(path, "w", encoding="utf-8") as out:
                            out.write(code)
                        entry = {
                            "filename": str(path), "lang": lang, "source": str(filepath),
                            "session_title": chat_title, "dt": str(dt_conv),
                            "speaker": who, "sentiment": guess_sentiment(msg_txt),
                            "snippet": code[:80] + "..." if len(code)>80 else code
                        }
                        index_log.append(entry)
                        n_found += 1
                        code_blocks += 1
                master_log.append({
                    "chat_source": str(filepath),
                    "title": chat_title,
                    "start_time": str(dt_conv),
                    "total_words": session_words,
                    "total_code_blocks": code_blocks,
                    "moods": moods,
                    "avg_sentiment": max(set(moods), key=moods.count) if moods else "neutral",
                })
        elif "messages" in data:  # Vertex/Gemini
            msgs = data["messages"]
            chat_title = data.get("title","VertexChat")
            moods = []
            session_words = 0
            code_blocks = 0
            for m in msgs:
                dt_msg = dt
                if "create_time" in m:
                    dt_msg = datetime.datetime.fromtimestamp(float(m["create_time"]))
                author = m.get("author","unknown")
                content = m.get("content",{})
                msgtxt = ""
                # Gemini: content.parts is list of dicts with "text"
                if isinstance(content, dict) and "parts" in content:
                    for part in content["parts"]:
                        t = part.get("text","")
                        msgtxt += t + "\n"
                        moods.append(guess_sentiment(t))
                        session_words += len(t.split())
                        blocks = extract_code_blocks(t)
                        for lang, code in blocks:
                            fn = safe_filename(dt_msg, n_found, lang)
                            path = OUT_DIR / fn
                            with open(path, "w", encoding="utf-8") as out:
                                out.write(code)
                            entry = {
                                "filename": str(path), "lang": lang, "source": str(filepath),
                                "session_title": chat_title, "dt": str(dt_msg),
                                "speaker": author, "sentiment": guess_sentiment(t),
                                "snippet": code[:80] + "..." if len(code)>80 else code
                            }
                            index_log.append(entry)
                            n_found += 1
                            code_blocks += 1
            master_log.append({
                "chat_source": str(filepath),
                "title": chat_title,
                "total_words": session_words,
                "total_code_blocks": code_blocks,
                "moods": moods,
                "avg_sentiment": max(set(moods), key=moods.count) if moods else "neutral",
            })
        else:
            # Fallback: treat as plaintext
            moods = [guess_sentiment(content)]
            blocks = extract_code_blocks(content)
            for lang, code in blocks:
                fn = safe_filename(dt, n_found, lang)
                path = OUT_DIR / fn
                with open(path, "w", encoding="utf-8") as out:
                    out.write(code)
                entry = {
                    "filename": str(path), "lang": lang, "source": str(filepath),
                    "dt": str(dt), "speaker":"unknown",
                    "sentiment": guess_sentiment(code),
                    "snippet": code[:80]+"..." if len(code)>80 else code
                }
                index_log.append(entry)
                n_found += 1
            master_log.append({
                "chat_source": str(filepath),
                "title": "Unknown/PlainText",
                "total_words": len(content.split()),
                "total_code_blocks": n_found,
                "moods": moods,
                "avg_sentiment": max(set(moods), key=moods.count) if moods else "neutral",
            })
    except Exception as e:
        moods = [guess_sentiment(content)]
        blocks = extract_code_blocks(content)
        for lang, code in blocks:
            fn = safe_filename(dt, n_found, lang)
            path = OUT_DIR / fn
            with open(path, "w", encoding="utf-8") as out:
                out.write(code)
            entry = {
                "filename": str(path), "lang": lang, "source": str(filepath),
                "dt": str(dt), "speaker":"unknown",
                "sentiment": guess_sentiment(code),
                "snippet": code[:80]+"..." if len(code)>80 else code
            }
            index_log.append(entry)
            n_found += 1
        master_log.append({
            "chat_source": str(filepath),
            "title": "Unknown/PlainText",
            "total_words": len(content.split()),
            "total_code_blocks": n_found,
            "moods": moods,
            "avg_sentiment": max(set(moods), key=moods.count) if moods else "neutral",
        })
    print(f"  Found {n_found} code blocks.")

def main():
    # You can adjust or expand CHAT_DIRS
    CHAT_DIRS = [
        Path(r"C:\jemai_hub\chatgpt"),
        Path(r"C:\jemai_hub\vertex"),
        Path(r"C:\jemai_hub"),
    ]
    for chat_dir in CHAT_DIRS:
        if not chat_dir.exists(): continue
        for root, dirs, files in os.walk(chat_dir):
            for f in files:
                if f.endswith((".json", ".txt", ".md", ".html")):
                    process_chat_file(os.path.join(root, f))
    # Save the logs
    with open(INDEX_FILE, "w", encoding="utf-8") as idx:
        json.dump(index_log, idx, indent=2)
    with open(MASTER_FILE, "w", encoding="utf-8") as m:
        json.dump(master_log, m, indent=2)
    print(f"Done. Index: {INDEX_FILE}\nMaster: {MASTER_FILE}")

if __name__ == "__main__":
    main()
