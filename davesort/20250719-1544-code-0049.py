# ===== 1. PyTorch (with CUDA) =====
    print("\n--- Downloading PyTorch and related packages ---")
    
    # Use a recent PyTorch version compatible with cu121
    # Check https://pytorch.org/get-started/locally/ for the latest stable version
    torch_version = "2.3.1" # <--- Update this to a version compatible with PyTorch's cu121 wheels
    torchvision_version = "0.18.1" # <--- Corresponding torchvision version
    torchaudio_version = "2.3.1" # <--- Corresponding torchaudio version

    torch_packages = [
        f"torch=={torch_version}+{PYTORCH_CUDA_STR}",
        f"torchvision=={torchvision_version}+{PYTORCH_CUDA_STR}",
        f"torchaudio=={torchaudio_version}+{PYTORCH_CUDA_STR}",
    ]
    pytorch_extra_index_url = f"https://download.pytorch.org/whl/{PYTORCH_CUDA_STR}"
    
    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "pytorch"), 
                 "--extra-index-url", pytorch_extra_index_url] + torch_packages)