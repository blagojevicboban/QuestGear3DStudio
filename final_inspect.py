import flet as ft
import asyncio
import inspect

async def main(page: ft.Page):
    print(f"Flet version: {ft.__version__}")
    print(f"Page.update is coroutine: {inspect.iscoroutinefunction(page.update)}")
    
    fp = ft.FilePicker()
    print(f"FilePicker class: {type(fp)}")
    print(f"FilePicker.pick_files is coroutine: {inspect.iscoroutinefunction(fp.pick_files)}")
    
    # Try to add it to overlay
    try:
        page.overlay.append(fp)
        print("Added FilePicker to overlay")
    except Exception as e:
        print(f"Error adding to overlay: {e}")
    
    await page.window_close_async()

if __name__ == "__main__":
    ft.run(main)
