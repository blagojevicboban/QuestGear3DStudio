import flet as ft
import asyncio

async def main(page: ft.Page):
    print(f"FilePicker MRO: {ft.FilePicker.__mro__}")
    try:
        fp = ft.FilePicker()
        print(f"FilePicker instance: {fp}")
        print(f"FilePicker methods: {[x for x in dir(fp) if not x.startswith('_')]}")
    except Exception as e:
        print(f"FilePicker init error: {e}")
    await page.window_close_async()

if __name__ == "__main__":
    ft.run(main)
