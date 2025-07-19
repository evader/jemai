import os
import subprocess
import json
import requests
import sys

# --- Configuration ---
# Base directory for all downloads
BASE_DOWNLOAD_DIR = "/ai_offline_setup"

# Ubuntu version for .deb packages (important for CUDA and general debs)
UBUNTU_VERSION = "22.04" 

# Choose your GPU type - "nvidia" or "amd" (NVIDIA is much better supported for AI)
GPU_TYPE = "nvidia" 

# For NVIDIA, specify CUDA version. Visit https://pytorch.org/get-started/locally/ for compatible versions.
# Example: 11.8 or 12.1. Make sure it matches your driver compatibility.
CUDA_VERSION = "11.8" 
# Corresponding PyTorch CUDA version string (e.g., 'cu118', 'cu121')
PYTORCH_CUDA_STR = f"cu{CUDA_VERSION.replace('.', '')}" 

# Python version for the Conda environment
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
    """Downloads a file from a URL."""
    print(f"Downloading {url} to {target_path}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded {target_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        sys.exit(1)

def download_system_debs():
    """Downloads essential Ubuntu .deb packages."""
    print("Downloading essential Ubuntu .deb packages...")
    print("You might be prompted for your sudo password.")
    
    # Common packages needed for build tools, python, git, etc.
    # Note: --no-install-recommends helps reduce the number of dependency downloads
    packages = [
        "git", "build-essential", "htop", "screenfetch", "curl", "wget", "ca-certificates",
        "python3-dev", "python3-venv", "libsndfile1-dev", "ffmpeg", "libssl-dev", "cmake",
        "libgl1-mesa-glx", "libglib2.0-0", # Common display/graphics libs for UIs
    ]
    
    # Try to download NVtop for NVIDIA users
    if GPU_TYPE == "nvidia":
        packages.append("nvtop")

    # This command downloads packages into /var/cache/apt/archives
    run_command(["sudo", "apt", "update"]) # Requires internet initially
    run_command(["sudo", "apt", "install", "--download-only", "--no-install-recommends"] + packages)
    
    # Copy downloaded .deb files to our designated directory
    run_command(["sudo", "cp", "/var/cache/apt/archives/*.deb", DEBS_PATH])
    print("Finished downloading Ubuntu .deb packages.")

def download_nvidia_drivers_cuda_cudnn():
    """Downloads NVIDIA CUDA Toolkit .deb local installer and cuDNN."""
    if GPU_TYPE != "nvidia":
        print("Skipping NVIDIA downloads as GPU_TYPE is not 'nvidia'.")
        return

    print("Downloading NVIDIA CUDA Toolkit and cuDNN...")

    # Find the correct CUDA Toolkit local .deb installer URL
    # This URL might change, always check NVIDIA's official site:
    # https://developer.nvidia.com/cuda-downloads (Linux -> x86_64 -> Ubuntu -> UBUNTU_VERSION -> deb (local))
    
    # Example for CUDA 11.8 on Ubuntu 22.04:
    # https://developer.nvidia.com/downloads/cuda/11.8.0/local_installers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb
    cuda_url_base = f"https://developer.nvidia.com/downloads/cuda/{CUDA_VERSION.replace('.', '')}0/local_installers/"
    cuda_deb_filename = f"cuda-repo-ubuntu{UBUNTU_VERSION.replace('.', '')}-{CUDA_VERSION.replace('.', '-')}-local_{CUDA_VERSION}-*-1_amd64.deb"
    
    # Unfortunately, the exact filename with build numbers changes. Better to provide a direct, manually verified link.
    # For robust scripting, it's better to fetch from a known stable source or hardcode tested URLs.
    if CUDA_VERSION == "11.8" and UBUNTU_VERSION == "22.04":
        cuda_installer_url = "https://developer.nvidia.com/downloads/cuda/11.8.0/local_installers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb"
    elif CUDA_VERSION == "12.1" and UBUNTU_VERSION == "22.04":
         cuda_installer_url = "https://developer.nvidia.com/downloads/cuda/12.1.0/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb"
    else:
        print(f"Warning: CUDA {CUDA_VERSION} for Ubuntu {UBUNTU_VERSION} not hardcoded. Please manually download from NVIDIA and place in {NVIDIA_CUDA_PATH}.")
        print("Skipping automatic CUDA .deb download.")
        print("You'll need to manually ensure it includes the CUDA toolkit and drivers for offline installation.")
        cuda_installer_url = None # Placeholder if we don't have a specific URL

    if cuda_installer_url:
        download_file(cuda_installer_url, os.path.join(NVIDIA_CUDA_PATH, os.path.basename(cuda_installer_url)))

    # Download cuDNN (requires NVIDIA Developer Program account and login)
    # This is often done manually because of the login wall.
    print("For cuDNN, you must download it manually from https://developer.nvidia.com/rdp/cudnn-download-survey")
    print(f"Place the cuDNN `tar.xz` or `tgz` file for CUDA {CUDA_VERSION} in: {NVIDIA_CUDA_PATH}")
    print("Example filename: cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz")
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
        "flash-attn", # Often needs special build for CUDA, `--no-binary :all: --no-deps` is a good start
        "bitsandbytes", # Specific CUDA build, `--no-binary :all: --no-deps` for pre-download
        "langchain", "llama-index", # Common LLM frameworks
        "opencv-python-headless", "scikit-image", # Image processing for SD UIs
        "invisible-watermark", # For Stable Diffusion
    ]

    # Create a temporary venv to run pip download
    temp_venv_path = os.path.join(BASE_DOWNLOAD_DIR, "temp_venv_for_pip_download")
    run_command([sys.executable, "-m", "venv", temp_venv_path])
    pip_executable = os.path.join(temp_venv_path, "bin", "pip")

    # Install pip and setuptools in the temporary venv to ensure they are up-to-date
    run_command([pip_executable, "install", "--upgrade", "pip", "setuptools", "wheel"])
    
    # Install huggingface_hub so we can use huggingface-cli later
    run_command([pip_executable, "install", "huggingface_hub"])

    # PyTorch
    print("\n--- Downloading PyTorch and related packages ---")
    torch_packages = [
        f"torch==2.1.2+{PYTORCH_CUDA_STR}", # Adjust version if needed
        f"torchvision==0.16.2+{PYTORCH_CUDA_STR}",
        f"torchaudio==2.1.2+{PYTORCH_CUDA_STR}",
    ]
    pytorch_extra_index_url = f"https://download.pytorch.org/whl/{PYTORCH_CUDA_STR}"
    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "pytorch"), 
                 "--extra-index-url", pytorch_extra_index_url] + torch_packages)

    # TensorFlow (if desired, make sure CUDA version compatibility)
    print("\n--- Downloading TensorFlow (optional) ---")
    # TF has specific CUDA/cuDNN requirements. Check TF docs for your desired version.
    # Example for TF 2.15 with CUDA 11.8:
    tf_packages = ["tensorflow[and-cuda]==2.15.0"] # This pulls many deps for CUDA, can be huge
    try:
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "tensorflow")] + tf_packages)
    except Exception:
        print("Skipping TensorFlow download due to potential issues or if not explicitly needed.")
        print("If you need it, verify exact versions and try again.")
        

    # Common AI Libraries for LLMs and Stable Diffusion
    print("\n--- Downloading Common AI Libraries ---")
    # For bitsandbytes and flash-attn, sometimes direct download of wheel or source compile is needed.
    # `--no-binary :all: --no-deps` means download source or universal wheel, but not pre-compiled specific wheels.
    # This ensures maximum compatibility for offline installation as a fallback.
    # You might need to manually get `bitsandbytes` wheels from their GitHub releases.
    
    # Try one go. If it fails due to specific packages, break it down.
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
        "accelerate", "safetensors", "omegaconf", "einops", "jsonmerge", "cleanfid",
        "resize-right", "torchmetrics", "clip", "k-diffusion", "open_clip_torch",
        "exifread", "piexif", "send2trash", "pyyaml", "mediapipe", "facexlib", "gfpgan", "realesrgan",
        "basicsr", "gradio==3.32.0", # A1111 often pins gradio. Check their webui-user.bat/sh
    ]
    
    # Combine and deduplicate
    all_common_packages = list(set(common_pip_packages + oobabooga_deps + sd_deps))

    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs")] + all_common_packages)
    
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
    
    # Ensure huggingface_hub is installed, it was already installed in temp_venv
    # As a fallback, install here globally if the script is run without venv support
    try:
        import huggingface_hub
    except ImportError:
        print("huggingface_hub not found. Installing now...")
        run_command(["pip", "install", "huggingface_hub"], check=False) # Non-critical if it fails

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
        f.write("PYTHON_VERSION=\"{}\"\n".format(PYTHON_VERSION))
        f.write("PYTORCH_CUDA_STR=\"{}\"\n".format(PYTORCH_CUDA_STR))
        f.write("CUDA_VERSION=\"{}\"\n".format(CUDA_VERSION))
        f.write("\n")
        f.write("set -e # Exit immediately if a command exits with a non-zero status.\n")
        f.write("\n")
        
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 0: Copy the downloaded setup files to the target machine.\"\n")
        f.write("echo \"  If you haven't already, copy the entire '{0}' folder\"\n".format(BASE_DOWNLOAD_DIR))
        f.write("f.write(\"  from your download machine to '/opt/' on this offline machine.\"\n")
        f.write("echo \"  E.g.: You are on your target offline machine. Your USB/external drive is /media/youruser/MySetupDrive.\"\n")
        f.write("echo \"  sudo mkdir -p ${OFFLINE_SETUP_DIR}\"\n")
        f.write("echo \"  sudo cp -r /media/youruser/MySetupDrive{0}/* ${OFFLINE_SETUP_DIR}/\"\n".format(BASE_DOWNLOAD_DIR))
        f.write("echo \"  Press ENTER to continue (after copying files).\"\n")
        f.write("f.write("read dummy)\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 1: Install essential Ubuntu packages (offline).\"\n")
        f.write("echo \"  This may take a while. Ignore 'Could not resolve' warnings.\"\n")
        f.write("echo \"  If any package fails, try installing it individually first or check dependencies.\"\n")
        f.write("f.write("cd ${OFFLINE_SETUP_DIR}/ubuntu_debs || { echo 'Error: Missing ubuntu_debs directory.'; exit 1; }\n")
        f.write("f.write("sudo dpkg -i --ignore-depends=libnvidia-* *.deb || echo 'dpkg warnings/errors are common. Will try to fix later.'\n")
        f.write("f.write("echo \"  Attempting to fix broken installs. (This will only work if all dependencies *are* present otherwise it will fail.)\"\n")
        # f.write("f.write("sudo apt --fix-broken install\n") # This requires internet
        f.write("echo \"*** IMPORTANT: If any package installation failed due to dependencies, try installing them manually in correct order or locate missing DEBs. ***\"\n")
        f.write("echo \"  Consider a brief internet connection for 'sudo apt update && sudo apt install -f' if stuck, then go offline again.\"\n")
        f.write("echo \"  Press ENTER to continue.\"\n")
        f.write("f.write("read dummy)\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        if GPU_TYPE == "nvidia":
            f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("echo \"STEP 2: Install NVIDIA Drivers and CUDA Toolkit (offline).\"\n")
            f.write("echo \"  This will install the CUDA local repository and then the toolkit.\"\n")
            f.write("f.write("cd ${OFFLINE_SETUP_DIR}/nvidia_cuda || { echo 'Error: Missing nvidia_cuda directory.'; exit 1; }\n")
            f.write("f.write("LOCAL_CUDA_DEB=$(find . -name 'cuda-repo-ubuntu*.deb' | head -n 1)\n")
            f.write("f.write("if [ -z \"$LOCAL_CUDA_DEB\" ]; then echo 'No CUDA local deb found. Skipping CUDA installation.'; else sudo dpkg -i $LOCAL_CUDA_DEB; fi\n")
            f.write("f.write("echo \"  Attempting to update apt. (Expect warnings about not being able to fetch remote repos)\"\n")
            f.write("f.write("sudo apt update || echo 'apt update failed (as expected, no internet). Proceeding.'\n")
            f.write("f.write("echo \"  Installing CUDA toolkit (this installs from the local deb repo).\"\n")
            f.write(f"f.write(\"sudo apt install -y cuda-toolkit-{CUDA_VERSION.replace('.', '-')}\"\n") # Install specific CUDA version
            f.write("f.write("echo \"  Installing general CUDA package for convenience (may pull more if available).\"\n")
            f.write("f.write("sudo apt install -y cuda\n")
            f.write("f.write("echo \"  Installing cuDNN (manual copy). You MUST have downloaded the tarball.\"\n")
            f.write("f.write("CUDNN_TAR=$(find . -name 'cudnn-*-cuda*.tgz' -o -name 'cudnn-*-cuda*.tar.xz' | head -n 1)\n")
            f.write("f.write("if [ -z \"$CUDNN_TAR\" ]; then echo 'No cuDNN tarball found. Skipping cuDNN installation.'; else\n")
            f.write("f.write("  tar -xf \"$CUDNN_TAR\"\n")
            f.write("f.write("  sudo cp -P cuda/include/* /usr/local/cuda/include/\n")
            f.write("f.write("  sudo cp -P cuda/lib/lib64/* /usr/local/cuda/lib64/\n")
            f.write("f.write("  sudo chmod a+r /usr/local/cuda/include/cudnn.h /usr/local/cuda/lib64/libcudnn*\n")
            f.write("fi\n")
            f.write("f.write("echo \"  Verifying NVIDIA installation...\"\n")
            f.write("f.write("nvidia-smi\n")
            f.write("f.write("nvcc --version\n")
            f.write("f.write("echo \"  Add CUDA to PATH and LD_LIBRARY_PATH (add to ~/.bashrc for permanent).\"\n")
            f.write("f.write("sudo sh -c 'echo \"export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}\" >> /etc/profile.d/cuda.sh'\n")
            f.write("f.write("sudo sh -c 'echo \"export LD_LIBRARY_PATH=/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}\" >> /etc/profile.d/cuda.sh'\n")
            f.write("f.write("source /etc/profile.d/cuda.sh\n")
            f.write("f.write("echo \"*** IMPORTANT: YOU MAY NEED TO REBOOT YOUR SYSTEM FOR DRIVERS TO TAKE EFFECT! ***\"\n")
            f.write("echo \"  After reboot, run `nvidia-smi` to confirm drivers are working.\"\n")
            f.write("echo \"  Press ENTER to continue.\"\n")
            f.write("f.write("read dummy)\n")
            f.write("echo \"-------------------------------------------------------------------\"\n")
            f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 3: Install Miniconda (offline).\"\n")
        f.write("f.write("cd ${OFFLINE_SETUP_DIR}/miniconda || { echo 'Error: Missing miniconda directory.'; exit 1; }\n")
        f.write("BASE_MINICONDA_INSTALL_DIR=\"$HOME/miniconda3\"\n")
        f.write("f.write("bash Miniconda3-latest-Linux-x86_64.sh -b -p ${BASE_MINICONDA_INSTALL_DIR}\n")
        f.write("f.write("echo \"  Initializing Conda. You will need to restart your terminal or 'source ~/.bashrc'.\"\n")
        f.write("f.write("${BASE_MINICONDA_INSTALL_DIR}/bin/conda init\n")
        f.write("f.write("source ~/.bashrc # For this session\n")
        f.write("f.write("echo \"  Press ENTER to continue (after restarting your terminal or sourcing ~/.bashrc).\n")
        f.write("echo \"  You should see (base) in your prompt.\"\n")
        f.write("f.write("read dummy)\n")
        f.write("f.write("source ${BASE_MINICONDA_INSTALL_DIR}/etc/profile.d/conda.sh # Ensure conda is activated for script\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 4: Create Conda environment and install Python packages (offline).\"\n")
        f.write("f.write("conda create -n ai_env python=${PYTHON_VERSION} -y\n")
        f.write("f.write("conda activate ai_env\n")
        f.write("f.write("echo \"  Installing PyTorch.\"\n")
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/pytorch\" torch torchvision torchaudio\n")
        # Optional: TensorFlow
        f.write("f.write("echo \"  Installing TensorFlow (optional, if downloaded).\"\n")
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/tensorflow\" tensorflow || echo 'TensorFlow install failed. Skipping if not needed.'\n")
        
        # Bitsandbytes and xformers often need specific compilation or wheels
        f.write("f.write("echo \"  Installing remaining common AI libraries.\"\n")
        # Try to install specific ones first with preferred options.
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" bitsandbytes || echo 'bitsandbytes install a common issue. If it fails, manual build might be needed.'\n")
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" flash-attn || echo 'flash-attn install a common issue. If it fails, manual build might be needed.'\n")
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" xformers || echo 'xformers install a common issue. If it fails, manual build might be needed.'\n")
        # Install the rest
        f.write("f.write("pip install --no-index --find-links=\"${OFFLINE_SETUP_DIR}/python_packages/common_libs\" $(ls ${OFFLINE_SETUP_DIR}/python_packages/common_libs/*.whl | xargs -n 1 basename | sed 's/\(.*\)-\([0-9.]*\)-py.\+/\1/g' | uniq | grep -vE '^(torch|tensorflow|bitsandbytes|flash-attn|xformers)$' | tr '\\n' ' ')\n")
        f.write("f.write("echo \"  Verifying PyTorch CUDA installation.\"\n")
        f.write("f.write("python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}'); if torch.cuda.is_available(): print(f'GPU: {torch.cuda.get_device_name(0)}')\"\n")
        f.write("f.write("echo \"  Press ENTER to continue.\"\n")
        f.write("f.write("read dummy)\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")
        
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 5: Prepare Git Repositories and AI Models.\"\n")
        f.write("f.write("echo \"  This step involves copying pre-downloaded Git repos and models.\"\n")
        f.write("f.write("echo \"  You may need to manually move specific model files (e.g., .safetensors checkpoints) to the correct subdirectories within each UI's 'models' folder.\"\n")
        f.write("f.write("cd ${OFFLINE_SETUP_DIR}/git_repos || { echo 'Error: Missing git_repos directory.'; exit 1; }\n")
        f.write("f.write("echo \"  Git clones are already done. No action needed here.\"\n")
        f.write("f.write("\n")
        f.write("f.write("echo \"  Copying pre-downloaded AI Models to AI_MODELS_PATH for organization. You'll link them where needed.\"\n")
        f.write("f.write("cp -r ${OFFLINE_SETUP_DIR}/ai_models/* ${AI_MODELS_PATH} || echo 'Could not copy all models. Verify structure.'\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"STEP 6: Launching AI Applications (Examples).\"\n")
        f.write("f.write("echo \"  Ensure your Conda 'ai_env' is activated before running these commands!\"\n")
        f.write("f.write("echo \"  To activate: conda activate ai_env\"\n")
        f.write("f.write("echo \"  Then navigate to the application's directory and run the command.\"\n")
        f.write("\n")
        
        if DOWNLOAD_LLM_WEBUI:
            f.write("f.write("echo \"  --- Text Generation WebUI (Oobabooga) ---\"\n")
            f.write("f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/text-generation-webui/models/\"\n")
            f.write("f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/text-generation-webui\"\n")
            f.write("f.write("echo \"  python server.py --listen --share # Add your model flags like --model <model_name> --n-gpu-layers <num>\"\n")
            f.write("f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("f.write("echo \"  Access at http://localhost:7860 (or given share URL)\"\n")
            f.write("\n")
        
        if DOWNLOAD_STABLE_DIFFUSION_WEBUI:
            f.write("f.write("echo \"  --- Automatic1111 Stable Diffusion WebUI ---\"\n")
            f.write("f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/stable-diffusion-webui/models/Stable-diffusion/\"\n")
            f.write("f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/stable-diffusion-webui\"\n")
            f.write("f.write("echo \"  python launch.py --listen --xformers --enable-insecure-extension-access --no-download-clip --skip-install # Or other suitable flags\"\n")
            f.write("f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("f.write("echo \"  Access at http://localhost:7860\"\n")
            f.write("\n")

        if DOWNLOAD_COMFYUI:
            f.write("f.write("echo \"  --- ComfyUI ---\"\n")
            f.write("f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/comfyui/models/checkpoints/ (and other subfolders)\"\n")
            f.write("f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/comfyui\"\n")
            f.write("f.write("echo \"  python main.py --listen --cuda-device 0\"\n")
            f.write("f.write("echo \"  (Initial run might re-configure, ignore internet errors)\"\n")
            f.write("f.write("echo \"  Access at http://localhost:8188\"\n")
            f.write("\n")

        if DOWNLOAD_LLAMACPP:
            f.write("f.write("echo \"  --- llama.cpp (CLI LLM inference) ---\"\n")
            f.write("f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/llama.cpp\"\n")
            f.write("f.write("echo \"  make LLAMA_CUBLAS=1 # (for NVIDIA GPU acceleration)\"\n")
            f.write("f.write("echo \"  Models go in ${OFFLINE_SETUP_DIR}/git_repos/llama.cpp/models/\"\n")
            f.write("f.write("echo \"  Example: ./main -m models/your-model.gguf -p 'Hello World' -n 128\"\n")
            f.write("\n")
            
        if DOWNLOAD_WHISPERCPP:
            f.write("f.write("echo \"  --- whisper.cpp (CLI ASR) ---\"\n")
            f.write("f.write("echo \"  cd ${OFFLINE_SETUP_DIR}/git_repos/whisper.cpp\"\n")
            f.write("f.write("echo \"  make -j\"\n")
            f.write("f.write("echo \"  FFmpeg needed for audio formats beyond WAV: sudo apt install ffmpeg\"\n")
            f.write("f.write("echo \"  Download GGML models (e.g., from ggerganov/whisper.cpp Hugging Face) and place in models/\"\n")
            f.write("f.write("echo \"  Example: ./main -m models/ggml-large-v3.bin -f /path/to/your/audio.wav\"\n")
            f.write("\n")

        f.write("echo \"-------------------------------------------------------------------\"\n")
        f.write("echo \"Setup complete! Remember to manually move models into app-specific directories.\"\n")
        f.write("echo \"For permanent environment variables (like CUDA PATH), add them to ~/.bashrc and source it.\"\n")
        f.write("echo \"Good luck with your offline AI adventures!\"\n")
        f.write("echo \"-------------------------------------------------------------------\"\n")

    os.chmod(script_path, 0o755) # Make the script executable
    print(f"\nOffline installation script generated: {script_path}")
    print("Transfer this entire `--ai_offline_setup` directory to your target Ubuntu machine!")
    print("On the target machine, copy it to `/opt/` (e.g., `sudo cp -r <USB_DRIVE>/ai_offline_setup /opt/`)")
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
    
    # Prompt for CUDA version if NVIDIA is selected
    if GPU_TYPE == "nvidia":
        global CUDA_VERSION, PYTORCH_CUDA_STR
        user_cuda = input(f"Enter desired NVIDIA CUDA version (e.g., 11.8 or 12.1, current: {CUDA_VERSION}): ")
        if user_cuda:
            CUDA_VERSION = user_cuda
            PYTORCH_CUDA_STR = f"cu{CUDA_VERSION.replace('.', '')}"
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
    print("Now, transfer the entire `/ai_offline_setup` directory to your offline Ubuntu machine.")
    print(f"On the offline machine, run `{os.path.join(SCRIPTS_PATH, 'install_offline_ai.sh')}` step-by-step.")

if __name__ == "__main__":
    main()