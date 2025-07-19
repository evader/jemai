# In download_python_packages() function:

    # --- Ensure you have python3.10 (or 3.11) installed on your host system for this venv ---
    # Example: sudo apt install python3.10 python3.10-venv

    # Python interpreter for the temporary venv
    # We use a specific version like python3.10 as many packages might not yet support 3.12/3.13
    TEMP_VENV_PYTHON_EXE = "python3.10"  # <--- Make sure this Python version is callable on your system

    # Create a temporary venv to run pip download
    temp_venv_path = os.path.join(BASE_DOWNLOAD_DIR, "temp_venv_for_pip_download")
    
    # Explicitly use the chosen python executable for the venv
    run_command([TEMP_VENV_PYTHON_EXE, "-m", "venv", temp_venv_path])
    
    pip_executable = os.path.join(temp_venv_path, "bin", "pip")

    # ... rest of the download_python_packages() function remains the same ...