def call_nexus_ai_and_execute_threaded(prompt, job_id):
  # ... (initial status update)
  if not NEXUS_MODEL:
    jobs[job_id]["status"] = "error"; jobs[job_id]["output"] += "Nexus API not configured."; return
  try:
    system_prompt = f"Based on the following user goal, provide a single, likely Linux shell command. Do not provide any explanation, only the raw command. Goal: '{prompt}'"
    response = NEXUS_MODEL.generate_content(system_prompt)
    shell_command = response.text.strip().replace('`', '')
    if shell_command:
      # ... (execute command)
    else:
      raise ValueError("Nexus AI did not return a valid command.")
  except Exception as e:
    jobs[job_id]["status"] = "error"; jobs[job_id]["output"] += f"\\nNexus AI Error: {e}"