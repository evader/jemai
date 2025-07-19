import os
import subprocess
import threading
import json
import time
import pyperclip
import psutil
import sys

# --- CRITICAL: Eventlet monkey patching MUST happen at the very top ---
# This ensures Flask-SocketIO and other patched modules work correctly in async environments.
try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    print("Eventlet not found, Flask-SocketIO might fall back to a less performant server. Recommended to install eventlet for production.", file=sys.stderr)

# Flask and SocketIO imports
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO 

# Global 'jobs' dictionary and SocketIO manager:
# This needs to be defined BEFORE 'app' and any route decorators for global access.
jobs = {} # Define the global jobs dictionary - CRITICAL FIX

# CONFIGURE FLASK APP
# Using correct template_folder and static_folder for Docker container context
app = Flask(__name__,
            static_folder='static',    # Flask will look for static files here (e.g., JS, CSS for index.html)
            template_folder='templates') # Flask will look here for templates (e.g., index.html)
# Flask-SocketIO initialization
socketio = SocketIO(app)

clipboard_listener_thread = None
clipboard_listener_stop_event = threading.Event()

# Define trigger phrases for clipboard monitoring
TRIGGER_PHRASE_RUN = "LT-RUN::"
TRIGGER_PHRASE_AI = "LT-AI::"
TRIGGER_PHRASE_ESPHOME = "LT-ESPHOME::"

# --- Helper to emit from threads ---
# This is crucial for fixing 'RuntimeError: Working outside of request context'
# It ensures emits from background threads use the correct SocketIO context by targeting a specific client SID.
def _background_emit(event, data, sid):
    if sid:
        socketio.emit(event, data, room=sid)
    else:
        # Fallback for general system messages if no specific SID (e.g., from system-generated events)
        # In this case, it will broadcast to all connected clients.
        socketio.emit(event, data)


# --- Core Command Execution ---
def _run_command(command, job_id, sid): # sid added for target client
  """
  Run a shell command and stream/emit output to the client.

  Args:
    command (str): The shell command to run.
    job_id (str): A unique ID for the job.
    sid (str): The SocketIO session ID of the client to send output to.
  """
  # Store job status, ensuring it's accessible globally
  jobs[job_id] = {"status": "running", "output": f"--- Lieutenant executing: '{command}' ---\n", "command": command}
  try:
    process = subprocess.Popen(
      command,
      shell=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, # Redirect stderr to stdout for combined output
      text=True, # Decode stdout/stderr as text (UTF-8 by default)
      bufsize=1, # Line-buffered output
      universal_newlines=True, # Ensure consistent newline characters
      cwd=os.path.expanduser("~") # Run commands from user's home directory
    )
    
    # Stream output line by line
    for line in iter(process.stdout.readline, ''):
      # Update global job output and emit to client
        jobs[job_id]["output"] += line
        _background_emit('output', {'output': line, 'job_id': job_id}, sid)
     
    # Wait for process to complete
    return_code = process.wait()
     
    # Update final status and emit completion message
    if return_code == 0:
      final_message = "\n--- Lieutenant reports: Command SUCCESS ---"
      jobs[job_id]["status"] = "complete"
    else:
      final_message = f"\n--- Lieutenant reports: Command FAILED with return code {return_code} ---"
      jobs[job_id]["status"] = "error"

    jobs[job_id]["output"] += final_message
    _background_emit('output', {'output': final_message, 'job_id': job_id}, sid) # Final emit of full output
    
  except Exception as e:
    # Handle Python-level errors during execution
    error_message = f"\nPython Error executing command: {e}"
    jobs[job_id]["output"] += error_message
    jobs[job_id]["status"] = "error"
    _background_emit('output', {'output': error_message, 'job_id': job_id}, sid)


# --- Ollama AI Integration ---
def _run_ollama(prompt, job_id, sid): # sid added
  """
  Interacts with Ollama to generate a shell command from a natural language prompt.

  Args:
    prompt (str): The natural language prompt for command generation.
    job_id (str): Unique job ID.
    sid (str): SocketIO session ID of the client.
  """
  try:
    system_instruction = 'You are an expert in Linux shell commands. Your purpose is to translate the user\'s request into a single, executable shell command. Respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
    
    # Command to call Ollama via subprocess
    command_ollama = [
      "ollama",
      "run",
      "llama3:8b", # Using Llama 3 8B as the default AI engine
      "--format",
      "json",
      system_instruction,
      prompt
    ]
    
    # Execute Ollama command
    process = subprocess.Popen(command_ollama, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    output, _ = process.communicate() # Wait for Ollama to finish
    
    # Parse Ollama's JSON output
    command_data = json.loads(output)
    shell_command = command_data.get("command") # Extract the command
    
    if shell_command:
      _background_emit('output', {'output': f'--- Generated command: {shell_command} ---\n', 'job_id': job_id}, sid)
      _run_command(shell_command, job_id, sid) # Execute the generated command, passing sid
    else:
      _background_emit('output', {'output': 'Error: Could not generate command from prompt.', 'job_id': job_id}, sid)
      
  except Exception as e:
    # Handle errors during Ollama interaction or JSON parsing
    _background_emit('output', {'output': f'Error generating command from AI: {e}', 'job_id': job_id}, sid)

# --- ESPHome Integration ---
def _run_esphome(yaml_file, job_id, sid): # sid added
  """
  Runs ESPHome to compile and upload firmware, emitting output.

  Args:
    yaml_file (str): Path to the ESPHome YAML configuration file.
    job_id (str): Unique job ID.
    sid (str): SocketIO session ID of the client.
  """
  _background_emit('output', {'output': f'--- Compiling and uploading {yaml_file} ---\n', 'job_id': job_id}, sid)
  try:
    command_esphome = ["esphome", "run", yaml_file] # Renamed 'command' to 'command_esphome'
    process = subprocess.Popen(command_esphome, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    
    for line in iter(process.stdout.readline, ''):
      _background_emit('output', {'output': line, 'job_id': job_id}, sid)
    
    return_code = process.wait()
    
    if return_code == 0:
        final_message = f'\n--- ESPHome finished with exit code {return_code} (SUCCESS) ---'
    else:
        final_message = f'\n--- ESPHome finished with exit code {return_code} (FAILED) ---'
    
    _background_emit('output', {'output': final_message, 'job_id': job_id}, sid)
    
  except Exception as e:
    _background_emit('output', {'output': f'Error running ESPHome: {e}', 'job_id': job_id}, sid)

# --- System Stats ---
def _get_system_stats():
  """
  Gets current system resource usage (CPU, memory, disk).
  """
  cpu_usage = psutil.cpu_percent()
  memory_usage = psutil.virtual_memory().percent
  disk_usage = psutil.disk_usage('/').percent
  return {
    'cpu_usage': cpu_usage,
    'memory_usage': memory_usage,
    'disk_usage': disk_usage
  }

# --- Clipboard Listener ---
def _start_clipboard_listener(sio_instance_arg, client_sid_arg): # sio_instance_arg for socketio.emit, client_sid_arg for target client
  """
  Monitors the system clipboard for specific trigger phrases to execute commands or AI prompts.
  This function runs in a separate thread. `pyperclip` needs a display/X server.
  """
  
  # Check for DISPLAY environment variable for X server access, and if it's not an interactive terminal
  if "DISPLAY" not in os.environ and not sys.stdout.isatty():
    sio_instance_arg.emit('output', {'output': "--- No X server display for clipboard listener. Thread not started. ---", 'job_id': 'system'}, room=client_sid_arg)
    return

  sio_instance_arg.emit('output', {'output': "--- Clipboard Listener Started ---", 'job_id': 'system'}, room=client_sid_arg)
  sio_instance_arg.emit('output', {'output': f"Monitoring for '{TRIGGER_PHRASE_RUN}', '{TRIGGER_PHRASE_AI}', and '{TRIGGER_PHRASE_ESPHOME}'...", 'job_id': 'system'}, room=client_sid_arg)
   
  last_clipboard_content = "" # Store last clipboard content to detect changes
   
  while not clipboard_listener_stop_event.is_set():
    try:
      current_clipboard_content = pyperclip.paste() # Access clipboard
      
      # If clipboard content has changed AND it's not empty, process it
      if current_clipboard_content != last_clipboard_content and current_clipboard_content.strip() != "":
        last_clipboard_content = current_clipboard_content # Update last content
        
        # Determine action based on trigger phrase
        if current_clipboard_content.startswith(TRIGGER_PHRASE_RUN):
          command_to_send = current_clipboard_content[len(TRIGGER_PHRASE_RUN):].strip()
          job_id = str(time.time()) # Unique job ID
          # Execute command in a new thread, passing client_sid_arg for output routing
          threading.Thread(target=_run_command, args=(command_to_send, job_id, client_sid_arg)).start()
         
        elif current_clipboard_content.startswith(TRIGGER_PHRASE_AI):
          prompt = current_clipboard_content[len(TRIGGER_PHRASE_AI):].strip()
          job_id = str(time.time())
          # Generate AI command in a new thread
          threading.Thread(target=_run_ollama, args=(prompt, job_id, client_sid_arg)).start()

        elif current_clipboard_content.startswith(TRIGGER_PHRASE_ESPHOME):
          yaml_file = current_clipboard_content[len(TRIGGER_PHRASE_ESPHOME):].strip()
          job_id = str(time.time())
          # Run ESPHome in a new thread
          threading.Thread(target=_run_esphome, args=(yaml_file, job_id, client_sid_arg)).start()

      time.sleep(1) # Check clipboard every second

    except pyperclip.PyperclipException as e:
      # Handle errors accessing clipboard (e.g., no display, clipboard manager not running)
      sio_instance_arg.emit('output', {'output': f"--- Pyperclip error: {e}. Clipboard listener stopping. ---", 'job_id': 'system'}, room=client_sid_arg)
      clipboard_listener_stop_event.set() # Stop the thread on Pyperclip errors
    except Exception as e:
      # Catch any other unexpected errors in the listener loop
      sio_instance_arg.emit('output', {'output': f"--- An unexpected error occurred in clipboard listener: {e}. ---", 'job_id': 'system'}, room=client_sid_arg)
      # Do not set stop_event here, allow it to try again
      time.sleep(2) # Short delay to prevent busy-looping on errors

# --- Flask Web Server Routes ---
@app.route('/')
def index():
  # Serve index.html directly from the /app/templates mapping location
  # This explicitly bypasses Jinja2 templating, ensuring the full file is sent.
  # Flask will look in the `templates` folder as configured by `template_folder='templates'` during app creation.
  return send_from_directory(app.template_folder, 'index.html') 

@socketio.on('execute')
def execute(data): # Deliberately keeping original signature to show extraction of sid
  """
  Execute a command based on client request.
  """
  sid = request.sid # Get session ID from client's request
  command = data.get('command')
  job_id = data.get('job_id')
  if not command:
    _background_emit('output', {'output': 'Error: No command provided.', 'job_id': job_id}, sid)
    return
  threading.Thread(target=_run_command, args=(command, job_id, sid)).start()

@socketio.on('generate_command')
def generate_command(data): # Deliberately keeping original signature to show extraction of sid
  """
  Generate a command from a prompt using AI.
  """
  sid = request.sid # Get session ID from client's request
  prompt = data.get('prompt')
  job_id = data.get('job_id')
  if not prompt:
    _background_emit('output', {'output': 'Error: No prompt provided.', 'job_id': job_id}, sid)
    return
  threading.Thread(target=_run_ollama, args=(prompt, job_id, sid)).start()

@socketio.on('run_esphome')
def run_esphome(data): # Deliberately keeping original signature to show extraction of sid
  """
  Run ESPHome compile/upload.
  """
  sid = request.sid # Get session ID from client's request
  yaml_file = data.get('yaml_file')
  job_id = data.get('job_id')
  if not yaml_file:
    _background_emit('output', {'output': 'Error: No YAML file provided.', 'job_id': job_id}, sid)
    return
  threading.Thread(target=_run_esphome, args=(yaml_file, job_id, sid)).start()

@socketio.on('request_jobs_list')
def request_jobs_list():
  """
  Sends the current list of jobs to the client.
  """
  # This function is called from the client, so Flask context is available,
  # but 'jobs' is a global dict managed by other threads.
  socketio.emit('jobs_list_update', jobs, room=request.sid) # Use request.sid for specific client

@socketio.on('get_system_stats')
def get_system_stats_socket(): # No 'data' or 'sid' needed if just directly calling _get_system_stats
  """
  Emits system stats periodically (if configured to be called by client).
  """
  stats = _get_system_stats()
  socketio.emit('stats_update', stats, room=request.sid) # Emit to specific client who requested

@socketio.on('start_clipboard')
def start_clipboard(data): # sid extracted from request, can't be passed from client for this
  """
  Start the clipboard listener thread.
  """
  sid = request.sid # Get session ID from the client who initiated this event
  global clipboard_listener_thread
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    _background_emit('output', {'output': "--- Clipboard listener already running. ---", 'job_id': 'system'}, sid)
    return

  clipboard_listener_stop_event.clear()
  # Pass the socketio instance and the original client's sid to the background thread
  clipboard_listener_thread = threading.Thread(target=_start_clipboard_listener, args=(socketio, sid))
  clipboard_listener_thread.daemon = True
  clipboard_listener_thread.start()
  _background_emit('output', {'output': "--- Attempting to start clipboard listener. Check Docker logs for display issues. ---", 'job_id': 'system'}, sid)


@socketio.on('stop_clipboard')
def stop_clipboard(data): # Deliberately keeping original signature to show extraction of sid
  """
  Stop the clipboard listener thread.
  """
  sid = request.sid # Get session ID from client's request
  if clipboard_listener_thread and clipboard_listener_thread.is_alive():
    clipboard_listener_stop_event.set()
    _background_emit('output', {'output': "--- Clipboard listener stop signal sent. ---", 'job_id': 'system'}, sid)
  else:
    _background_emit('output', {'output': "--- Clipboard listener not running. ---", 'job_id': 'system'}, sid)


if __name__ == '__main__':
  # For robust static file serving from within the Flask container (optional, but good practice if not using Nginx)
  # Ensure 'static' folder exists inside the 'templates' folder when copying web assets.
  os.makedirs(os.path.join(os.path.dirname(__file__), app.template_folder), exist_ok=True)
  
  # For production, use a WSGI server like Gunicorn + Gevent
  # eventlet is recommended for Flask-SocketIO.
  # It's patched at the top of the file.
  
  socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True) # Development server