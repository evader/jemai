# Cleanup temporary venv
    print("Cleaning up temporary pip download environment...")
    run_command(["rm", "-rf", temp_venv_path]) # <--- THIS IS THE CULPRIT!
    print("Finished downloading Python packages.")