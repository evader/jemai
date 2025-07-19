def download_system_debs():
    """Downloads essential Ubuntu .deb packages."""
    print("Downloading essential Ubuntu .deb packages...")
    print("You might be prompted for your sudo password.")
    
    packages = [
        "git", "build-essential", "htop", "screenfetch", "curl", "wget", "ca-certificates",
        "python3-dev", "python3-venv", "libsndfile1-dev", "ffmpeg", "libssl-dev", "cmake",
        "libgl1", # General OpenGL library
        "libglib2.0-0t64", # Explicit for Noble (24.04), might fallback to libglib2.0-0 if not found
    ]
    
    if GPU_TYPE == "nvidia":
        packages.append("nvtop")

    run_command(["sudo", "apt", "update"]) 
    run_command(["sudo", "apt", "install", "--download-only", "--no-install-recommends"] + packages)
    
    print("Copying downloaded .deb packages from /var/cache/apt/archives/...")
    
    # Use find to locate *.deb files that were recently downloaded in the cache
    command_to_get_debs = ["sudo", "find", "/var/cache/apt/archives/", "-maxdepth", "1", "-name", "*.deb", "-cmin", "-15"] 
    # Capture the output of the find command
    print(f"Searching for .deb files with command: {' '.join(command_to_get_debs)}")
    result = run_command(command_to_get_debs, capture_output=True)
    deb_files = result.stdout.strip().split('\n')
    
    if not deb_files or (len(deb_files) == 1 and deb_files[0] == ''):
        print("Warning: No .deb files found in /var/cache/apt/archives/ that were recently modified or matching glob. Check the apt output above.")
    else:
        deb_files = [f for f in deb_files if f] # Filter out empty strings - CORRECTED THIS LINE
        print(f"Found {len(deb_files)} .deb files to copy.")
        for deb_file in deb_files:
            run_command(["sudo", "cp", deb_file, DEBS_PATH])
            
    print("Finished downloading Ubuntu .deb packages.")