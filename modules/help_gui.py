"""
Help GUI Module for QuestGear 3D Studio.
Provides a dedicated tab with instructions and documentation in multiple languages.
"""

import flet as ft

class HelpUI:
    """Manages the Help tab and documentation display with multi-language support."""
    
    TRANSLATIONS = {
        "en": {
            "tab_title": "Help",
            "welcome_title": "QuestGear 3D Studio",
            "welcome_subtitle": "Your center for creating premium 3D models from Meta Quest 3 scans.",
            "main_processes": "Main Processes",
            "step1_title": "1. Data Import",
            "step1_content": "Transfer recorded data from Meta Quest 3 to your computer. You can load a .zip archive directly from the QuestGear 3D Scan app or a data folder.\n• Use 'Load ZIP' for original archives.\n• Use 'Load Folder' for already extracted data.",
            "step2_title": "2. TSDF Reconstruction (Fast)",
            "step2_content": "The fastest way to get a textured 3D mesh. Uses depth maps recorded by the sensor.\n• Adjust 'Voxel Size' (smaller = more detailed, but slower).\n• 'Max Depth' limits how far the sensor 'sees'.\n• Export to .OBJ or .GLB for use in 3D software.",
            "step3_title": "3. NerfStudio / Splatting (Photorealistic)",
            "step3_content": "For top-quality models without visible noise.\n• Splatfacto: Uses Gaussian Splatting for instant rendering.\n• Nerfacto: Standard NeRF for precise geometries.\n• Note: Requires an NVIDIA graphics card (CUDA).",
            "faq_title": "Frequently Asked Questions (FAQ)",
            "q1_title": "Why is the model dark or has holes?",
            "q1_subtitle": "Tips for lighting and coverage",
            "q1_content": "Check if the room is sufficiently lit. The depth sensor on Quest works best in uniform light conditions. Holes occur if a part of the object was not visible from multiple angles.",
            "q2_title": "Which format is best for Blender/Unity?",
            "q2_subtitle": "Export recommendations",
            "q2_content": ".OBJ is the most universal, but .GLB (glTF) is best for web, AR, and modern engines like Unity as it preserves textures and materials in a single file.",
            "q3_title": "NerfStudio won't start?",
            "q3_subtitle": "Installation troubleshooting",
            "q3_content": "Make sure you have the latest NVIDIA drivers and Visual Studio Redistributable installed. Check the logs at the bottom of the app for specific errors during installation.",
            "credits": "2026 QuestGear 3D Suite | Developed by Mejkerslab",
            "version": "Version 2.1.0-stable"
        },
        "sr": {
            "tab_title": "Pomoć",
            "welcome_title": "QuestGear 3D Studio",
            "welcome_subtitle": "Vaš centar za kreiranje vrhunskih 3D modela iz Meta Quest 3 snimaka.",
            "main_processes": "Glavni Procesi",
            "step1_title": "1. Uvoz Podataka (Import)",
            "step1_content": "Prebacite snimljene podatke sa Meta Quest 3 na računar. Možete učitati .zip arhivu direktno iz QuestGear 3D Scan aplikacije ili folder sa podacima.\n• Koristite 'Load ZIP' za originalne arhive.\n• Koristite 'Load Folder' za već otpakovane podatke.",
            "step2_title": "2. TSDF Rekonstrukcija (Brza)",
            "step2_content": "Najbrži način da dobijete 3D mesh sa teksturom. Koristi dubinske mape snimljene senzorom.\n• Podesite 'Voxel Size' (manje = detaljnije, ali sporije).\n• 'Max Depth' ograničava koliko daleko senzor 'vidi'.\n• Eksportujte u .OBJ ili .GLB za korišćenje u 3D softverima.",
            "step3_title": "3. NerfStudio / Splatting (Fotorealistično)",
            "step3_content": "Za modele vrhunskog kvaliteta bez vidljivih šumova.\n• Splatfacto: Koristi Gaussian Splatting za trenutni rendering.\n• Nerfacto: Standardni NeRF za precizne geometrije.\n• Napomena: Zahteva NVIDIA grafičku karticu (CUDA).",
            "faq_title": "Često Postavljana Pitanja (FAQ)",
            "q1_title": "Zašto je model taman ili ima rupe?",
            "q1_subtitle": "Saveti za osvetljenje i pokrivanje",
            "q1_content": "Proverite da li je prostorija dovoljno osvetljena. Senzor dubine na Questu najbolje radi u uslovima ravnomernog svetla. Rupe nastaju ako neki deo objekta nije bio vidljiv iz više uglova.",
            "q2_title": "Koji format je najbolji za Blender/Unity?",
            "q2_subtitle": "Preporuke za eksport",
            "q2_content": ".OBJ je najuniverzalniji, ali .GLB (glTF) je najbolji za web, AR i moderne engine kao što je Unity jer čuva teksture i materijale u jednom fajlu.",
            "q3_title": "NerfStudio se ne pokreće?",
            "q3_subtitle": "Rešavanje problema sa instalacijom",
            "q3_content": "Uverite se da imate instalirane najnovije NVIDIA drajvere i Visual Studio Redistributable. Proverite logove u donjem delu aplikacije za specifične greške tokom instalacije.",
            "credits": "2026 QuestGear 3D Suite | Razvijeno od strane Mejkerslab-a",
            "version": "Verzija 2.1.0-stable"
        }
    }
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.lang = "en" # Default
        self.container = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self.tab = ft.Tab(
            text="Pomoć",
            icon=ft.Icons.HELP_CENTER,
            content=ft.Container(
                content=self.container,
                padding=20,
                expand=True
            )
        )
        self.update_ui()

    def update_ui(self):
        """Update the Help UI components based on selected language."""
        t = self.TRANSLATIONS[self.lang]
        
        self.tab.text = t["tab_title"]
        self.container.controls.clear()
        
        # Language Selector
        self.container.controls.append(
            ft.Row([
                ft.Text("Language / Jezik:", size=12, color=ft.Colors.GREY_400),
                ft.SegmentedButton(
                    selected={self.lang},
                    on_change=self._on_lang_change,
                    segments=[
                        ft.Segment(value="sr", label=ft.Text("SR")),
                        ft.Segment(value="en", label=ft.Text("EN")),
                    ],
                )
            ], alignment=ft.MainAxisAlignment.END)
        )

        # Welcome
        self.container.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ROCKET_LAUNCH, size=30, color=ft.Colors.WHITE),
                        ft.Text(t["welcome_title"], size=28, weight="bold", color=ft.Colors.WHITE),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(
                        t["welcome_subtitle"],
                        size=16, color=ft.Colors.BLUE_100, italic=True
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=30,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=[ft.Colors.BLUE_900, ft.Colors.BLUE_700]
                ),
                border_radius=15,
                margin=ft.margin.only(bottom=25)
            )
        )
        
        # Main Processes
        self.container.controls.append(
            ft.Container(
                content=ft.Text(t["main_processes"], size=20, weight="bold"),
                margin=ft.margin.only(bottom=10)
            )
        )
        
        self.container.controls.append(self.get_help_section(t["step1_title"], t["step1_content"], ft.Icons.FILE_DOWNLOAD))
        self.container.controls.append(self.get_help_section(t["step2_title"], t["step2_content"], ft.Icons.LAYERS))
        self.container.controls.append(self.get_help_section(t["step3_title"], t["step3_content"], ft.Icons.AUTO_AWESOME))

        self.container.controls.append(ft.Divider(height=40))
        
        # FAQ
        self.container.controls.append(
            ft.Container(
                content=ft.Text(t["faq_title"], size=20, weight="bold"),
                margin=ft.margin.only(bottom=10)
            )
        )
        
        self.container.controls.append(
            ft.ExpansionTile(
                title=ft.Text(t["q1_title"]),
                subtitle=ft.Text(t["q1_subtitle"]),
                controls=[ft.ListTile(title=ft.Text(t["q1_content"]))],
            )
        )
        
        self.container.controls.append(
            ft.ExpansionTile(
                title=ft.Text(t["q2_title"]),
                subtitle=ft.Text(t["q2_subtitle"]),
                controls=[ft.ListTile(title=ft.Text(t["q2_content"]))],
            )
        )
        
        self.container.controls.append(
            ft.ExpansionTile(
                title=ft.Text(t["q3_title"]),
                subtitle=ft.Text(t["q3_subtitle"]),
                controls=[ft.ListTile(title=ft.Text(t["q3_content"]))],
            )
        )

        # Support/Credits
        self.container.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Divider(),
                    ft.Row([
                        ft.Icon(ft.Icons.COPYRIGHT, size=14, color=ft.Colors.GREY_600),
                        ft.Text(t["credits"], size=12, color=ft.Colors.GREY_600),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(t["version"], size=10, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                margin=ft.margin.only(top=30, bottom=50)
            )
        )
        
        if self.page:
            self.page.update()

    def _on_lang_change(self, e):
        self.lang = list(e.control.selected)[0]
        self.update_ui()

    def get_help_section(self, title: str, content: str, icon: str = ft.Icons.HELP_OUTLINE):
        """Helper to create a consistent help section."""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=ft.Colors.BLUE_400),
                    ft.Text(title, size=18, weight="bold"),
                ]),
                ft.Text(content, size=14, color=ft.Colors.GREY_300),
            ], spacing=10),
            padding=15,
            bgcolor="#2a2a2a",
            border_radius=10,
            margin=ft.margin.only(bottom=15)
        )

    def get_tab(self) -> ft.Tab:
        """Returns the Help tab for the main GUI."""
        return self.tab
