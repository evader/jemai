print("\n--- Attempting to download flash-attn (may fail, often requires manual build) ---")
    try: # <--- REMOVE THIS try/except block
        # Pass check=False to run_command so it doesn't exit if pip download fails
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "flash-attn", "--no-binary", ":all:"], check=False)
    except Exception as e: # <--- REMOVE THIS try/except block
        print(f"Warning: Failed to download flash-attn. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")

    print("\n--- Attempting to download bitsandbytes (may fail, often requires manual wheel) ---")
    try: # <--- REMOVE THIS try/except block
        # Pass check=False to run_command so it doesn't exit if pip download fails
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "bitsandbytes", "--no-binary", ":all:"], check=False)
    except Exception as e: # <--- REMOVE THIS try/except block
        print(f"Warning: Failed to download bitsandbytes. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")