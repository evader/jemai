def run_command(command, cwd=None, check=True, shell=False, capture_output=False):
    """Executes a shell command. If check is True and command fails, script exits."""
    print(f"\nExecuting: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(command, cwd=cwd, check=check, shell=shell, capture_output=capture_output, text=True)
        if capture_output:
            print(result.stdout)
            if result.stderr:
                print(f"Stderr: {result.stderr}")
        return result.returncode == 0 # Returns True on success, False on failure (if check=False)
    except subprocess.CalledProcessError as e:
        # This block is only entered if check=True and command failed.
        # If check=False, subprocess.run would not raise this, it would just return non-zero.
        print(f"Error executing command: {e}")
        if capture_output: # Show output from failed command if it was captured
            print(f"Stdout: {e.stdout}\nStderr: {e.stderr}")
        sys.exit(1) # Critical failure, exit script because check was True
    except FileNotFoundError:
        print(f"Command not found. Make sure '{command[0] if isinstance(command, list) else command.split(' ')[0]}' is in your PATH.")
        sys.exit(1) # Critical failure, exit script
    except Exception as e:
        print(f"An unexpected error occurred in run_command: {e}")
        sys.exit(1) # Catch any other unexpected errors