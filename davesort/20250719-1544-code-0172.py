# In download_python_packages() function:
# Find these lines and DELETE them:
    # Cleanup temporary venv
    # print("Cleaning up temporary pip download environment...")
    # run_command(["rm", "-rf", temp_venv_path])
    # print("Finished downloading Python packages.") # Keep this print, but it should be moved outside the cleanup block


# In main() function:
# Add these lines after generate_offline_install_script() and before the final print statements:
    # Cleanup temporary venv here, after all download functions have run
    print("Cleaning up temporary pip download environment...")
    run_command(["rm", "-rf", os.path.join(BASE_DOWNLOAD_DIR, "temp_venv_for_pip_download")])
    print("Temporary pip download environment cleaned.")