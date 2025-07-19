print("\n--- Attempting to download flash-attn (may fail, often requires manual build) ---")
    # Pass check=False to run_command so it doesn't exit the script on pip download failure
    flash_attn_success = run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "flash-attn", "--no-binary", ":all:"], check=False)
    if not flash_attn_success:
        print(f"Warning: Failed to download flash-attn. This often indicates a complex build requirement. Check previous command output.")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")

    print("\n--- Attempting to download bitsandbytes (may fail, often requires manual wheel) ---")
    # Pass check=False to run_command so it doesn't exit the script on pip download failure
    bitsandbytes_success = run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "bitsandbytes", "--no-binary", ":all:"], check=False)
    if not bitsandbytes_success:
        print(f"Warning: Failed to download bitsandbytes. This often indicates a complex build requirement. Check previous command output.")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")