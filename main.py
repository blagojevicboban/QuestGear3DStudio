import flet as ft
from modules.gui import main as gui_main

def main():
    print("Application starting...")
    # Using ft.app() for Flet 0.26.0 compatibility, enabling assets for 3D viewer
    ft.app(target=gui_main, assets_dir="assets")

if __name__ == "__main__":
    main()
