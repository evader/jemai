def download_system_debs():
    """Downloads essential Ubuntu .deb packages."""
    print("Downloading essential Ubuntu .deb packages...")
    print("You might be prompted for your sudo password.")
    
    packages = [
        "git", "build-essential", "htop", "screenfetch", "curl", "wget", "ca-certificates",
        "python3-dev", "python3-venv", "libsndfile1-dev", "ffmpeg", "libssl-dev", "cmake",
        "libgl1", # Replaced libgl1-mesa-glx with the more generic libgl1
        "libglib2.0-0t64", # Explicitly request the t64 version if that's what apt suggested
    ]
    
    if GPU_TYPE == "nvidia":
        packages.append("nvtop")

    run_command(["sudo", "apt", "update"]) # Requires internet initially
    
    # Run the download command
    run_command(["sudo", "apt", "install", "--download-only", "--no-install-recommends"] + packages)
    
    # Use find to locate *.deb files that were recently downloaded in the cache
    print("Copying downloaded .deb packages from /var/cache/apt/archives/...")
    
    command_to_get_debs = ["sudo", "find", "/var/cache/apt/archives/", "-maxdepth", "1", "-name", "*.deb", "-cmin", "-15"] 
    # Capture the output of the find command
    # run_command will print stdout/stderr by default even if captured.
    print(f"Searching for .deb files with command: {' '.join(command_to_get_debs)}")
    result = run_command(command_to_get_debs, capture_output=True)
    deb_files = result.stdout.strip().split('\n')
    
    if not deb_files or (len(deb_files) == 1 and deb_files[0] == ''):
        print("Warning: No .deb files found in /var/cache/apt/archives/ that were recently modified. Check the apt output above.")
    else:
        deb_files = [f for f in deb_files if f] # Filter out empty strings
        print(f"Found {len(deb_files)} .deb files to copy.")
        for deb_file in deb_files:
            run_command(["sudo", "cp", deb_file, DEBS_PATH])
            
    print("Finished downloading Ubuntu .deb packages.") # This line must be outside the loop AND on its own line