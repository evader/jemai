# cluster_update.py
import os, sys, time, socket, threading, zipfile, shutil, platform, http.server
from pathlib import Path

CLUSTER_UPDATE_PORT = 8791
UPDATE_TOKEN = "jemai_cluster_update"  # simple shared secret

def zip_dir(src_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for f in files:
                p = os.path.join(root, f)
                arc = os.path.relpath(p, src_dir)
                z.write(p, arc)

def unzip_dir(zip_path, dst_dir):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dst_dir)

def serve_update(zip_path, port=CLUSTER_UPDATE_PORT):
    class UpdateHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/update.zip?token="+UPDATE_TOKEN:
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.end_headers()
                with open(zip_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_response(404)
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), UpdateHandler)
    print(f"[CLUSTER] Update server ready at :{port}/update.zip")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def fetch_update(ip, port=CLUSTER_UPDATE_PORT, dst="update.zip"):
    import urllib.request
    url = f"http://{ip}:{port}/update.zip?token={UPDATE_TOKEN}"
    print(f"[CLUSTER] Fetching update from {url}")
    urllib.request.urlretrieve(url, dst)
    print("[CLUSTER] Update downloaded.")

def announce_update(ip, port=CLUSTER_UPDATE_PORT):
    # UDP broadcast to tell others about update
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = f"JEMAI_UPDATE:{ip}:{port}:{UPDATE_TOKEN}"
    sock.sendto(msg.encode("utf-8"), ("<broadcast>", 6789))
    sock.close()
    print("[CLUSTER] Update announcement sent.")

def apply_update(zipfile_path, code_dir):
    # Backup, replace, restart
    backup = code_dir+"_backup_"+time.strftime("%Y%m%d%H%M%S")
    shutil.copytree(code_dir, backup)
    unzip_dir(zipfile_path, code_dir)
    print(f"[CLUSTER] Code updated. Backup at {backup}. Restarting...")
    # This will depend on your system; for now, just restart Python
    os.execv(sys.executable, [sys.executable] + sys.argv)

def start_update_listener(code_dir):
    def listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", 6789))
        while True:
            data, addr = sock.recvfrom(65536)
            msg = data.decode("utf-8", errors="replace")
            if msg.startswith("JEMAI_UPDATE:"):
                parts = msg.strip().split(":")
                if len(parts) == 4 and parts[3] == UPDATE_TOKEN:
                    _, ip, port, _ = parts
                    try:
                        fetch_update(ip, int(port), "update.zip")
                        apply_update("update.zip", code_dir)
                    except Exception as e:
                        print(f"[CLUSTER] Update failed: {e}")
    threading.Thread(target=listener, daemon=True).start()
