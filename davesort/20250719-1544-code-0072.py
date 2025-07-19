def run_command(command, cwd=None, check=True, shell=False, capture_output=False):
    """Executes a shell command. If check is True and command fails, script exits.
    Returns CompletedProcess object if capture_output is True, otherwise returns bool (success/fail)."""
    print(f"\nExecuting: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(command, cwd=cwd, check=check, shell=shell, capture_output=capture_output, text=True)
        
        if capture_output:
            print(result.stdout) # Prints captured stdout to script's console
            if result.stderr:
                print(f"Stderr: {result.stderr}") # Prints captured stderr to script's console
            return result # <--- This is the key: it returns the actual result object
        else:
            return result.returncode == 0 # Return True/False indicating success

    except subprocess.CalledProcessError as e:
        # This block is only entered if check=True and command failed (non-zero return code).
        print(f"Error executing command: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        sys.exit(1) # Critical failure, exit script because check was True
    except FileNotFoundError:
        print(f"Command not found. Make sure '{command[0] if isinstance(command, list) else command.split(' ')[0]}' is in your PATH.")
        sys.exit(1) # Critical failure, exit script
    except Exception as e:
        print(f"An unexpected error occurred in run_command: {e}")
        sys.exit(1) # Catch any other unexpected errors