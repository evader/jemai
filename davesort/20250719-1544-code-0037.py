# Use find to locate *.deb files that were recently downloaded in the cache
    # This is more robust as it doesn't rely on shell wildcard expansion in the calling script.
    # We specify max-age 15 minutes to only pick up recent downloads.
    print("Copying downloaded .deb packages from /var/cache/apt/archives/...")
    
    # Get a list of actual .deb files from the cache, ensuring we use sudo to list them
    # And then copy them using sudo cp
    command_to_get_debs = ["sudo", "find", "/var/cache/apt/archives/", "-maxdepth", "1", "-name", "*.deb", "-cmin", "-15"] # -cmin -15 finds files changed in last 15 mins
    
    # Capture the output of the find command
    result = run_command(command_to_get_debs, capture_output=True)
    deb_files = result.stdout.strip().split('\n')
    
    if not deb_files or (len(deb_files) == 1 and deb_files[0] == ''):
        print("Warning: No .deb files found in /var/cache/apt/archives/ that were recently modified. Check the apt output above.")
    else:
        # Filter out empty strings if any
        deb_files = [f for f in deb_files if f]
        
        # Now copy them one by one or in chunks
        for deb_file in deb_files:
            run_command(["sudo", "cp", deb_file, DEBS_PATH])