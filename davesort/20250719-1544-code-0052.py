def download_file(url, target_path):
    """Downloads a file from a URL, skipping if it already exists."""
    if os.path.exists(target_path):
        print(f"File already exists: {target_path}. Skipping download.")
        return True # Indicate success
    
    print(f"Downloading {url} to {target_path}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded {target_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        # Clean up partially downloaded file if it exists
        if os.path.exists(target_path):
            os.remove(target_path)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        if os.path.exists(target_path):
            os.remove(target_path)
        sys.exit(1)