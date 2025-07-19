if __name__ == "__main__":
  print("--- Starting Local Lieutenant v13.0 (Server Only) ---")
  if not os.path.isdir('templates'):
    print("CRITICAL ERROR: 'templates' directory not found. Please create it and place index.html inside.", file=sys.stderr)
    sys.exit(1) # <-- This is where it exits if 'templates' is missing
  app.run(host='0.0.0.0', port=5000) # This should now be 5001 internally