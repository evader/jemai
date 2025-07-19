def download_file(url, target_path, expected_size=None):
    """Downloads a file from a URL, skipping if it already exists."""
    if os.path.exists(target_path):
        current_size = os.path.getsize(target_path)
        if expected_size and current_size == expected_size:
            print(f"File already exists and size matches: {target_path} ({current_size} bytes). Skipping download.")
            return True
        else:
            print(f"File already exists: {target_path} ({current_size} bytes). Re-downloading just in case, or size mismatch.")
            # If size mismatches or expected_size is not provided, proceed to re-download.
            # You could add an input() here to ask the user if they want to re-download.
            os.remove(target_path) # Remove incomplete/old file before re-download
    
    print(f"Downloading {url} to {target_path}...")
    try:
        # Added stream=True and iter_content for large files to avoid loading entire file into memory
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            total_size = int(r.headers.get('content-length', 0))
            if expected_size and total_size != expected_size:
                print(f"Warning: Downloaded file size ({total_size}) does not match expected size ({expected_size}).")
            
            with open(target_path, 'wb') as f:
                # Add a progress bar (optional, but nice for large files)
                try:
                    from tqdm import tqdm
                    # Wrap the iterator with tqdm for a progress bar
                    for chunk in tqdm(r.iter_content(chunk_size=8192), total=total_size // 8192, unit='KB', desc="Downloading"):
                        f.write(chunk)
                except ImportError:
                    # Fallback if tqdm is not installed
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        print(f"Downloaded {target_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        # Clean up partially downloaded file
        if os.path.exists(target_path):
            os.remove(target_path)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        if os.path.exists(target_path):
            os.remove(target_path)
        sys.exit(1)