f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("echo \"STEP 1: Install essential Ubuntu packages (offline).\"\n")
            f.write("echo \"  This may take a while. Ignore 'Could not resolve' warnings.\"\n")
            f.write("echo \"  If any package fails, try installing it individually first or check dependencies.\"\n")
            f.write("cd ${OFFLINE_SETUP_DIR}/ubuntu_debs || { echo 'Error: Missing ubuntu_debs directory.'; exit 1; }\n")
            f.write("sudo dpkg -i *.deb || echo 'dpkg warnings/errors are common. Will try to fix later.'\n") # <--- THIS LINE MUST BE CORRECTED
            f.write("echo \"  Attempting to fix broken installs. Any dependency errors means you likely missed downloading a .deb file.\"\n")