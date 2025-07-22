import os
import logging
import subprocess

from ..config import PLUGINS_DIR

PLUGIN_FUNCS = {}

def register_plugin(name, func):
    logging.info(f"PLUGIN: Registering '{name}'")
    PLUGIN_FUNCS[name] = func

def load_plugins():
    for fn in os.listdir(PLUGINS_DIR):
        if fn.endswith('.py') and not fn.startswith('__'):
            try:
                filepath = os.path.join(PLUGINS_DIR, fn)
                module_name = fn[:-3]
                spec = __import__('importlib.util').util.spec_from_file_location(module_name, filepath)
                module = __import__('importlib.util').util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'register'):
                    module.register(register_plugin)
            except Exception as e:
                logging.error(f"PLUGIN: Failed to load {fn}: {e}")

def run_command(command):
    logging.info(f"CMD: Executing '{command}'")
    try:
        result = subprocess.run(command, capture_output=True, shell=True, text=True, timeout=300, encoding='utf-8', errors='ignore')
        output = (result.stdout or "") + ("\n" + (result.stderr or "") if result.stderr else "")
        logging.info(f"CMD: Output: {output[:100].strip()}...")
        return output.strip()
    except Exception as e:
        logging.error(f"CMD: Error executing '{command}': {e}")
        return f"Error: {e}"
