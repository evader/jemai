import os
from pystray import Icon as TrayIcon, MenuItem as item
from PIL import Image
from ..config import JEMAI_HUB

def get_icon_image():
    """
    Tries to load an icon from 'assets/icon.png', otherwise creates a default one.
    """
    try:
        # Assumes you have an 'assets' folder in your JEMAI_HUB with 'icon.png'
        icon_path = os.path.join(JEMAI_HUB, "assets", "icon.png")
        return Image.open(icon_path)
    except (FileNotFoundError, IOError):
        # Create a dummy image if icon.png is not found
        width = 64
        height = 64
        color1 = (20, 20, 80)  # Dark Blue
        color2 = (70, 180, 255)  # Light Blue
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.ellipse([(width // 4, height // 4), (width * 3 // 4, height * 3 // 4)], fill=color2)
        return image

def exit_action(icon, item):
    icon.stop()
    os._exit(0)  # Force exit for all threads

def create_tray_icon():
    """
    Creates and runs the system tray icon. This is a blocking call.
    """
    # Use the helper function to get the icon image
    image = get_icon_image()

    menu = (item('Exit JEMAI', exit_action),)
    icon = TrayIcon("JEMAI", image, "JEMAI Mission Control", menu)

    # This is a blocking call and should be run in a dedicated thread
    # so it doesn't block the rest of the application.
    icon.run()
