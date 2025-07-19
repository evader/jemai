def generate_offline_install_script():
    """Generates the shell script for offline installation."""
    script_path = os.path.join(SCRIPTS_PATH, "install_offline_ai.sh")
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# This script automates the OFFline installation of the AI OS components.\n")
        f.write("# It assumes all necessary files have been downloaded to the /opt/ai_offline_setup directory.\n")
        f.write("# IMPORTANT: Execute each step manually and verify success before proceeding.\n")
        f.write("# Most steps require 'sudo'.\n")
        f.write("\n")
        f.write("OFFLINE_SETUP_DIR=\"/opt/ai_offline_setup\"\n")
        f.write("PYTHON_VERSION=\"{}\"\n".format(PYTHON_VERSION))
        f.write("PYTORCH_CUDA_STR=\"{}\"\n".format(PYTORCH_CUDA_STR))
        f.write("CUDA_VERSION=\"{}\"\n".format(CUDA_VERSION))
        f.write("\n")
        f.write("set -e # Exit immediately if a command exits with a non-zero status.\n")
        f.write("\n")
        
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 0: Copy the downloaded setup files to the target machine.\"\n")
        f.write("echo \"  If you haven't already, copy the entire '{0}' folder\"\n".format(BASE_DOWNLOAD_DIR))
        f.write("echo \"  from your download machine to '/opt/' on this offline machine.\"\n")
        f.write("echo \"  E.g.: You are on your target offline machine. Your USB/external drive is /media/youruser/MySetupDrive.\"\n")
        f.write("echo \"  sudo mkdir -p ${OFFLINE_SETUP_DIR}\"\n")
        f.write("echo \"  sudo cp -r /media/youruser/MySetupDrive{0}/* ${OFFLINE_SETUP_DIR}/\"\n".format(BASE_DOWNLOAD_DIR))
        f.write("echo \"  Press ENTER to continue (after copying files).\"\n")
        f.write("read dummy\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 1: Install essential Ubuntu packages (offline).\"\n")
        f.write("echo \"  This may take a while. Ignore 'Could not resolve' warnings.\"\n")
        f.write("echo \"  If any package fails, try installing it individually first or check dependencies.\"\n")
        f.write("cd ${OFFLINE_SETUP_DIR}/ubuntu_debs || { echo 'Error: Missing ubuntu_debs directory.'; exit 1; }\n")
        f.write("sudo dpkg -i --ignore-depends=libnvidia-* *.deb || echo 'dpkg warnings/errors are common. Will try to fix later.'\n")
        f.write("echo \"  Attempting to fix broken installs. Any dependency errors means you likely missed downloading a .deb file.\"\n")
        # f.write("sudo apt --fix-broken install\n") # This requires internet
        f.write("echo \"*** IMPORTANT: If any package installation failed due to dependencies, try installing them manually in correct order or locate missing DEBs. ***\"\n")
        f.write("echo \"  Consider a brief internet connection for 'sudo apt update && sudo apt install -f' if stuck, then go offline again.\"\n")
        f.write("echo \"  Press ENTER to continue.\"\n")
        f.write("read dummy\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        if GPU_TYPE == "nvidia":
            f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("echo \"STEP 2: Install NVIDIA Drivers and CUDA Toolkit (offline).\"\n")
            f.write("echo \"  This will install the CUDA local repository and then the toolkit.\"\n")
            f.write("cd ${OFFLINE_SETUP_DIR}/nvidia_cuda || { echo 'Error: Missing nvidia_cuda directory.'; exit 1; }\n")
            f.write("LOCAL_CUDA_DEB=$(find . -maxdepth 1 -name 'cuda-repo-ubuntu*.deb' | head -n 1)\n") # Added -maxdepth 1 to avoid subdirectories
            f.write("if [ -z \"$LOCAL_CUDA_DEB\" ]; then echo 'No CUDA local deb found. Skipping CUDA installation.'; else sudo dpkg -i $LOCAL_CUDA_DEB; fi\n")
            f.write("echo \"  Attempting to update apt. (Expect warnings about not being able to fetch remote repos)\"\n")
            f.write("sudo apt update || echo 'apt update failed (as expected, no internet). Proceeding.'\n") # This will likely output errors, but proceed anyway
            f.write("echo \"  Installing CUDA toolkit (this installs from the local deb repo).\"\n")
            f.write(f"sudo apt install -y cuda-toolkit-{CUDA_VERSION.replace('.', '-')}\n") # Using f-string correctly
            f.write("echo \"  Installing general CUDA package for convenience (may pull more if available).\"\n")
            f.write("sudo apt install -y cuda\n")
            f.write("echo \"  Installing cuDNN (manual copy). You MUST have downloaded the tarball.\"\n") # Remind user
            f.write("CUDNN_TAR=$(find . -maxdepth 1 -name 'cudnn-*-cuda*.tgz' -o -name 'cudnn-*-cuda*.tar.xz' | head -n 1)\n") # Added -maxdepth 1
            f.write("if [ -z \"$CUDNN_TAR\" ]; then echo 'No cuDNN tarball found. Skipping cuDNN installation.'; else\n")
            f.write("  tar -xf \"$CUDNN_TAR\"\n")
            f.write("  sudo cp -P cuda/include/* /usr/local/cuda/include/\n")
            f.write("  sudo cp -P cuda/lib/lib64/* /usr/local/cuda/lib64/\n")
            f.write("  sudo chmod a+r /usr/local/cuda/include/cudnn.h /usr/local/cuda/lib64/libcudnn*\n")
            f.write("fi\n")
            f.write("echo \"  Verifying NVIDIA installation...\"\n")
            f.write("nvidia-smi\n")
            f.write("nvcc --version\n")
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

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 3: Install Miniconda (offline).\"\n")
        f.write("cd ${OFFLINE_SETUP_DIR}/miniconda || { echo 'Error: Missing miniconda directory.'; exit 1; }\n")
        f.write("BASE_MINICONDA_INSTALL_DIR=\"$HOME/miniconda3\"\n")
        f.write("bash Miniconda3-latest-Linux-x86_64.sh -b -p ${BASE_MINICONDA_INSTALL_DIR}\n")
        f.write("echo \"  Initializing Conda. You will need to restart your terminal or 'source ~/.bashrc'.\"\n")
        f.write("${BASE_MINICONDA_INSTALL_DIR}/bin/conda init\n")
        f.write("source ~/.bashrc # For this session\n")
        f.write("echo \"  Press ENTER to continue (after restarting your terminal or sourcing ~/.bashrc).\n")
        f.write("echo \"  You should see (base) in your prompt.\"\n")
        f.write("read dummy\n")
        f.write("source ${BASE_MINICONDA_INSTALL_DIR}/etc/profile.d/conda.sh # Ensure conda is activated for script\n") # Corrected this line as well
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 4: Create Conda environment and install Python packages (offline).\"\n")
        f.write("conda create -n ai_env python=${PYTHON_VERSION} -y\n")
        f.write("conda activate ai_env\n")
        f.write("echo \"  Installing PyTorch.\"\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/pytorch\" torch torchvision torchaudio\n")
        # Optional: TensorFlow
        f.write("echo \"  Installing TensorFlow (optional, if downloaded).\"\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/tensorflow\" tensorflow || echo 'TensorFlow install failed. Skipping if not needed.'\n")
        
        # Bitsandbytes and xformers often need specific compilation or wheels
        f.write("echo \"  Installing remaining common AI libraries.\"\n")
        # Try to install specific ones first with preferred options.
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" bitsandbytes || echo 'bitsandbytes install a common issue. If it fails, manual build might be needed.'\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" flash-attn || echo 'flash-attn install a common issue. If it fails, manual build might be needed.'\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" xformers || echo 'xformers install a common issue. If it fails, manual build might be needed.'\n")
        # Install the rest
        # This approach for installing the rest should work assuming well-formed wheel names
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" $(ls ${OFFLINE_SETUP_DIR}/python_packages/common_libs/*.whl | xargs -n 1 basename | sed 's/\(.*\)-\([0-9.]*\)-py.\+/\1/g' | uniq | grep -vE '^(torch|tensorflow|bitsandbytes|flash-attn|xformers)$' | tr '\\n' ' ')\n")
        f.write("echo \"  Verifying PyTorch CUDA installation.\"\n")
        f.write("python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}'); if torch.cuda.is_available(): print(f'GPU: {torch.cuda.get_device_name(0)}')\"\n")
        f.write("echo \"  Press ENTER to continue.\"\n")
        f.write("read dummy\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")
        
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 5: Prepare Git Repositories and AI Models.\"\n")
        f.write("echo \"  This step involves copying pre-downloaded Git repos and models.\"\n")
        f.write("echo \"  You may need to manually move specific model files (e.g., .safetensors checkpoints) to the correct subdirectories within each UI's 'models' folder.\"\n")
        f.write("cd ${OFFLINE_SETUP_DIR}/git_repos || { echo 'Error: Missing git_repos directory.'; exit 1; }\n")
        f.write("echo \"  Git clones are already done. No action needed here.\"\n")
        f.write("\n") # This was a single, empty `f.write("f.write("\n")` which became `f.write("f.write("))\n"`

        f.write("echo \"  Copying pre-downloaded AI Models to AI_MODELS_PATH for organization. You'll link them where needed.\"\n")
        f.write("cp -r ${OFFLINE_SETUP_DIR}/ai_models/* ${AI_MODELS_PATH} || echo 'Could not copy all models. Verify structure.'\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 6: Launching AI Applications (Examples).\"\n")
        f.write("echo \"  Ensure your Conda 'ai_env' is activated before running these commands!\"\n")
        f.write("echo \"  To activate: conda activate ai_env\"\n")
        f.write("echo \"  Then navigate to the application's directory and run the command.\"\n")
        f.write("\n")
        
        if DOWNLOAD_LLM_WEBUI:
            f.write("echo \"  --- Text Generation WebUI (Oobabooga) ---\"\n")
            f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/text-generation-webui/models/\"\n")
            f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/text-generation-webui\"\n")
            f.write("echo \"  python server.py --listen --share # Add your model flags like --model <model_name> --n-gpu-layers <num>\"\n")
            f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("echo \"  Access at http://localhost:7860 (or given share URL)\"\n")
            f.write("\n")
        
        if DOWNLOAD_STABLE_DIFFUSION_WEBUI:
            f.write("echo \"  --- Automatic1111 Stable Diffusion WebUI ---\"\n")
            f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/stable-diffusion-webui/models/Stable-diffusion/\"\n")
            f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/stable-diffusion-webui\"\n")
            f.write("echo \"  python launch.py --listen --xformers --enable-insecure-extension-access --no-download-clip --skip-install # Or other suitable flags\"\n")
            f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("echo \"  Access at http://localhost:7860\"\n")
            f.write("\n")

        if DOWNLOAD_COMFYUI:
            f.write("echo \"  --- ComfyUI ---\"\n")
            f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/comfyui/models/checkpoints/ (and other subfolders)\"\n")
            f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/comfyui\"\n")
            f.write("echo \"  python main.py --listen --cuda-device 0\"\n")
            f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("echo \"  Access at http://localhost:8188\"\n")
            f.write("\n")

        if DOWNLOAD_LLAMACPP:
            f.write("echo \"  --- llama.cpp (CLI LLM inference) ---\"\n")
            f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/llama.cpp\"\n")
            f.write("echo \"  make LLAMA_CUBLAS=1 # (for NVIDIA GPU acceleration)\"\n")
            f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/llama.cpp/models/\"\n")
            f.write("echo \"  Example: ./main -m models/your-model.gguf -p 'What is the capital of France?' -n 128\"\n")
            f.write("\n")
            
        if DOWNLOAD_WHISPERCPP:
            f.write("echo \"  --- whisper.cpp (CLI ASR) ---\"\n")
            f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/whisper.cpp\"\n")
            f.write("echo \"  make -j\"\n")
            f.write("echo \"  FFmpeg needed for audio formats beyond WAV: sudo apt install ffmpeg\"\n")
            f.write("echo \"  Download GGML models (e.g., from ggerganov/whisper.cpp Hugging Face) and place in models/\"\n")
            f.write("echo \"  Example: ./main -m models/ggml-large-v3.bin -f /path/to/your/audio.wav\"\n")
            f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"Setup complete! Remember to manually move models into app-specific directories.\"\n")
        f.write("echo \"For permanent environment variables (like CUDA PATH), add them to ~/.bashrc and source it.\"\n")
        f.write("echo \"Good luck with your offline AI adventures!\"\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")

    os.chmod(script_path, 0o755) # Make the script executable
    print(f"\nOffline installation script generated: {script_path}")
    print("Transfer this entire `/ai_offline_setup` directory to your target Ubuntu machine!")
    print("On the target machine, copy it to `/opt/` (e.g., `sudo cp -r <USB_DRIVE>/ai_offline_setup /opt/`)")
    print(f"Then execute it step-by-step: `cd {SCRIPTS_PATH}` and `./install_offline_ai.sh`")