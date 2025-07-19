# AT THE TOP OF YOUR SCRIPT:
    CUDA_VERSION = "12.9.1" # Matches your .run installer
    PYTORCH_CUDA_STR = "cu121" # PyTorch's string for CUDA 12.1+ wheels

    # WITHIN download_python_packages() FUNCTION:
    torch_version = "2.3.1"
    torchvision_version = "0.18.1"
    torchaudio_version = "2.3.1"