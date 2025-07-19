if GPU_TYPE == "nvidia":
            f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("echo \"STEP 2: Install NVIDIA Drivers and CUDA Toolkit (OFFLINE).\"\n")
            f.write("echo \"  You will be prompted LIVE during this installation. Follow instructions carefully!\"\n")
            f.write("echo \"  It's critical not to skip components unless you know what you're doing.\"\n")
            f.write("echo \"  Typical choices: Accept Eula, Install Driver (unless you have a newer one), CUDA Toolkit, Symlink.\"\n")
            f.write("cd ${OFFLINE_SETUP_DIR}/nvidia_cuda || { echo 'Error: Missing nvidia_cuda directory.'; exit 1; }\n")
            f.write("CUDA_INSTALLER_RUN=$(find . -maxdepth 1 -name 'cuda_*.run' | head -n 1)\n")
            f.write("if [ -z \"$CUDA_INSTALLER_RUN\" ]; then echo 'No CUDA .run installer found. Skipping CUDA installation.'; else\n")
            f.write("  chmod +x \"$CUDA_INSTALLER_RUN\"\n")
            f.write("  sudo \"$CUDA_INSTALLER_RUN\" --silent --toolkit --driver --library_path=/usr/local/cuda/lib64\n") # Added --silent to attempt non-interactive install as much as possible, but often still prompts.
            f.write("  echo \"NOTE: The --silent flag attempts an unattended install, but you might still be prompted.\"\n")
            f.write("  echo \"      If the installer hangs or requires input, remove '--silent' and run it manually.\"\n")
            f.write("  # You might replace the line above with just:
            # f.write("  # sudo sh \"$CUDA_INSTALLER_RUN\" # This will be fully interactive - the safer option for first time.
            # f.write("  # echo \"  Follow the on-screen prompts carefully!\"\n")

            f.write("fi\n")
            f.write("echo \"  Installing cuDNN (manual copy). You MUST have downloaded the tarball.\"\n")
            f.write("CUDNN_TAR=$(find . -maxdepth 1 -name 'cudnn-*-cuda*.tgz' -o -name 'cudnn-*-cuda*.tar.xz' | head -n 1)\n")
            f.write("if [ -z \"$CUDNN_TAR\" ]; then echo 'No cuDNN tarball found. Skipping cuDNN installation.'; else\n")
            f.write("  # Ensure /usr/local/cuda exists after the .run install
            f.write("  if [ ! -d \"/usr/local/cuda\" ]; then\n")
            f.write("    echo \"/usr/local/cuda does not exist. cuDNN cannot be installed. Did CUDA installation fail?\"\n")
            f.write("  else\n")
            f.write("    tar -xf \"$CUDNN_TAR\"\n")
            f.write("    sudo cp -P cuda/include/* /usr/local/cuda/include/\n")
            f.write("    sudo cp -P cuda/lib/lib64/* /usr/local/cuda/lib64/\n")
            f.write("    sudo chmod a+r /usr/local/cuda/include/cudnn.h /usr/local/cuda/lib64/libcudnn*\n")
            f.write("    rm -rf cuda # Clean up extracted folder
            f.write("  fi\n")
            f.write("fi\n")
            f.write("echo \"  Verifying NVIDIA installation...\"\n")
            f.write("nvidia-smi\n") # Check if driver is loaded
            f.write("nvcc --version\n") # Check if toolkit is installed
            f.write("echo \"  Add CUDA to PATH and LD_LIBRARY_PATH (add to ~/.bashrc for permanent).\"\n")
            f.write("sudo sh -c 'echo \"export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}\" >> /etc/profile.d/cuda.sh'\n")
            f.write("sudo sh -c 'echo \"export LD_LIBRARY_PATH=/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}\" >> /etc/profile.d/cuda.sh'\n")
            f.write("source /etc/profile.d/cuda.sh\n")
            f.write("echo \"*** IMPORTANT: YOU MAY NEED TO REBOOT YOUR SYSTEM FOR DRIVERS TO TAKE EFFECT! ***\"\n")
            f.write("echo \"  After reboot, run `nvidia-smi` to confirm drivers are working.\"\n")
            f.write("echo \"  Press ENTER to continue.\"\n")
            f.write("read dummy\n")
            f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("\n")