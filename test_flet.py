import flet as ft

def main(page: ft.Page):
    fp = ft.FilePicker()
    page.overlay.append(fp)
    page.add(ft.Text("Testing FilePicker..."))
    page.update()

ft.run(main)
