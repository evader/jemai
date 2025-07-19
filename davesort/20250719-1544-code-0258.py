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
from flask_socketio import SocketIO # Removed 'emit' as it's used via socketio.emit
from werkzeug.serving import run_simple, WSGIRequestHandler


# Global 'jobs' dictionary and SocketIO manager:
# This needs to be defined BEFORE 'app' and any route decorators
jobs = {} # Define the global jobs dictionary - CRITICAL FIX

# CONFIGURE FLASK APP to explicitly find templates/static and then pass to Flask-SocketIO
# Using the correct template_folder and static_folder relative to the app's root
app = Flask(__name__,
            static_folder='static',    # Flask will look in 'static' subfolder for static files
            template_folder='templates')  # Flask will look in 'templates' subfolder for templates
socketio = SocketIO(app)

clipboard_listener_thread = None
clipboard_listener_stop_event = threading.Event()

TRIGGER_PHRASE_RUN = "LT-RUN::"
TRIGGER_PHRASE_AI = "LT-AI::"
TRIGGER_PHRASE_ESPHOME = "LT-ESPHOME::"

# --- Helper to emit from threads ---
# This is crucial for fixing 'RuntimeError: Working outside of request context'
# It ensures emits from background threads use the correct SocketIO context
def _background_emit(event, data, sid):
    # Use socketio.run_with_context to ensure Flask/SocketIO context is available
    if sid:
        socketio.emit(event, data, room=sid)
    else:
        # Fallback for general system messages if no specific SID (e.g., from clipboard listener)
        socketio.emit(event, data)


def _run_command(command, job_id, sid): # sid added
  """
  Run a command and emit output to the client.
  """
  jobs[job_id] = {"status": "running", "output": f"--- Lieutenant executing: '{command}' ---\n", "command": command}
  try:
    process = subprocess.Popen(
      command,
      shell=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
      universal_newlines=True
    )
    output_buffer = ""
    for line in iter(process.stdout.readline, ''):
      output_buffer += line
      _background_emit('output', {'output': line, 'job_id': job_id}, sid) # Use _background_emit
     
    return_code = process.wait()
     
    if return_code == 0:
      output_buffer += "\n--- Lieutenant reports: Command SUCCESS ---"
      jobs[job_id]["status"] = "complete"
    else:
      output_buffer += f"\n--- Lieutenant reports: Command FAILED with return code {return_code} ---"
      jobs[job_id]["status"] = "error"

  except Exception as e:
    output_buffer += f"\nPython Error executing command: {e}"
    jobs[job_id]["status"] = "error"

  _background_emit('output', {'output': output_buffer, 'job_id': job_id}, sid) # Final emit of full output


def _run_ollama(prompt, job_id, sid): # sid added
  """
  Run Ollama and generate a command from the prompt.
  """
  try:
    system_instruction = 'You are an expert in Linux shell commands. Your purpose is to translate the user\'s request into a single, executable shell command. Respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
    command_ollama = [ # Renamed 'command' to 'command_ollama' to avoid conflict
      "ollama",
      "run",
      "llama3:8b",
      "--format",
      "json",
      system_instruction,
      prompt
    ]
    process = subprocess.Popen(command_ollama, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    output, _ = process.communicate()
    command_data = json.loads(output)
    shell_command = command_data.get("command")
    if shell_command:
      _background_emit('output', {'output': f'--- Generated command: {shell_command} ---\n', 'job_id': job_id}, sid) # Use _background_emit
      _run_command(shell_command, job_id, sid) # Also pass sid here
    else:
      _background_emit('output', {'output': 'Error: Could not generate command from prompt.', 'job_id': job_id}, sid) # Use _background_emit
  except Exception as e:
    _background_emit('output', {'output': f'Error: {e}', 'job_id': job_id}, sid) # Use _background_emit


def _run_esphome(yaml_file, job_id, sid): # sid added
  """
  Run ESPHome and compile/upload the YAML file.
  """
  _background_emit('output', {'output': f'--- Compiling and uploading {yaml_file} ---\n', 'job_id': job_id}, sid) # Use _background_emit
  try:
    command_esphome = ["esphome", "run", yaml_file] # Renamed 'command' to 'command_esphome'
    process = subprocess.Popen(command_esphome, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    for line in iter(process.stdout.readline, ''):
      _background_emit('output', {'output': line, 'job_id': job_id}, sid) # Use _background_emit
    process.stdout.close()
    return_code = process.wait()
    _background_emit('output', {'output': f'\n--- ESPHome finished with exit code {return_code} ---', 'job_id': job_id}, sid) # Use _background_emit
  except Exception as e:
    _background_emit('output', {'output': f'Error: {e}', 'job_id': job_id}, sid) # Use _background_emit


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

def _start_clipboard_listener(sio_instance, client_sid_arg): # s_io_instance added, client_sid_arg added
  """
  Start the clipboard listener thread.
  """
  # This function runs in a separate thread. `pyperclip` needs a display.
  # If a display is not available, we should gracefully exit this thread.
  
  if "DISPLAY" not in os.environ and not sys.stdout.isatty():
    sio_instance.emit('output', {'output': "--- No X server display for clipboard listener. Thread not started. ---", 'job_id': 'system'}, room=client_sid_arg)
    return

  sio_instance.emit('output', {'output': "--- Clipboard Listener Started ---", 'job_id': 'system'}, room=client_sid_arg)
  sio_instance.emit('output', {'output': f"Monitoring for '{TRIGGER_PHRASE_RUN}', '{TRIGGER_PHRASE_AI}', and '{TRIGGER_PHRASE_ESPHOME}'...", 'job_id': 'system'}, room=client_sid_arg)
   
  last_clipboard_content = ""
   
  while not clipboard_listener_stop_event.is_set():
    try:
      current_clipboard_content = pyperclip.paste()

      if current_clipboard_content != last_clipboard_content:
        last_clipboard_content = current_clipboard_content
         
        if current_clipboard_content.startswith(TRIGGER_PHRASE_RUN):
          command_to_send = current_clipboard_content[len(TRIGGER_PHRASE_RUN):].strip()
          job_id = str(time.time())
          # Pass client_sid_arg to _run_command so output goes back to originating client
          threading.Thread(target=_run_command, args=(command_to_send, job_id, client_sid_arg)).start()
         
        elif current_clipboard_content.startswith(TRIGGER_PHRASE_AI):
          prompt = current_clipboard_content[len(TRIGGER_PHRASE_AI):].strip()
          job_id = str(time.time())
          # Pass client_sid_arg to _run_ollama
          threading.Thread(target=_run_ollama, args=(prompt, job_id, client_sid_arg)).start()

        elif current_clipboard_content.startswith(TRIGGER_PHRASE_ESPHOME):
          yaml_file = current_clipboard_content[len(TRIGGER_PHRASE_ESPHOME):].strip()
          job_id = str(time.time())
          # Pass client_sid_arg to _run_esphome
          threading.Thread(target=_run_esphome, args=(yaml_file, job_id, client_sid_arg)).start()

      time.sleep(1) 

    except pyperclip.PyperclipException as e:
      sio_instance.emit('output', {'output': f"--- Pyperclip error: {e}. Clipboard listener stopped. ---", 'job_id': 'system'}, room=client_sid_arg)
      clipboard_listener_stop_event.set() # Ensure thread actually stops
    except Exception as e:
      sio_instance.emit('output', {'output': f"--- An unexpected error occurred in the listener loop: {e}. Thread will continue. ---", 'job_id': 'system'}, room=client_sid_arg)
      time.sleep(2) # Short delay to prevent rapid error looping

# --- Flask Web Server Routes ---
@app.route('/')
def index():
  # Serve index.html directly from the /app/templates mapping location
  # This explicitly bypasses Jinja2 templating, ensuring the full file is sent.
  return send_from_directory('templates', 'index.html') 

@socketio.on('execute')
def execute(data, sid): # sid added
  """
  Execute a command.
  """
  command = data.get('command')
  job_id = data.get('job_id')
  if not command:
    socketio.emit('output', {'output': 'Error: No command provided.', 'job_id': job_id}, room=sid)
    return
  threading.Thread(target=_run_command, args=(command, job_id, sid)).start() # sid passed

@socketio.on('generate_command')
def generate_command(data, sid): # sid added
  """
  Generate a command from a prompt.
  """
  prompt = data.get('prompt')
  job_id = data.get('job_id')
  if not prompt:
    socketio.emit('output', {'output': 'Error: No prompt provided.', 'job_id': job_id}, room=sid)
    return
  threading.Thread(target=_run_ollama, args=(prompt, job_id, sid)).start() # sid passed

@socketio.on('run_esphome')
def run_esphome(data, sid): # sid added
  """
  Run ESPHome.
  """
  yaml_file = data.get('yaml_file')
  job_id = data.get('job_id')
  if not yaml_file:
    socketio.emit('output', {'output': 'Error: No YAML file provided.', 'job_id': job_id}, room=sid)
    return
  threading.Thread(target=_run_esphome, args=(yaml_file, job_id, sid)).start() # sid passed

@socketio.on('request_jobs_list')
def request_jobs_list():
  """
  Sends the current list of jobs to the client.
  """
  # This function is called from the client, so Flask context is available,
  # but 'jobs' is a global dict managed by other threads.
  socketio.emit('jobs_list_update', jobs, room=request.sid) # Use request.sid for specific client

@socketio.on('get_system_stats')
def get_system_stats_socket(sid): # This will be called from a SocketIO event
  """
  Emits system stats periodically.
  """
  # Stats collection needs to be in a loop if continuously updated,
  # or just sent once on request. Assuming once on request for now.
  stats = _get_system_stats()
  socketio.emit('stats_update', stats, room=sid) # Emit to specific client


@socketio.on('start_clipboard')
def start_clipboard(data, sid): # sid added
  """
  Start the clipboard listener thread.
  Optional: Pass data to thread if needed.
  """
  global clipboard_listener_thread
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    socketio.emit('output', {'output': "--- Clipboard listener already running. ---", 'job_id': 'system'}, room=sid)
    return

  clipboard_listener_stop_event.clear()
  clipboard_listener_thread = threading.Thread(target=_start_clipboard_listener, args=(socketio, sid)) # Pass socketio instance and client sid
  clipboard_listener_thread.daemon = True
  clipboard_listener_thread.start()
  socketio.emit('output', {'output': "--- Attempting to start clipboard listener. Check Docker logs for display issues. ---", 'job_id': 'system'}, room=sid)


@socketio.on('stop_clipboard')
def stop_clipboard(data, sid): # sid added
  """
  Stop the clipboard listener thread.
  """
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    clipboard_listener_stop_event.set()
    socketio.emit('output', {'output': "--- Clipboard listener stop signal sent. ---", 'job_id': 'system'}, room=sid)
  else:
    socketio.emit('output', {'output': "--- Clipboard listener not running. ---", 'job_id': 'system'}, room=sid)


if __name__ == '__main__':
  # For production, use a WSGI server like Gunicorn + Gevent
  # socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True) # Old method
  # eventlet is recommended for Flask-SocketIO. Needs to be imported at top.
  try:
    import eventlet
    eventlet.monkey_patch()
  except ImportError:
    print("Eventlet not found, using Flask's default development server. Recommended to install eventlet for production.", file=sys.stderr)
  
  # For robust static file serving from within the Flask container, ensure 'static' folder exists
  # in '/app' if using `static_folder='static'` or '/app/templates' if `static_folder='templates'`
  # The Dockerfile already copies 'templates' into '/app/templates'
  
  socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True) # Development server