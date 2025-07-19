try:
        import huggingface_hub
    except ImportError:
        print("huggingface_hub not found. This should have been installed. Trying to install now...")
        run_command([sys.executable, "-m", "pip", "install", "huggingface_hub"], check=False)