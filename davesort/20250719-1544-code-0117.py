# Use a recent PyTorch version compatible with PYTORCH_CUDA_STR (e.g., cu121)
    # Check https://pytorch.org/get-started/locally/ for the latest stable version
    torch_version = "2.3.1" 
    torchvision_version = "0.18.1"
    torchaudio_version = "2.2.0" # <--- Change torchaudio to 2.2.0

    # Note: Sometimes, specific combinations are tricky. If 2.2.0 still fails for torchaudio,
    # we might need to use PyTorch 2.2.2 or similar, then check for torchaudio 0.17.2 or 2.2.2.
    # But this combination (torch 2.3.1, torchvision 0.18.1, torchaudio 2.2.0) is a commonly working one
    # with cu121.