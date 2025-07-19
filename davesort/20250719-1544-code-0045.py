def download_nvidia_drivers_cuda_cudnn():
    """Downloads NVIDIA CUDA Toolkit .run installer and cuDNN."""
    if GPU_TYPE != "nvidia":
        print("Skipping NVIDIA downloads as GPU_TYPE is not 'nvidia'.")
        return

    print("Downloading NVIDIA CUDA Toolkit and cuDNN...")

    # Using the .run file installer, which is often more reliable
    # Found this example: https://developer.nvidia.com/cuda/12.9.1/local_installers/cuda_12.9.1_575.57.08_linux.run
    # You MUST verify this URL still works on NVIDIA's website!
    # Go to: https://developer.nvidia.com/cuda-downloads
    # Select: Linux -> x86_64 -> Ubuntu -> 24.04 (Noble) -> runfile (local)
    
    cuda_installer_url = f"https://developer.download.nvidia.com/compute/cuda/{CUDA_VERSION}/local_installers/cuda_{CUDA_VERSION}_575.57.08_linux.run"

    # IMPORTANT: The 575.57.08 driver version is specific to CUDA 12.9.1.
    # If the CUDA_VERSION changes, you must update this driver version here!
    # Better to manually find the exact URL from NVIDIA's site for the CUDA version you want.
    
    # For now, let's hardcode the URL you found, as it's proven to exist:
    cuda_installer_url = "https://developer.download.nvidia.com/compute/cuda/12.9.1/local_installers/cuda_12.9.1_575.57.08_linux.run"
    cuda_installer_filename = os.path.basename(cuda_installer_url)

    print(f"Attempting to download CUDA Toolkit .run file: {cuda_installer_url}")
    download_file(cuda_installer_url, os.path.join(NVIDIA_CUDA_PATH, cuda_installer_filename))

    # Download cuDNN (requires NVIDIA Developer Program account and login)
    # This is still a manual step.
    print("\nFor cuDNN, you must download it manually from https://developer.nvidia.com/rdp/cudnn-download-survey")
    print(f"Place the cuDNN `tar.xz` or `tgz` file for CUDA {CUDA_VERSION} in: {NVIDIA_CUDA_PATH}")
    print("Example filename: cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz (adjust for your CUDA version)")
    print("You will install it later by extracting and copying to /usr/local/cuda.")

    print("Finished NVIDIA CUDA/cuDNN instructions. Don't forget cuDNN manual download.")