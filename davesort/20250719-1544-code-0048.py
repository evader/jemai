# CUDA_VERSION and PYTORCH_CUDA_STR are used for PyTorch/TF compatibility
CUDA_VERSION = "12.9.1" # Keep this as it matches your .run installer
# For PyTorch, we need a string that matches PyTorch's available wheels.
# PyTorch typically bundles 12.1, 12.2. Let's use 12.1 which is widely available for recent PyTorch.
PYTORCH_CUDA_STR = "cu121" # <--- Change this to an actual PyTorch CUDA string