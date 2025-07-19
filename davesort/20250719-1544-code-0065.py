import os
import subprocess
import json
import requests
import sys

# --- Configuration ---
# Base directory for all downloads
BASE_DOWNLOAD_DIR = "./ai_offline_setup_downloads" # Creates a folder in the current directory

# Ubuntu version for .deb packages and CUDA installer (must match your actual Ubuntu OS)
UBUNTU_VERSION = "24.04" # Your system is Noble (24.04)

# Choose your GPU type - "nvidia" or "amd" (NVIDIA is much better supported for AI)
GPU_TYPE = "nvidia" 

# For NVIDIA, specify CUDA version. This should match the .run installer you will download.
# PyTorch/TensorFlow versions might internally use slightly older CUDA builds (e.g. cu121 for your 12.9.1 CUDA)
CUDA_VERSION = "12.9.1" 
# PyTorch CUDA version string for their pre-built wheels. For actual CUDA 12.x, PyTorch often uses 'cu121' or 'cu122'.
PYTORCH_CUDA_STR = "cu121" 

# Python version for the Conda environment on the *offline* machine.
# This should be a widely compatible version for AI libs (e.g., 3.10 or 3.11).
# The temporary venv for downloading will use your host's python (likely 3.12).
PYTHON_VERSION = "3.10" 

# --- AI Components to Download ---
DOWNLOAD_LLM_WEBUI = True
DOWNLOAD_STABLE_DIFFUSION_WEBUI = True
DOWNLOAD_COMFYUI = True
DOWNLOAD_LLAMACPP = True
DOWNLOAD_WHISPERCPP = True
DOWNLOAD_BARK_MODELS = False # Bark models are very large

# --- Hugging Face Models to Download (Adjust these lists as needed) ---
# LLM Models (GGUF for llama.cpp/oobabooga, HF_TRANSFORMERS for generic)
LLM_MODELS_HUGGINGFACE = [
    "TheBloke/Llama-2-7B-Chat-GGUF", # GGUF format for llama.cpp or text-generation-webui
    # "meta-llama/Llama-2-7b-chat-hf", # Hugging Face transformers format (much larger)
    # Add more LLMs here, e.g., "stabilityai/StableBeluga-7B"
]

# Stable Diffusion Models (Hugging Face diffusers format)
STABLE_DIFFUSION_MODELS_HUGGINGFACE = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/stable-diffusion-xl-refiner-1.0",
    "runwayml/stable-diffusion-v1-5",
    # Add more SD models here, e.g., "stabilityai/sdxl-turbo"
]

# Whisper ASR Models (Hugging Face)
WHISPER_MODELS_HUGGINGFACE = [
    "openai/whisper-large-v3", # This is the full PyTorch model, used by HuggingFace Transformers
]
# For whisper.cpp, you'd typically download specific GGML/GGUF models separately,
# often from https://huggingface.co/ggerganov/whisper.cpp/tree/main.
# The script can't auto-download arbitrary files from a tree, so include them in `ADDITIONAL_DOWNLOADS` if needed.

# --- Additional Downloads (e.g., CivitAI models, specific binaries) ---
# Provide direct download URLs and target filenames/paths within BASE_DOWNLOAD_DIR
ADDITIONAL_DOWNLOADS = [
    # Example for a Stable Diffusion checkpoint from CivitAI (replace with actual model URL)
    # {"url": "https://civitai.com/api/download/models/12345", "target_path": "ai_models/stable_diffusion/my_favorite_model.safetensors"},
]

# --- Internal Paths (Do not modify unless you know what you are doing) ---
DEBS_PATH = os.path.join(BASE_DOWNLOAD_DIR, "ubuntu_debs")
NVIDIA_CUDA_PATH = os.path.join(BASE_DOWNLOAD_DIR, "nvidia_cuda")
MINICONDA_PATH = os.path.join(BASE_DOWNLOAD_DIR, "miniconda")
PYTHON_PACKAGES_PATH = os.path.join(BASE_DOWNLOAD_DIR, "python_packages")
GIT_REPOS_PATH = os.path.join(BASE_DOWNLOAD_DIR, "git_repos")
AI_MODELS_PATH = os.path.join(BASE_DOWNLOAD_DIR, "ai_models")
SCRIPTS_PATH = os.path.join(BASE_DOWNLOAD_DIR, "scripts")

# --- Helper Functions ---

def create_directories():
    """Creates the necessary directory structure."""
    print(f"Creating download directories under: {BASE_DOWNLOAD_DIR}")
    for path in [DEBS_PATH, NVIDIA_CUDA_PATH, MINICONDA_PATH, PYTHON_PACKAGES_PATH, 
                 GIT_REPOS_PATH, AI_MODELS_PATH, SCRIPTS_PATH]:
        os.makedirs(path, exist_ok=True)
    
    # Subdirectories for Python packages and AI models
    os.makedirs(os.path.join(PYTHON_PACKAGES_PATH, "pytorch"), exist_ok=True)
    os.makedirs(os.path.join(PYTHON_PACKAGES_PATH, "tensorflow"), exist_ok=True) # Even if not using, good to have
    os.makedirs(os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), exist_ok=True)
    os.makedirs(os.path.join(AI_MODELS_PATH, "llm"), exist_ok=True)
    os.makedirs(os.path.join(AI_MODELS_PATH, "stable_diffusion"), exist_ok=True)
    os.makedirs(os.path.join(AI_MODELS_PATH, "audio"), exist_ok=True)
    print("Directories created.")

def run_command(command, cwd=None, check=True, shell=False, capture_output=False):
    """Executes a shell command."""
    print(f"\nExecuting: {' '.join(command) if isinstance(command, list) else command}")
    try:
        if capture_output:
            result = subprocess.run(command, cwd=cwd, check=check, shell=shell, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            return result
        else:
            subprocess.run(command, cwd=cwd, check=check, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        if capture_output:
            print(f"Stdout: {e.stdout}\nStderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Command not found. Make sure '{command[0] if isinstance(command, list) else command.split(' ')[0]}' is in your PATH.")
        sys.exit(1)

def download_file(url, target_path):
    """Downloads a file from a URL, skipping if it already exists."""
    if os.path.exists(target_path):
        print(f"File already exists: {target_path}. Skipping download.")
        return True # Indicate success
    
    print(f"Downloading {url} to {target_path}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded {target_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        if os.path.exists(target_path):
            os.remove(target_path) # Clean up partially downloaded file if it exists
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        if os.path.exists(target_path):
            os.remove(target_path)
        sys.exit(1)


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
        deb_files = [f for f in deb_files if f] # Filter out empty strings
        print(f"Found {len(deb_files)} .deb files to copy.")
        for deb_file in deb_files:
            run_command(["sudo", "cp", deb_file, DEBS_PATH])
            
    print("Finished downloading Ubuntu .deb packages.")


def download_nvidia_drivers_cuda_cudnn():
    """Downloads NVIDIA CUDA Toolkit .run installer and cuDNN."""
    if GPU_TYPE != "nvidia":
        print("Skipping NVIDIA downloads as GPU_TYPE is not 'nvidia'.")
        return

    print("Downloading NVIDIA CUDA Toolkit and cuDNN...")

    # Using the .run file installer, which is often more reliable on newer Ubuntu versions.
    # Verify this URL still works on NVIDIA's website!
    # Go to: https://developer.nvidia.com/cuda-downloads
    # Select: Linux -> x86_64 -> Ubuntu -> Your_UBUNTU_VERSION (e.g., 24.04) -> runfile (local)
    cuda_installer_url = "https://developer.download.nvidia.com/compute/cuda/12.9.1/local_installers/cuda_12.9.1_575.57.08_linux.run"
    cuda_installer_filename = os.path.basename(cuda_installer_url)

    print(f"Attempting to download CUDA Toolkit .run file: {cuda_installer_url}")
    download_file(cuda_installer_url, os.path.join(NVIDIA_CUDA_PATH, cuda_installer_filename))

    print("\nFor cuDNN, you must download it manually from https://developer.nvidia.com/rdp/cudnn-download-survey")
    print(f"Place the cuDNN `tar.xz` or `tgz` file for CUDA {CUDA_VERSION} in: {NVIDIA_CUDA_PATH}")
    print("Example filename: cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz (adjust for your CUDA version)")
    print("You will install it later by extracting and copying to /usr/local/cuda.")

    print("Finished NVIDIA CUDA/cuDNN instructions. Don't forget cuDNN manual download.")


def download_miniconda():
    """Downloads the Miniconda installer."""
    print("Downloading Miniconda installer...")
    miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    download_file(miniconda_url, os.path.join(MINICONDA_PATH, "Miniconda3-latest-Linux-x86_64.sh"))
    print("Finished downloading Miniconda.")


def download_python_packages():
    """Downloads all Python packages using pip download."""
    print("Downloading Python packages...")

    common_pip_packages = [
        "transformers", "accelerate", "safetensors", "datasets", "trl", "xformers",
        "onnxruntime", "sentencepiece", "tokenizers", "optimum", "jupyter", "matplotlib",
        "scikit-learn", "scipy", "notebook", "rich", "ipywidgets", "tabulate",
        "langchain", "llama-index", # Common LLM frameworks
        "opencv-python-headless", "scikit-image", # Image processing for SD UIs
        "invisible-watermark", # For Stable Diffusion
    ]

    # Create a temporary venv to run pip download using the host system's python
    temp_venv_path = os.path.join(BASE_DOWNLOAD_DIR, "temp_venv_for_pip_download")
    
    # Use sys.executable (your system's python, likely 3.12) for the temporary venv.
    # This ensures compatibility with available wheels on PyPI.
    run_command([sys.executable, "-m", "venv", temp_venv_path])
    
    pip_executable = os.path.join(temp_venv_path, "bin", "pip")

    # Install pip and setuptools in the temporary venv to ensure they are up-to-date
    run_command([pip_executable, "install", "--upgrade", "pip", "setuptools", "wheel"])
    
    # Install huggingface_hub so we can use huggingface-cli later.
    run_command([pip_executable, "install", "huggingface_hub"])


    # ===== 1. PyTorch (with CUDA) - FIRST to ensure torch is available for others =====
    print("\n--- Downloading PyTorch and related packages ---")
    
    # Use a recent PyTorch version compatible with PYTORCH_CUDA_STR (e.g., cu121)
    # Check https://pytorch.org/get-started/locally/ for the latest stable version
    torch_version = "2.3.1" 
    torchvision_version = "0.18.1"
    torchaudio_version = "2.3.1"

    torch_packages = [
        f"torch=={torch_version}+{PYTORCH_CUDA_STR}",
        f"torchvision=={torchvision_version}+{PYTORCH_CUDA_STR}",
        f"torchaudio=={torcaudio_version}+{PYTORCH_CUDA_STR}",
    ]
    pytorch_extra_index_url = f"https://download.pytorch.org/whl/{PYTORCH_CUDA_STR}"
    
    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "pytorch"), 
                 "--extra-index-url", pytorch_extra_index_url] + torch_packages)

    # ===== 2. TensorFlow (if desired, make sure CUDA version compatibility) - SECOND =====
    print("\n--- Downloading TensorFlow (optional) ---")
    tf_packages = ["tensorflow[and-cuda]==2.19.0"] # Using a recent version that showed as available
    try:
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "tensorflow")] + tf_packages)
    except Exception:
        print("Skipping TensorFlow download due to potential issues or if not explicitly needed.")
        print("If you need it, verify exact versions and try again.")
        

    # ===== 3. Common AI Libraries (excluding problematic ones like flash-attn/bitsandbytes for bulk download) =====
    print("\n--- Downloading Common AI Libraries ---")
    # Example for oobabooga dependencies:
    oobabooga_deps = [
        "Jinja2", "gradio", "markdown-it-py", "Pygments", "linkify-it-py", "mdurl",
        "requests", "sentencepiece", "tk", "tqdm", "uvicorn", "websockets", "starlette",
        "fastapi", "pydantic", "typing-extensions", "sse_starlette", "httpx", "aiofiles",
        "scipy", "numexpr", "ninja"
    ]
    
    # Example for Automatic1111/ComfyUI dependencies:
    sd_deps = [
        "Pillow", "numpy", "scipy", "tqdm", "requests", "huggingface_hub", "diffusers",
        "accelerate", "safetensors", "omegaconf", "einops", "jsonmerge",
        "resize-right", "torchmetrics", "clip", "open_clip_torch", # k-diffusion may use torch for metadata/build
        "exifread", "piexif", "send2trash", "pyyaml", "mediapipe", "facexlib", "gfpgan", "realesrgan",
        "basicsr",
        "gradio", # Changed from gradio==3.32.0 to just 'gradio' to find Python 3.12 compatible version
    ]
        
    all_common_packages = list(set(common_pip_packages + oobabooga_deps + sd_deps))

    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs")] + all_common_packages)
    
    # ===== 4. Attempt to download flash-attn and bitsandbytes separately =====
    # These often require specific pre-compiled wheels or careful source compilation
    # for full CUDA integration. For offline mode, this is very tricky.
    
    print("\n--- Attempting to download flash-attn (may fail, often requires manual build) ---")
    try:
        # `--no-binary :all:` forces it to try source or specific platform wheels, not generic ones.
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "flash-attn", "--no-binary", ":all:"])
    except Exception as e:
        print(f"Warning: Failed to download flash-attn. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")

    print("\n--- Attempting to download bitsandbytes (may fail, often requires manual wheel) ---")
    try:
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "bitsandbytes", "--no-binary", ":all:"])
    except Exception as e:
        print(f"Warning: Failed to download bitsandbytes. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")


    # Cleanup temporary venv
    print("Cleaning up temporary pip download environment...")
    run_command(["rm", "-rf", temp_venv_path])

    print("Finished downloading Python packages.")


def clone_git_repos():
    """Clones necessary Git repositories."""
    print("Cloning Git repositories...")
    
    if DOWNLOAD_LLM_WEBUI:
        run_command(["git", "clone", "https://github.com/oobabooga/text-generation-webui.git", 
                     os.path.join(GIT_REPOS_PATH, "text-generation-webui")])
    if DOWNLOAD_STABLE_DIFFUSION_WEBUI:
        run_command(["git", "clone", "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git", 
                     os.path.join(GIT_REPOS_PATH, "stable-diffusion-webui")])
    if DOWNLOAD_COMFYUI:
        run_command(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", 
                     os.path.join(GIT_REPOS_PATH, "comfyui")])
    if DOWNLOAD_LLAMACPP:
        run_command(["git", "clone", "https://github.com/ggerganov/llama.cpp.git", 
                     os.path.join(GIT_REPOS_PATH, "llama.cpp")])
    if DOWNLOAD_WHISPERCPP:
        run_command(["git", "clone", "https://github.com/ggerganov/whisper.cpp.git", 
                     os.path.join(GIT_REPOS_PATH, "whisper.cpp")])
    if DOWNLOAD_BARK_MODELS: # Bark is a Python library, not a standalone UI
        run_command(["git", "clone", "https://github.com/suno-ai/bark.git", 
                     os.path.join(GIT_REPOS_PATH, "bark")])
                     
    print("Finished cloning Git repositories.")


def download_ai_models():
    """Downloads AI models from Hugging Face."""
    print("Downloading AI models from Hugging Face...")
    
    # Ensure huggingface_hub is installed (it should be from download_python_packages)
    try:
        import huggingface_hub
    except ImportError:
        print("huggingface_hub not found. This should have been installed. Trying to install now...")
        run_command([sys.executable, "-m", "pip", "install", "huggingface_hub"], check=False)

    from huggingface_hub import HfApi, snapshot_download

    api = HfApi()

    # Download LLM models
    for model_id in LLM_MODELS_HUGGINGFACE:
        target_dir = os.path.join(AI_MODELS_PATH, "llm", model_id.split('/')[-1].replace('.', '_'))
        print(f"Downloading LLM model: {model_id} to {target_dir}")
        try:
            snapshot_download(repo_id=model_id, local_dir=target_dir, local_dir_use_symlinks=False)
        except Exception as e:
            print(f"Warning: Failed to download {model_id}: {e}")
            print("Try manually with `huggingface-cli download <repo_id> --local-dir <path> --local-dir-use-symlinks False`")

    # Download Stable Diffusion models
    for model_id in STABLE_DIFFUSION_MODELS_HUGGINGFACE:
        target_dir = os.path.join(AI_MODELS_PATH, "stable_diffusion", model_id.split('/')[-1].replace('.', '_'))
        print(f"Downloading Stable Diffusion model: {model_id} to {target_dir}")
        try:
            snapshot_download(repo_id=model_id, local_dir=target_dir, local_dir_use_symlinks=False)
        except Exception as e:
            print(f"Warning: Failed to download {model_id}: {e}")
            print("Try manually with `huggingface-cli download <repo_id> --local-dir <path> --local-dir-use-symlinks False`")

    # Download Whisper models
    for model_id in WHISPER_MODELS_HUGGINGFACE:
        target_dir = os.path.join(AI_MODELS_PATH, "audio", model_id.split('/')[-1].replace('.', '_'))
        print(f"Downloading Whisper model: {model_id} to {target_dir}")
        try:
            snapshot_download(repo_id=model_id, local_dir=target_dir, local_dir_use_symlinks=False)
        except Exception as e:
            print(f"Warning: Failed to download {model_id}: {e}")
            print("Try manually with `huggingface-cli download <repo_id> --local-dir <path> --local-dir-use-symlinks False`")
            
    # Download Bark models (if enabled)
    if DOWNLOAD_BARK_MODELS:
        print("\n--- Preparing Bark model download instructions ---")
        print("Bark models are often downloaded automatically by the `suno-ai/bark` library.")
        print("To pre-download, you can try running their download script or let it download on first run.")
        # Alternatively, find the model IDs on Hugging Face and add them to LLM_MODELS_HUGGINGFACE,
        # e.g., "suno/bark-small", "suno/bark-coarse" etc.

    print("Finished downloading AI models.")

def download_additional_files():
    """Downloads any manually specified additional files."""
    if not ADDITIONAL_DOWNLOADS:
        print("No additional files specified for download.")
        return

    print("Downloading additional files...")
    for item in ADDITIONAL_DOWNLOADS:
        target_full_path = os.path.join(BASE_DOWNLOAD_DIR, item["target_path"])
        os.makedirs(os.path.dirname(target_full_path), exist_ok=True)
        download_file(item["url"], target_full_path)
    print("Finished downloading additional files.")


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
        f.write(f"PYTHON_VERSION=\"{PYTHON_VERSION}\"\n")
        f.write(f"PYTORCH_CUDA_STR=\"{PYTORCH_CUDA_STR}\"\n")
        f.write(f"CUDA_VERSION=\"{CUDA_VERSION}\"\n")
        f.write("\n")
        f.write("set -e # Exit immediately if a command exits with a non-zero status.\n")
        f.write("\n")
        
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 0: Copy the downloaded setup files to the target machine.\"\n")
        f.write(f"echo \"  If you haven't already, copy the entire '{BASE_DOWNLOAD_DIR}' folder\"\n")
        f.write("echo \"  from your download machine to '/opt/' on this offline machine.\"\n")
        f.write("echo \"  E.g.: You are on your target offline machine. Your USB/external drive is /media/youruser/MySetupDrive.\"\n")
        f.write("echo \"  sudo mkdir -p ${OFFLINE_SETUP_DIR}\"\n")
        f.write("echo \"  sudo cp -r /media/youruser/MySetupDrive/ai_offline_setup_downloads/* ${OFFLINE_SETUP_DIR}/\"\n") # Adjusted for new BASE_DOWNLOAD_DIR structure
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
        f.write("echo \"*** IMPORTANT: If any package installation failed due to dependencies, try installing them manually in correct order or locate missing DEBs. ***\"\n")
        f.write("echo \"  Consider a brief internet connection for 'sudo apt update && sudo apt install -f' if stuck, then go offline again.\"\n")
        f.write("echo \"  Press ENTER to continue.\"\n")
        f.write("read dummy\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

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
            f.write("  sudo sh \"$CUDA_INSTALLER_RUN\" # This will be fully interactive - the safer option for first time.\n")
            f.write("  echo \"  Follow the on-screen prompts carefully!\"\n")
            f.write("fi\n")
            f.write("echo \"  Installing cuDNN (manual copy). You MUST have downloaded the tarball.\"\n")
            f.write("CUDNN_TAR=$(find . -maxdepth 1 -name 'cudnn-*-cuda*.tgz' -o -name 'cudnn-*-cuda*.tar.xz' | head -n 1)\n")
            f.write("if [ -z \"$CUDNN_TAR\" ]; then echo 'No cuDNN tarball found. Skipping cuDNN installation.'; else\n")
            f.write("  if [ ! -d \"/usr/local/cuda\" ]; then\n")
            f.write("    echo \"/usr/local/cuda does not exist. cuDNN cannot be installed. Did CUDA installation fail?\"\n")
            f.write("  else\n")
            f.write("    tar -xf \"$CUDNN_TAR\"\n")
            f.write("    sudo cp -P cuda/include/* /usr/local/cuda/include/\n")
            f.write("    sudo cp -P cuda/lib/lib64/* /usr/local/cuda/lib64/\n")
            f.write("    sudo chmod a+r /usr/local/cuda/include/cudnn.h /usr/local/cuda/lib64/libcudnn*\n")
            f.write("    rm -rf cuda # Clean up extracted folder\n")
            f.write("  fi\n")
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
        f.write("echo \"  Press ENTER to continue (after restarting your terminal or sourcing ~/.bashrc).\"\n")
        f.write("echo \"  You should see (base) in your prompt.\"\n")
        f.write("read dummy\n")
        f.write("source ${BASE_MINICONDA_INSTALL_DIR}/etc/profile.d/conda.sh # Ensure conda is activated for script\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 4: Create Conda environment and install Python packages (offline).\"\n")
        f.write(f"conda create -n ai_env python={PYTHON_VERSION} -y\n")
        f.write("conda activate ai_env\n")
        f.write("echo \"  Installing PyTorch.\"\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/pytorch\" torch torchvision torchaudio\n")
        f.write("echo \"  Installing TensorFlow (optional, if downloaded).\"\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/tensorflow\" tensorflow || echo 'TensorFlow install failed. Skipping if not needed.'\n")
        
        f.write("echo \"  Installing remaining common AI libraries.\"\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" bitsandbytes || echo 'bitsandbytes installation might fail. If so, build manually or get specified wheels.'\n")
        f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" flash-attn || echo 'flash-attn installation might fail. If so, build manually or get specified wheels.'\n")
        f.write(r"pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" $(ls ${OFFLINE_SETUP_DIR}/python_packages/common_libs/*.whl | xargs -n 1 basename | sed 's/\(.*\)-\([0-9.]*\)-py.\+/\1/g' | uniq | grep -vE '^(torch|tensorflow|bitsandbytes|flash-attn|xformers)$' | tr '\\n' ' ')" + "\n")
        
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
    print("Transfer this entire `/ai_offline_setup_downloads` directory to your target Ubuntu machine!")
    print("On the target machine, copy it to `/opt/` (e.g., `sudo cp -r <USB_DRIVE>/ai_offline_setup_downloads /opt/`)")
    print(f"Then execute it step-by-step: `cd {SCRIPTS_PATH}` and `./install_offline_ai.sh`")

def main():
    print("--- Starting AI OS Offline Preparation Script (Online Phase) ---")
    print(f"All downloads will go into: {BASE_DOWNLOAD_DIR}")
    print("Ensure you have sufficient disk space (hundreds of GBs to TBs!).")
    print("This script requires internet access to download files.")
    print("You might be prompted for your sudo password for apt operations.")
    
    # Pre-flight checks
    if os.geteuid() == 0:
        print("WARNING: Running this script as root might lead to permission issues for user files.")
        print("It's better to run as a regular user, it will prompt for `sudo` when required.")
    
    # Using hardcoded CUDA version based on what was found to work with .run installer for 24.04
    print(f"Using CUDA version: {CUDA_VERSION}, PyTorch CUDA string: {PYTORCH_CUDA_STR}")

    create_directories()
    download_system_debs()
    download_nvidia_drivers_cuda_cudnn()
    download_miniconda()
    download_python_packages()
    clone_git_repos()
    download_ai_models()
    download_additional_files()
    generate_offline_install_script()

    print("\n--- AI OS Offline Preparation Completed Successfully! ---")
    print("Now, transfer the entire `/ai_offline_setup_downloads` directory to your offline Ubuntu machine.")
    print(f"On the offline machine, run `{os.path.join(SCRIPTS_PATH, 'install_offline_ai.sh')}` step-by-step.")

if __name__ == "__main__":
    main()