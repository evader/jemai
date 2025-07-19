PYTHON_VERSION = "3.10" # Or "3.11", pick one that works for all libs
    # ...
    # Instead of sys.executable, explicitly use python 3.10 for the venv
    run_command(["python3.10", "-m", "venv", temp_venv_path])