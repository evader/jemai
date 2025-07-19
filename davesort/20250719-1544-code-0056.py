def download_python_packages():
    """Downloads all Python packages using pip download."""
    print("Downloading Python packages...")

    common_pip_packages = [
        "transformers", "accelerate", "safetensors", "datasets", "trl", "xformers",
        "onnxruntime", "sentencepiece", "tokenizers", "optimum", "jupyter", "matplotlib",
        "scikit-learn", "scipy", "notebook", "rich", "ipywidgets", "tabulate",
        # "flash-attn", # <--- REMOVE THESE FROM THIS LIST (we'll try separately or rely on offline build)
        # "bitsandbytes", # <--- REMOVE THESE FROM THIS LIST
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
    
    # Install huggingface_hub so we can use huggingface-cli later.
    # We install it here because it might be needed by other packages for metadata.
    # It must be installed *into* the temp venv where pip will be run.
    run_command([pip_executable, "install", "huggingface_hub"])


    # ===== 1. PyTorch (with CUDA) - FIRST to ensure torch is available for others =====
    print("\n--- Downloading PyTorch and related packages ---")
    torch_version = "2.3.1"
    torchvision_version = "0.18.1"
    torchaudio_version = "2.3.1"

    torch_packages = [
        f"torch=={torch_version}+{PYTORCH_CUDA_STR}",
        f"torchvision=={torchvision_version}+{PYTORCH_CUDA_STR}",
        f"torchaudio=={torchaudio_version}+{PYTORCH_CUDA_STR}",
    ]
    pytorch_extra_index_url = f"https://download.pytorch.org/whl/{PYTORCH_CUDA_STR}"
    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "pytorch"), 
                 "--extra-index-url", pytorch_extra_index_url] + torch_packages)

    # ===== 2. TensorFlow (if desired, make sure CUDA version compatibility) - SECOND =====
    print("\n--- Downloading TensorFlow (optional) ---")
    tf_packages = ["tensorflow[and-cuda]==2.19.0"] # Use the version you just determined
    try:
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "tensorflow")] + tf_packages)
    except Exception:
        print("Skipping TensorFlow download due to potential issues or if not explicitly needed.")
        print("If you need it, verify exact versions and try again.")
        

    # ===== 3. Common AI Libraries (excluding flash-attn/bitsandbytes for now) =====
    print("\n--- Downloading Common AI Libraries (excluding problematic ones) ---")
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
        "resize-right", "torchmetrics", "clip", "open_clip_torch", # k-diffusion may use torch for metadata/build
        "exifread", "piexif", "send2trash", "pyyaml", "mediapipe", "facexlib", "gfpgan", "realesrgan",
        "basicsr", "gradio==3.32.0", # A1111 often pins gradio. Check their webui-user.bat/sh
    ]
        
    all_common_packages = list(set(common_pip_packages + oobabooga_deps + sd_deps))

    run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs")] + all_common_packages)
    
    # ===== 4. Attempt to download flash-attn and bitsandbytes separately =====
    # These often require specific pre-compiled wheels or careful source compilation
    # for full CUDA integration. For offline mode, this is very tricky.
    
    print("\n--- Attempting to download flash-attn (may fail, often requires manual build) ---")
    try:
        # `--no-binary :all:` forces it to try source or specific platform wheels, not generic ones.
        # This is often needed for flash-attn with CUDA builds.
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "flash-attn", "--no-binary", ":all:"])
    except Exception as e:
        print(f"Warning: Failed to download flash-attn. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")

    print("\n--- Attempting to download bitsandbytes (may fail, often requires manual wheel) ---")
    try:
        # Also often needs --no-binary :all: or very specific pre-built wheels
        run_command([pip_executable, "download", "-d", os.path.join(PYTHON_PACKAGES_PATH, "common_libs"), "bitsandbytes", "--no-binary", ":all:"])
    except Exception as e:
        print(f"Warning: Failed to download bitsandbytes. This often indicates a complex build requirement. Error: {e}")
        print("You may need to manually download pre-compiled wheels from their GitHub releases or build during offline installation.")


    # Cleanup temporary venv
    print("Cleaning up temporary pip download environment...")
    run_command(["rm", "-rf", temp_venv_path])

    print("Finished downloading Python packages.")