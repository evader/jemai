import os
import subprocess
import threading
import json
import time
import pyperclip
import psutil
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit # 'emit' can still be used locally within event handlers
from flask_socketio import ConnectionRefusedError # Import this for clipboard exception handling if needed

# MODIFIED: Define 'jobs' at a higher scope if it's meant to be truly global and modifiable
jobs = {} # This needs to be at the module level.
          # Functions that modify it should use 'global jobs'

# CONFIGURE FLASK APP to explicitly find templates/static and then pass to Flask-SocketIO
app = Flask(__name__,
            static_folder='templates',    # Flask will look in 'templates' relative to app root for static files if served by send_static_file
            template_folder='templates')  # Flask will look in 'templates' relative to app root for templates
socketio = SocketIO(app)
clipboard_listener_thread = None
clipboard_listener_stop_event = threading.Event()

TRIGGER_PHRASE_RUN = "LT-RUN::"
TRIGGER_PHRASE_AI = "LT-AI::"
TRIGGER_PHRASE_ESPHOME = "LT-ESPHOME::"

def _run_command(command, job_id, initial_prompt=""): # Added initial_prompt as it's passed here
    global jobs # ENSURE GLOBAL SCOPE CLARITY
    jobs[job_id]["status"] = "running" # Set status at start
    jobs[job_id]["command"] = initial_prompt # Store command
    jobs[job_id]["output"] += f"--- Executing: '{command}' ---\n" # Output this to jobs

    try:
        # Note: The original had venv_path. For Docker context, usually not needed unless venv is inside container specifically managed.
        # Assuming subprocess directly runs within container env.
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        for line in iter(process.stdout.readline, ''):
            jobs[job_id]["output"] += line # Update global 'jobs' dict
            socketio.emit('output', {'output': line, 'job_id': job_id}) # Emit line-by-line output
        process.stdout.close()
        return_code = process.wait()
        
        jobs[job_id]["status"] = "complete" if return_code == 0 else "error"
        jobs[job_id]["output"] += f"\n--- Command finished with exit code {return_code} ---"
        socketio.emit('output', {'output': f"\n--- Command finished with exit code {return_code} ---", 'job_id': job_id, 'final_status': jobs[job_id]["status"]})

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["output"] += f"\nPython Error: {e}"
        socketio.emit('output', {'output': f"\nPython Error: {e}", 'job_id': job_id, 'final_status': 'error'})

def _run_ollama(prompt, job_id):
    global jobs # ENSURE GLOBAL SCOPE CLARITY
    jobs[job_id]["status"] = "thinking" # Set status
    jobs[job_id]["output"] += f"--- Lieutenant thinking locally about: '{prompt}' ---\n"
    jobs[job_id]["command"] = prompt

    try:
        system_instruction = 'You are an expert in Linux shell commands. Your purpose is to translate the user\'s request into a single, executable shell command. Respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
        command = [
            "ollama",
            "run",
            "llama3:8b", # Consider making this configurable
            "--format",
            "json",
            system_instruction,
            prompt
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        output, _ = process.communicate()
        command_data = json.loads(output)
        shell_command = command_data.get("command")
        
        if shell_command:
            jobs[job_id]["output"] += f"Local brain suggested command: '{shell_command}'\n"
            socketio.emit('output', {'output': f"Local brain suggested command: '{shell_command}'\n", 'job_id': job_id})
            socketio.start_background_task(_run_command, shell_command, job_id, prompt) # Pass original prompt
        else:
            jobs[job_id]["output"] += 'Error: Could not generate command from prompt.'
            socketio.emit('output', {'output': 'Error: Could not generate command from prompt.', 'job_id': job_id, 'final_status': 'error'})
            jobs[job_id]["status"] = "error" # Mark job as error

    except Exception as e:
        jobs[job_id]["output"] += f'Error: {e}'
        socketio.emit('output', {'output': f'Error: {e}', 'job_id': job_id, 'final_status': 'error'})
        jobs[job_id]["status"] = "error" # Mark job as error

def _run_esphome(yaml_file, job_id):
    global jobs # ENSURE GLOBAL SCOPE CLARITY
    jobs[job_id]["status"] = "running" # Set status
    jobs[job_id]["output"] += f"--- Compiling and uploading {yaml_file} ---\n"
    jobs[job_id]["command"] = f"esphome run {yaml_file}" # Store command

    socketio.emit('output', {'output': f'--- Compiling and uploading {yaml_file} ---\n', 'job_id': job_id})
    try:
        command = ["esphome", "run", yaml_file]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in iter(process.stdout.readline, ''):
            jobs[job_id]["output"] += line
            socketio.emit('output', {'output': line, 'job_id': job_id})
        process.stdout.close()
        return_code = process.wait()
        
        jobs[job_id]["status"] = "complete" if return_code == 0 else "error"
        jobs[job_id]["output"] += f"\n--- ESPHome finished with exit code {return_code} ---"
        socketio.emit('output', {'output': f'\n--- ESPHome finished with exit code {return_code} ---', 'job_id': job_id, 'final_status': jobs[job_id]["status"]})

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["output"] += f'Error: {e}'
        socketio.emit('output', {'output': f'Error: {e}', 'job_id': job_id, 'final_status': 'error'})

def _get_system_stats():
    # No global jobs needed here unless it were to update a global stat.
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    return {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_usage': disk_usage
    }

def _start_clipboard_listener():
    global clipboard_listener_thread # ENSURE GLOBAL SCOPE CLARITY
    global clipboard_listener_stop_event # ENSURE GLOBAL SCOPE CLARITY
    global jobs # ENSURE GLOBAL SCOPE CLARITY

    if "DISPLAY" not in os.environ:
        print("--- No display found. Clipboard listener not started. ---")
        return

    print(f"--- Clipboard Listener Started ---")
    print(f"Monitoring for '{TRIGGER_PHRASE_RUN}', '{TRIGGER_PHRASE_AI}', and '{TRIGGER_PHRASE_ESPHOME}'...")
    
    last_clipboard_content = ""
    
    while not clipboard_listener_stop_event.is_set():
        try:
            current_clipboard_content = pyperclip.paste()

            if current_clipboard_content != last_clipboard_content:
                last_clipboard_content = current_clipboard_content
                job_id = str(time.time()) # New job ID for clipboard trigger
                jobs[job_id] = {"status": "triggered", "output": f"--- Clipboard Triggered: {current_clipboard_content} ---\n", "command": current_clipboard_content}
                socketio.emit('output', {'output': f"--- Clipboard Triggered: {current_clipboard_content} ---\n", 'job_id': job_id}) # Notify UI
                
                if current_clipboard_content.startswith(TRIGGER_PHRASE_RUN):
                    command_to_send = current_clipboard_content[len(TRIGGER_PHRASE_RUN):].strip()
                    jobs[job_id]["status"] = "running"
                    jobs[job_id]["output"] += f"Executing triggered command: {command_to_send}\n"
                    socketio.emit('output', {'output': f"Executing triggered command: {command_to_send}\n", 'job_id': job_id})
                    socketio.start_background_task(_run_command, command_to_send, job_id, command_to_send)
                
                elif current_clipboard_content.startswith(TRIGGER_PHRASE_AI):
                    prompt = current_clipboard_content[len(TRIGGER_PHRASE_AI):].strip()
                    socketio.start_background_task(_run_ollama, prompt, job_id)

                elif current_clipboard_content.startswith(TRIGGER_PHRASE_ESPHOME):
                    yaml_file = current_clipboard_content[len(TRIGGER_PHRASE_ESPHOME):].strip()
                    socketio.start_background_task(_run_esphome, yaml_file, job_id)

            time.sleep(1) # Poll clipboard every second

        except pyperclip.PyperclipException as e:
            print(f"--- Pyperclip error: {e} ---")
            print("--- Clipboard listener stopped. ---")
            break
        except ConnectionRefusedError: # Handle if client disconnects while emitting
            print("--- Socket.IO connection refused during clipboard emit. Client may have disconnected. ---")
            break # Exit clipboard listener gracefully
        except Exception as e:
            print(f"--- An unexpected error occurred in clipboard listener: {e}", file=sys.stderr)
            time.sleep(2)

# MODIFIED: Use send_from_directory to serve index.html statically and explicitly
@app.route('/')
def index():
    # Serve index.html directly from the /app/templates mapping location
    # This explicitly bypasses Jinja2 templating, ensuring the full file is sent.
    return send_from_directory('/app/templates', 'index.html') 

@socketio.on('request_jobs_list')
def request_jobs_list():
    global jobs # ENSURE GLOBAL SCOPE CLARITY
    emit('jobs_list_update', jobs) 

@app.route("/files/list", methods=['GET'])
def list_files():
  """
  List files in the workspace directory.

  Returns:
    A JSON response with a list of files.
  """
  workspace_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
  if not os.path.isdir(workspace_path):
    return jsonify({"error": "Workspace directory not found."}), 404

  items = []
  for item in os.listdir(workspace_path):
    item_path = os.path.join(workspace_path, item)
    items.append({
      "name": item,
      "is_dir": os.path.isdir(item_path)
    })
  return jsonify(items)

@app.route("/files/read", methods=['GET'])
def read_file():
  """
  Read a file from the workspace directory.

  Args:
    filename (str): The name of the file to read.

  Returns:
    A JSON response with the contents of the file.
  """
  filename = request.args.get('filename')
  if not filename:
    return jsonify({"error": "No filename provided."}), 400

  file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace", filename)
  if not os.path.isfile(file_path):
    return jsonify({"error": "File not found."}), 404

  with open(file_path, 'r') as f:
    content = f.read()
  return jsonify({"content": content})

@app.route("/files/write", methods=['POST'])
def write_file():
  """
  Write data to a file in the workspace directory.

  Args:
    data (dict): The data to write, including filename and content.

  Returns:
    A JSON response with the status of the operation.
  """
  data = request.get_json()
  filename = data.get('filename')
  content = data.get('content')
  if not filename or content is None:
    return jsonify({"error": "Missing filename or content."}), 400

  file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace", filename)
  with open(file_path, 'w') as f:
    f.write(content)
  return jsonify({"status": "success"})

@app.route("/files/create", methods=['POST'])
def create_file():
  """
  Create a new file in the workspace directory.

  Args:
    data (dict): The data to write, including filename.

  Returns:
    A JSON response with the status of the operation.
  """
  data = request.get_json()
  filename = data.get('filename')
  if not filename:
    return jsonify({"error": "No filename provided."}), 400

  file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace", filename)
  if os.path.exists(file_path):
    return jsonify({"error": "File already exists."}), 400

  with open(file_path, 'w') as f:
    f.write("")
  return jsonify({"status": "success"})

@app.route("/files/delete", methods=['POST'])
def delete_file():
  """
  Delete a file from the workspace directory.

  Args:
    data (dict): The filename to delete.

  Returns:
    A JSON response with the status of the operation.
  """
  data = request.get_json()
  filename = data.get('filename')
  if not filename:
    return jsonify({"error": "No filename provided."}), 400

  file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace", filename)
  if not os.path.isfile(file_path):
    return jsonify({"error": "File not found."}), 404

  os.remove(file_path)
  return jsonify({"status": "success"})

@socketio.on('execute')
def execute(data):
  """
  Execute a command.

  Args:
    data (dict): The command to execute, including job ID.
  """
  command = data.get('command')
  job_id = data.get('job_id')
  if not command:
    emit('output', {'output': 'Error: No command provided.', 'job_id': job_id})
    return
  socketio.start_background_task(_run_command, command, job_id, command) # Pass command as initial_prompt

@socketio.on('generate_command')
def generate_command(data):
  """
  Generate a command from a prompt.

  Args:
    data (dict): The prompt to use, including job ID.
  """
  prompt = data.get('prompt')
  job_id = data.get('job_id')
  if not prompt:
    emit('output', {'output': 'Error: No prompt provided.', 'job_id': job_id})
    return
  socketio.start_background_task(_run_ollama, prompt, job_id)

@socketio.on('run_esphome')
def run_esphome(data):
  """
  Run ESPHome.

  Args:
    yaml_file (str): The YAML file to use, including job ID.
  """
  yaml_file = data.get('yaml_file')
  job_id = data.get('job_id')
  if not yaml_file:
    emit('output', {'output': 'Error: No YAML file provided.', 'job_id': job_id})
    return
  socketio.start_background_task(_run_esphome, yaml_file, job_id)

@socketio.on('get_system_stats')
def get_system_stats():
  """
  Get system stats.
  """
  stats = _get_system_stats()
  socketio.emit('stats_update', stats)

@socketio.on('start_clipboard')
def start_clipboard():
  """
  Start the clipboard listener thread.
  """
  global clipboard_listener_thread
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    return

  clipboard_listener_stop_event.clear()
  socketio.start_background_task(_start_clipboard_listener) # MODIFIED: Use socketio.start_background_task

@socketio.on('stop_clipboard')
def stop_clipboard():
  """
  Stop the clipboard listener thread.
  """
  clipboard_listener_stop_event.set()


if __name__ == '__main__':
  # Removed the templates directory check as send_from_directory handles existence by raising 404.
  socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)