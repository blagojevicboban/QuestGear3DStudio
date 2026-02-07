import flet as ft
import asyncio

async def main(page: ft.Page):
    async def pick_click(e):
        # In Flet 1.0, pick_files is async and returns the result
        files = await page.pick_files(
            dialog_title="Test Pick",
            allowed_extensions=["zip"]
        )
        if files:
            print(f"Picked: {files[0].path}")
        else:
            print("Cancelled")

    page.add(ft.ElevatedButton("Pick File", on_click=pick_click))
    print("UI Ready")

ft.run(main)
