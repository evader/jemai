# In download_nvidia_drivers_cuda_cudnn():
# Find the actual size in bytes from NVIDIA's site
cuda_run_file_expected_size = 6271927702 # Example: Replace with actual size from NVIDIA's download page for 12.9.1 run file
download_file(cuda_installer_url, os.path.join(NVIDIA_CUDA_PATH, cuda_installer_filename), expected_size=cuda_run_file_expected_size)