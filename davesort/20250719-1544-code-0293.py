import os
import subprocess
import threading
import json
import time
import pyperclip
import psutil
import sys
# ADDED: send_from_directory for serving static files directly
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

# CONFIGURE FLASK APP to explicitly find templates/static and then pass to Flask-SocketIO
app = Flask(__name__,
            static_folder='templates',    # Flask will look in 'templates' relative to app root for static files if needed
            template_folder='templates')  # Flask will look in 'templates' relative to app root for templates
socketio = SocketIO(app)
clipboard_listener_thread = None
clipboard_listener_stop_event = threading.Event()

TRIGGER_PHRASE_RUN = "LT-RUN::"
TRIGGER_PHRASE_AI = "LT-AI::"
TRIGGER_PHRASE_ESPHOME = "LT-ESPHOME::"

def _run_command(command, job_id):
  """
  Run a command and emit output to the client.

  Args:
    command (str): The command to run.
    job_id (str): The ID of the job.
  """
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
    emit('output', {'output': line, 'job_id': job_id})
  process.stdout.close()
  return_code = process.wait()
  emit('output', {'output': f'\n--- Command finished with exit code {return_code} ---', 'job_id': job_id})

def _run_ollama(prompt, job_id):
  """
  Run Ollama and generate a command from the prompt.

  Args:
    prompt (str): The prompt to use.
    job_id (str): The ID of the job.
  """
  try:
    system_instruction = 'You are an expert in Linux shell commands. Your purpose is to translate the user\'s request into a single, executable shell command. Respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
    command = [
      "ollama",
      "run",
      "llama3:8b",
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
      emit('output', {'output': f'--- Generated command: {shell_command} ---\n', 'job_id': job_id})
      _run_command(shell_command, job_id)
    else:
      emit('output', {'output': 'Error: Could not generate command from prompt.', 'job_id': job_id})
  except Exception as e:
    emit('output', {'output': f'Error: {e}', 'job_id': job_id})

def _run_esphome(yaml_file, job_id):
  """
  Run ESPHome and compile/upload the YAML file.

  Args:
    yaml_file (str): The path to the YAML file.
    job_id (str): The ID of the job.
  """
  socketio.emit('output', {'output': f'--- Compiling and uploading {yaml_file} ---\n', 'job_id': job_id})
  try:
    command = ["esphome", "run", yaml_file]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    for line in iter(process.stdout.readline, ''):
      socketio.emit('output', {'output': line, 'job_id': job_id})
    process.stdout.close()
    return_code = process.wait()
    socketio.emit('output', {'output': f'\n--- ESPHome finished with exit code {return_code} ---', 'job_id': job_id})
  except Exception as e:
    socketio.emit('output', {'output': f'Error: {e}', 'job_id': job_id})

def _get_system_stats():
  """
  Get system stats.
  """
  cpu_usage = psutil.cpu_percent()
  memory_usage = psutil.virtual_memory().percent
  disk_usage = psutil.disk_usage('/').percent
  return {
    'cpu_usage': cpu_usage,
    'memory_usage': memory_usage,
    'disk_usage': disk_usage
  }

def _start_clipboard_listener():
  """
  Start the clipboard listener thread.
  """
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
         
        if current_clipboard_content.startswith(TRIGGER_PHRASE_RUN):
          command_to_send = current_clipboard_content[len(TRIGGER_PHRASE_RUN):].strip()
          job_id = str(time.time())
          threading.Thread(target=_run_command, args=(command_to_send, job_id)).start()
         
        elif current_clipboard_content.startswith(TRIGGER_PHRASE_AI):
          prompt = current_clipboard_content[len(TRIGGER_PHRASE_AI):].strip()
          job_id = str(time.time())
          threading.Thread(target=_run_ollama, args=(prompt, job_id)).start()

        elif current_clipboard_content.startswith(TRIGGER_PHRASE_ESPHOME):
          yaml_file = current_clipboard_content[len(TRIGGER_PHRASE_ESPHOME):].strip()
          job_id = str(time.time())
          threading.Thread(target=_run_esphome, args=(yaml_file, job_id)).start()

      time.sleep(1) 

    except pyperclip.PyperclipException as e:
      print(f"--- Pyperclip error: {e} ---")
      print("--- Clipboard listener stopped. ---")
      break
    except Exception as e:
      print(f"--- An unexpected error occurred: {e}", file=sys.stderr)
      time.sleep(2)

# MODIFIED: Use send_from_directory to serve index.html statically and explicitly
@app.route('/')
def index():
  # Serve index.html directly from the /app/templates mapping location
  # This explicitly bypasses Jinja2 templating, ensuring the full file is sent.
  return send_from_directory('/app/templates', 'index.html') 

@socketio.on('request_jobs_list') # ADDED: route to handle job list requests
def request_jobs_list():
  """
  Sends the current list of jobs to the client. (Assuming 'jobs' is managed globally)
  """
  # Need 'jobs' to be a global structure or accessed from context
  # For now, let's establish a basic global 'jobs' if not already done.
  # In a real app, this would be a more robust state management.
  global jobs # This needs to refer to the 'jobs = {}' at top if it becomes global
  emit('jobs_list_update', jobs) # 'Emit' needs to be imported or used via socketio.emit


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
  threading.Thread(target=_run_command, args=(command, job_id)).start()

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
  threading.Thread(target=_run_ollama, args=(prompt, job_id)).start()

@socketio.on('run_esphome')
def run_esphome(data):
  """
  Run ESPHome.

  Args:
    yaml_file (str): The YAML file to use, including job ID.
  """
  socketio.emit('output', {'output': f'--- Compiling and uploading {yaml_file} ---\n', 'job_id': job_id})
  try:
    command = ["esphome", "run", yaml_file]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    for line in iter(process.stdout.readline, ''):
      socketio.emit('output', {'output': line, 'job_id': job_id})
    process.stdout.close()
    return_code = process.wait()
    socketio.emit('output', {'output': f'\n--- ESPHome finished with exit code {return_code} ---', 'job_id': job_id})
  except Exception as e:
    socketio.emit('output', {'output': f'Error: {e}', 'job_id': job_id})

def _get_system_stats():
  """
  Get system stats.
  """
  cpu_usage = psutil.cpu_percent()
  memory_usage = psutil.virtual_memory().percent
  disk_usage = psutil.disk_usage('/').percent
  return {
    'cpu_usage': cpu_usage,
    'memory_usage': memory_usage,
    'disk_usage': disk_usage
  }

def _start_clipboard_listener():
  """
  Start the clipboard listener thread.
  """
  global clipboard_listener_thread
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    return

  clipboard_listener_stop_event.clear()
  clipboard_listener_thread = threading.Thread(target=_start_clipboard_listener)
  clipboard_listener_thread.daemon = True
  clipboard_listener_thread.start()

@socketio.on('request_jobs_list') # ADDED: route to handle job list requests
def request_jobs_list():
  """
  Sends the current list of jobs to the client. (Assuming 'jobs' is managed globally)
  """
  global jobs # This ensures we reference the global 'jobs' dictionary
  emit('jobs_list_update', jobs) # 'Emit' needs to be imported or used via socketio.emit


@socketio.on('stop_clipboard')
def stop_clipboard():
  """
  Stop the clipboard listener thread.
  """
  clipboard_listener_stop_event.set()

if __name__ == '__main__':
  socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)