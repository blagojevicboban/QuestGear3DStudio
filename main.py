import flet as ft
from modules.gui import main as gui_main

def main():
    print("Application starting...")
    # Using ft.app() for Flet 0.26.0 compatibility
    ft.app(target=gui_main)

if __name__ == "__main__":
    main()
