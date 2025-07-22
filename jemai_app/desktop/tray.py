import os
from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw

def get_icon_image():
    try:
        # Try loading your actual icon (if it exists)
        icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'icon.png')
        icon_path = os.path.abspath(icon_path)
        print(f"Trying to load icon from: {icon_path}")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            raise FileNotFoundError
    except Exception as e:
        print(f"[tray.py] Using fallback icon due to: {e}")
        # Fallback: simple blue circle
        size = 64
        color1 = (20, 20, 80)
        color2 = (70, 180, 255)
        image = Image.new('RGB', (size, size), color1)
        dc = ImageDraw.Draw(image)
        dc.ellipse((size//8, size//8, size*7//8, size*7//8), fill=color2)
        return image

def on_exit(icon, _):
    icon.stop()
    os._exit(0)  # Optional: force all threads to die

def create_tray_icon():
    print("[tray.py] Starting create_tray_icon()")
    image = get_icon_image()
    menu = (item('Exit JEMAI', on_exit),)
    icon = Icon("JEMAI", image, "JEMAI Mission Control", menu)
    print("[tray.py] Running icon...")
    icon.run()
