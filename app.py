#!/usr/bin/env python3
import os
import re
import io
import sys
import subprocess
import pyfiglet
from PIL import Image, ImageOps
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, TabbedContent, TabPane, Input, Button, Static, Label, DirectoryTree, Select, Checkbox, TextArea

POPULAR_FONTS = [
    ("Slant", "slant"),
    ("Standard", "standard"),
    ("Block", "block"),
    ("Bubble", "bubble"),
    ("Doom", "doom"),
    ("Isometric", "isometric1"),
    ("Banner", "banner"),
    ("Digital", "digital"),
    ("Big", "big"),
    ("Mini", "mini"),
    ("Stop", "stop"),
]

BORDERS = [
    ("Heavy", "heavy"),
    ("Rounded", "rounded"),
    ("Double", "double"),
    ("ASCII", "ascii"),
    ("Simple", "simple"),
    ("None", "none"),
]

IMAGE_STYLES = [
    ("Clasico", "rakko"),
    ("Bloques Solidos", "blocks"),
    ("Alfanumerico Standard", "standard"),
]

class SSAsciiApp(App):
    CSS = """
    Screen {
        background: #000000;
        color: #ffffff;
    }
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    #left-panel {
        width: 38%;
        border-right: solid #333333;
        padding: 1;
        overflow-y: scroll;
    }
    #right-panel {
        width: 62%;
        padding: 1;
        layout: vertical;
    }
    TextArea {
        border: solid #ffffff;
        background: #000000;
        color: #ffffff;
        height: 1fr;
    }
    #stats-bar {
        background: #111111;
        color: #aaaaaa;
        padding: 1;
        margin-top: 1;
        margin-bottom: 1;
        border: solid #444444;
    }
    Button {
        margin-top: 1;
        margin-bottom: 1;
        width: 100%;
    }
    Input {
        margin-bottom: 1;
    }
    Select {
        margin-bottom: 1;
    }
    Checkbox {
        margin-top: 1;
        margin-bottom: 1;
    }
    DirectoryTree {
        height: 15;
        border: solid #444444;
        background: #050505;
        color: #ffffff;
        margin-bottom: 1;
    }
    """

    last_generated = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            # Panel Izquierdo
            with Vertical(id="left-panel"):
                with TabbedContent():
                    with TabPane("Texto"):
                        yield Label("Titulo")
                        yield Input(value="ASCII", id="banner-title")
                        yield Label("Subtitulo")
                        yield Input(value="", placeholder="Opcional", id="banner-subtitle")
                        yield Label("Eslogan")
                        yield Input(value="", placeholder="Opcional", id="banner-tagline")
                        yield Label("Fuente")
                        yield Select(POPULAR_FONTS, value="stop", id="banner-font")
                        yield Label("Borde")
                        yield Select(BORDERS, value="heavy", id="banner-border")
                        yield Label("Ancho")
                        yield Input(value="50", id="banner-width")
                    with TabPane("Imagen"):
                        yield Label("Seleccionar Imagen:")
                        yield DirectoryTree(os.path.expanduser("~"), id="file-tree")
                        yield Label("Estilo de Resultado:")
                        yield Select(IMAGE_STYLES, value="rakko", id="img-style")
                        yield Label("Ancho (columnas):")
                        yield Input(value="80", id="img-columns")
                        yield Checkbox("Invertir Colores", id="invert-checkbox")

                yield Button("Generar Arte ASCII", id="generate-btn", variant="primary")
                yield Label("Guardar Resultado:")
                yield Input(value="output.txt", id="save-path")
                yield Button("Guardar en archivo", id="save-btn", variant="success")
                yield Button("Copiar al portapapeles", id="copy-btn", variant="warning")
                yield Static("", id="save-status")

            # Panel Derecho (TextArea seleccionable y copiable)
            with Vertical(id="right-panel"):
                yield Label("Vista Previa (Seleccionable y Copiable)")
                yield TextArea("", id="output-view", read_only=True)
                yield Static("Ancho: 0 | Lineas: 0 | Total caracteres: 0", id="stats-bar")

        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_image = event.path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "generate-btn":
            self.generate_art()
        elif btn_id == "save-btn":
            self.save_art()
        elif btn_id == "copy-btn":
            self.copy_art()

    def generate_art(self):
        output_view = self.query_one("#output-view", TextArea)
        
        tabbed = self.query_one(TabbedContent)
        active_tab = tabbed.active

        try:
            if active_tab == "tab-1": # Texto
                title = self.query_one("#banner-title", Input).value
                subtitle = self.query_one("#banner-subtitle", Input).value
                tagline = self.query_one("#banner-tagline", Input).value
                font_select = self.query_one("#banner-font", Select)
                font = font_select.value if font_select.value is not Select.BLANK else "stop"
                border_select = self.query_one("#banner-border", Select)
                border_style = border_select.value if border_select.value is not Select.BLANK else "heavy"
                width_val = int(self.query_one("#banner-width", Input).value or 50)

                f = pyfiglet.Figlet(font=str(font))
                title_art = f.renderText(title)

                lines = [title_art.rstrip()]
                if subtitle:
                    lines.append(f"\n{subtitle}\n")
                if tagline:
                    lines.append(f"\n{tagline}\n")
                
                content = "".join(lines)
                framed = self.apply_border(content, border_style, width_val)
                
                self.last_generated = framed
                output_view.text = framed
                self.update_stats(framed)

            elif active_tab == "tab-2": # Imagen
                if not hasattr(self, "selected_image") or not self.selected_image:
                    output_view.text = "Por favor, selecciona una imagen del explorador en la pestaña Imagen."
                    return
                
                cols = int(self.query_one("#img-columns", Input).value)
                invert = self.query_one("#invert-checkbox", Checkbox).value
                style_select = self.query_one("#img-style", Select)
                style_val = style_select.value if style_select.value is not Select.BLANK else "rakko"

                img_path = str(self.selected_image)
                img = Image.open(img_path)
                
                if invert:
                    if img.mode == 'RGBA':
                        r, g, b, a = img.split()
                        rgb_image = Image.merge('RGB', (r, g, b))
                        inverted_rgb = ImageOps.invert(rgb_image)
                        r, g, b = inverted_rgb.split()
                        img = Image.merge('RGBA', (r, g, b, a))
                    else:
                        img = ImageOps.invert(img.convert('RGB'))

                img = img.convert('L')
                ramps = {
                    "rakko": " .:-=+*#%@",
                    "blocks": " ░▒▓█",
                    "standard": " `.-':_,^=&/rksbpadwm*#$@"
                }
                ramp = ramps.get(style_val, ramps["rakko"])
                
                aspect_ratio = img.height / img.width
                rows = int(cols * aspect_ratio * 0.55)
                img = img.resize((cols, rows), Image.Resampling.LANCZOS)
                
                pixels = img.getdata()
                num_chars = len(ramp)
                
                ascii_str = ""
                for i, pixel in enumerate(pixels):
                    char_idx = pixel * (num_chars - 1) // 255
                    ascii_str += ramp[char_idx]
                    if (i + 1) % cols == 0:
                        ascii_str += "\n"

                self.last_generated = ascii_str
                output_view.text = ascii_str
                self.update_stats(ascii_str)

        except Exception as e:
            output_view.text = f"Error al generar: {e}"
            self.last_generated = ""

    def apply_border(self, text: str, border_type: str, width: int) -> str:
        if border_type == "none":
            return text

        borders = {
            "heavy": ("┏", "┓", "┗", "┛", "━", "┃"),
            "rounded": ("╭", "╮", "╰", "╯", "─", "│"),
            "double": ("╔", "╗", "╚", "╝", "═", "║"),
            "ascii": ("+", "+", "+", "+", "-", "|"),
            "simple": (".", ".", "'", "'", "-", "|"),
        }
        tl, tr, bl, br, h, v = borders.get(border_type, borders["heavy"])

        content_lines = text.splitlines()
        max_len = max([len(line) for line in content_lines] + [width])
        box_width = max(max_len + 4, width)

        top_line = tl + h * (box_width - 2) + tr
        bottom_line = bl + h * (box_width - 2) + br

        framed_lines = [top_line]
        for line in content_lines:
            padded = line.ljust(box_width - 4)
            framed_lines.append(f"{v} {padded} {v}")
        framed_lines.append(bottom_line)

        return "\n".join(framed_lines)

    def update_stats(self, text: str):
        lines = text.splitlines()
        num_lines = len(lines)
        max_width = max((len(line) for line in lines), default=0)
        total_chars = len(text)
        stats_bar = self.query_one("#stats-bar", Static)
        stats_bar.update(f"Ancho: {max_width} caracteres x {num_lines} lineas | Total: {total_chars} caracteres")

    def save_art(self):
        path = self.query_one("#save-path", Input).value
        status = self.query_one("#save-status", Static)
        if not self.last_generated:
            status.update("No hay arte generado para guardar.")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.last_generated)
            status.update(f"Guardado en {path}!")
        except Exception as e:
            status.update(f"Error: {e}")

    def copy_art(self):
        status = self.query_one("#save-status", Static)
        text = self.query_one("#output-view", TextArea).text
        if not text:
            status.update("No hay arte generado para copiar.")
            return
        
        success = False

        # 1. Copiar usando un subproceso Python con tkinter (cero dependencias externas)
        try:
            escaped_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`")
            code = f"import tkinter as tk\nr = tk.Tk()\nr.withdraw()\nr.clipboard_clear()\nr.clipboard_append('''{text}''')\nr.update()\nr.destroy()"
            subprocess.run([sys.executable, "-c", code], check=True, timeout=2)
            success = True
        except Exception as e:
            pass

        # 2. Respaldo wl-copy / xclip / xsel si tkinter fallara
        if not success:
            for cmd in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=1)
                    success = True
                    break
                except Exception:
                    pass

        if success:
            status.update("¡Copiado al portapapeles con éxito!")
        else:
            status.update("Error al acceder al portapapeles.")

if __name__ == "__main__":
    app = SSAsciiApp()
    app.run()
