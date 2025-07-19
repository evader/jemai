# lt.py - Local Lieutenant Core Script
# Version: 13.0 (Jemma Purge)
# Change: Removed all ESPHome/ESP32 code and dependencies.

#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import threading
import uuid
from flask import Flask, request, jsonify, render_template
import ollama 
import google.generativeai as genai

# --- Configuration ---
OLLAMA_MODEL_NAME = "llama3:8b"

# --- Lieutenant's Core ---
app = Flask(__name__) 
jobs = {} 

# --- Gemini (Nexus) API Configuration ---
try:
  genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
  # Note: The original code used gemini-2.0-flash here.
  # If you want to temporarily relax safety settings for testing (as discussed yesterday):
  NEXUS_MODEL = genai.GenerativeModel(
      'gemini-2.0-flash', # Or gemini-1.0-pro if that was your intended model. This was from your code.
      safety_settings = [ # Add this block if you want to relax safety
          {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
          {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
          {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
          {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
      ]
  )
  print("Nexus (Gemini) API configured successfully.")
except Exception as e:
  print(f"WARNING: Could not configure Nexus (Gemini) API. Is GOOGLE_API_KEY set? Error: {e}", file=sys.stderr)
  NEXUS_MODEL = None

# --- Helper Functions ---
def execute_shell_command_threaded(command, job_id, initial_prompt=""):
  """Runs shell commands in a background thread."""
  if not initial_prompt:
    initial_prompt = command
  jobs[job_id] = {"status": "running", "output": f"--- Executing: '{command}' ---\n", "command": initial_prompt}
  try:
    venv_path = os.path.join(os.path.expanduser("~"), "local_lieutenant_env", "bin")
    env = os.environ.copy()
    env["PATH"] = f"{venv_path}:{env['PATH']}"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, cwd=os.path.expanduser("~"), env=env)
    output_buffer = jobs[job_id]["output"]
    for line in iter(process.stdout.readline, ''):
      output_buffer += line
      jobs[job_id]["output"] = output_buffer
    rc = process.wait()
    jobs[job_id]["status"] = "complete" if rc == 0 else "error"
    jobs[job_id]["output"] += f"\n--- Result: {'SUCCESS' if rc == 0 else 'FAILED'} ---"
  except Exception as e:
    jobs[job_id]["status"] = "error"
    jobs[job_id]["output"] += f"\nPython Error: {e}"

def call_local_ai_and_execute_threaded(prompt, job_id):
  """Calls the local Ollama brain to get a command, then executes it."""
  jobs[job_id] = {"status": "thinking", "output": f"--- Lieutenant thinking locally about: '{prompt}' ---\n", "command": prompt}
  try:
    system_instruction = 'You are an expert in Linux shell commands. Your sole purpose is to translate the user\'s request into a single, executable shell command. You must respond with ONLY a JSON object in the format {"command": "shell_command_here"}. Do not provide any other text, explanations, or markdown formatting.'
    response = ollama.chat(model=OLLAMA_MODEL_NAME, messages=[{'role': 'system', 'content': system_instruction},{'role': 'user', 'content': prompt}], format='json')
    command_data = json.loads(response['message']['content'])
    if command_data.get("command"):
      shell_command = command_data["command"]
      jobs[job_id]["output"] += f"Local brain suggested command: '{shell_command}'\n"
      execute_shell_command_threaded(shell_command, job_id, initial_prompt=prompt)
    else:
      raise ValueError("Local AI did not return a valid command.")
  except Exception as e:
    jobs[job_id]["status"] = "error"
    jobs[job_id]["output"] += f"\nLocal AI Error: {e}"

def call_nexus_ai_and_execute_threaded(prompt, job_id):
  """Calls the online Nexus (Gemini) brain to get a command, then executes it."""
  jobs[job_id] = {"status": "thinking", "output": f"--- Contacting Nexus (Online) about: '{prompt}' ---\n", "command": prompt}
  if not NEXUS_MODEL:
    jobs[job_id]["status"] = "error"; jobs[job_id]["output"] += "Nexus API not configured."; return
  try:
    system_prompt = f"Based on the following user goal, provide a single, likely Linux shell command. Do not provide any explanation, only the raw command. Goal: '{prompt}'"
    response = NEXUS_MODEL.generate_content(system_prompt)
    shell_command = response.text.strip().replace('`', '')
    if shell_command:
      jobs[job_id]["output"] += f"Nexus suggested command: '{shell_command}'\n"
      execute_shell_command_threaded(shell_command, job_id, initial_prompt=prompt)
    else:
      raise ValueError("Nexus AI did not return a valid command.")
  except Exception as e:
    jobs[job_id]["status"] = "error"; jobs[job_id]["output"] += f"\nNexus AI Error: {e}"

# --- Flask Web Server Routes ---
@app.route("/")
def index():
  return render_template('index.html')

@app.route("/run", methods=['GET'])
def unified_run_endpoint():
  mode = request.args.get('mode', 'direct')
  command_or_prompt = request.args.get('command')
  job_id = str(uuid.uuid4())
  if not command_or_prompt: return jsonify({"status": "error", "output": "No command/prompt provided."}), 400

  if mode == 'local_ai':
    thread = threading.Thread(target=call_local_ai_and_execute_threaded, args=(command_or_prompt, job_id))
  elif mode == 'nexus_ai':
    thread = threading.Thread(target=call_nexus_ai_and_execute_threaded, args=(command_or_prompt, job_id))
  else: # 'direct' mode
    thread = threading.Thread(target=execute_shell_command_threaded, args=(command_or_prompt, job_id))

  thread.daemon = True
  thread.start()
  return jsonify({"status": "started", "job_id": job_id})

@app.route("/list_jobs", methods=['GET'])
def list_jobs_endpoint():
  """Returns all jobs for the dashboard UI."""
  return jsonify(jobs)

if __name__ == "__main__":
  print("--- Starting Local Lieutenant v13.0 (Server Only) ---")
  if not os.path.isdir('templates'):
    print("CRITICAL ERROR: 'templates' directory not found. Please create it and place index.html inside.", file=sys.stderr)
    sys.exit(1)
  app.run(host='0.0.0.0', port=5000)