# CUDA_VERSION and PYTORCH_CUDA_STR are used for PyTorch/TF compatibility
CUDA_VERSION = "12.9.1" # <--- Update this to match your .run file
PYTORCH_CUDA_STR = f"cu{CUDA_VERSION.replace('.', '')}" # This will become cu1291