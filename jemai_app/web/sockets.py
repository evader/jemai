import re
import threading
import time
import os
import json
from .. import socketio
from ..config import SYSTEM_PROMPT, JEMAI_HUB
from ..core.rag import rag_search
from ..core.ai import call_llm
from ..core.tools import run_command
from ..core.voice import speak
from ..core.self_modification import write_file_content

@socketio.on('chat_message')
def handle_chat_message(data):
    messages = data.get("messages", [])
    model = data.get("model", "gpt-4o")
    if not messages: return

    last_user_message = messages[-1]['content']
    context = rag_search(last_user_message)
    if context:
        messages[-1]['content'] = f"CONTEXT:\n{context}\n\nQUERY: {last_user_message}"

    if messages[0]['role'] != 'system':
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    response_text = call_llm(messages, model=model)

    try:
        tool_match = json.loads(response_text)
        if tool_match.get("tool_to_use") == "write_file":
            params = tool_match.get("parameters", {})
            path = params.get("path")
            content = params.get("content")
            if path and content is not None:
                success, result_msg = write_file_content(path, content)
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"I executed the `write_file` tool. Result: {result_msg}"})
                final_response = call_llm(messages, model=model)
                socketio.emit('chat_response', {'resp': final_response})
                return
    except (json.JSONDecodeError, TypeError):
        pass

    shell_match = re.search(r"```shell\n([\s\S]*?)\n```", response_text)
    if shell_match:
        command_to_run = shell_match.group(1).strip()
        command_output = run_command(command_to_run)
        
        follow_up_messages = messages + [
            {"role": "assistant", "content": response_text},
            {"role": "user", "content": f"I executed that command. Here is the output:\n\n```\n{command_output}\n```\n\nPlease analyze this output and provide the final answer."}
        ]
        
        final_response = call_llm(follow_up_messages, model=model)
        socketio.emit('chat_response', {'resp': final_response})
        threading.Thread(target=speak, args=(final_response,)).start()
    else:
        socketio.emit('chat_response', {'resp': response_text})
        threading.Thread(target=speak, args=(response_text,)).start()

@socketio.on('request_log_stream')
def handle_log_stream_request():
    log_file_path = os.path.join(JEMAI_HUB, "jemai.log")
    
    def stream_log():
        if not os.path.exists(log_file_path):
            socketio.emit('log_update', {'data': "jemai.log does not exist yet."})
            return

        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    socketio.sleep(0.2) 
                    continue
                socketio.emit('log_update', {'data': line})

    socketio.start_background_task(stream_log)

DIRECTOR_SYSTEM_PROMPT = """You are JEMAI. You are receiving a high-priority directive from your core architect.
This is a meta-level command to guide your development.
Analyze the directive and formulate a plan to implement it using your self-modification tools.
Execute the plan immediately."""

@socketio.on('director_message')
def handle_director_message(data):
    directive = data.get("directive", "")
    if not directive:
        return

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": directive}
    ]
    
    # Use a specific model for this complex task
    response_text = call_llm(messages, model="gpt-4o")
    
    # The response from JEMAI will be handled by the main chat logic,
    # so we just emit it back as a standard chat response for the user to see.
    socketio.emit('chat_response', {'resp': response_text})
