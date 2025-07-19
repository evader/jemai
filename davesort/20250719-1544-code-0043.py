if CUDA_VERSION == "12.4" and UBUNTU_VERSION == "24.04":
        cuda_installer_url = "https://developer.nvidia.com/downloads/cuda/12.4.1/local_installers/cuda-repo-ubuntu2404-12-4-local_12.4.1-1_amd64.deb"
    # Ensure this check is *before* the 11.8/12.1 checks if you want 12.4 to be default for 24.04
    # ... (other existing 'elif' blocks)
    elif CUDA_VERSION == "11.8" and UBUNTU_VERSION == "22.04":
        cuda_installer_url = "https://developer.nvidia.com/downloads/cuda/11.8.0/local_installers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb"
    elif CUDA_VERSION == "12.1" and UBUNTU_VERSION == "22.04":
         cuda_installer_url = "https://developer.nvidia.com/downloads/cuda/12.1.0/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb"
    else:
        print(f"Warning: CUDA {CUDA_VERSION} for Ubuntu {UBUNTU_VERSION} not hardcoded or URL not found. Please manually download from NVIDIA and place in {NVIDIA_CUDA_PATH}.")
        print("Skipping automatic CUDA .deb download.")
        print("You'll need to manually ensure it includes the CUDA toolkit and drivers for offline installation.")
        cuda_installer_url = None