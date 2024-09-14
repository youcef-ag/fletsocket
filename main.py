import flet as ft
import socket
import ipaddress
import json
import os
from datetime import datetime
from functools import lru_cache

SETTINGS_FILE = "scanner_settings.json"
HISTORY_FILE = "scan_history.json"
COLOR_PALETTE = {
    "background": "#edf4fe", "secondary": "#c1e3ff", "accent": "#70bdf2",
    "primary": "#153f65", "text": "#03131f",
}

@lru_cache(maxsize=1)
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    return {"ip": "", "port": ""}

def save_settings(ip, port):
    with open(SETTINGS_FILE, "w") as file:
        json.dump({"ip": ip, "port": port}, file)
    load_settings.cache_clear()

def save_history(ip, port, status):
    history = load_history()
    new_entry = {
        "ip": ip,
        "port": port,
        "status": status,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    history = [item for item in history if not (item['ip'] == ip and item['port'] == port)]
    history.append(new_entry)
    history = history[-30:]
    with open(HISTORY_FILE, 'w') as file:
        json.dump(history, file)

@lru_cache(maxsize=1)
def load_history():
    try:
        with open(HISTORY_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def is_port_open(ip: str, port: int, timeout=1) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

class PortScanner(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.bgcolor = COLOR_PALETTE["background"]
        self.padding = ft.padding.symmetric(vertical=10, horizontal=10)
        self.expand = True
        self.content = self._build()

    def _build(self):
        settings = load_settings()
        self.ip_field = self._create_text_field("Adresse IP", settings["ip"])
        self.port_field = self._create_text_field("Port", settings["port"])
        self.result_text = ft.Text("Résultat apparaîtra ici", size=14, color=COLOR_PALETTE["text"])
        self.check_button = self._create_check_button()

        return ft.Column(
            [self.ip_field, ft.Container(height=20), self.port_field, ft.Container(height=20),
             self.check_button, ft.Container(height=20),
             ft.Container(content=self.result_text, bgcolor=COLOR_PALETTE["secondary"],
                          border_radius=8, padding=10, width=280)],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0, expand=True
        )

    def _create_text_field(self, label, value):
        return ft.TextField(
            label=label, value=value, width=280,
            border_color=COLOR_PALETTE["primary"],
            focused_border_color=COLOR_PALETTE["accent"],
            label_style=ft.TextStyle(color=COLOR_PALETTE["text"], size=12),
            text_style=ft.TextStyle(color=COLOR_PALETTE["text"], size=14),
            bgcolor=COLOR_PALETTE["secondary"],
            content_padding=ft.padding.all(8),
        )

    def _create_check_button(self):
        return ft.ElevatedButton(
            text="Vérifier",
            on_click=self.check_port,
            style=ft.ButtonStyle(
                color=COLOR_PALETTE["text"],
                bgcolor=COLOR_PALETTE["accent"],
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(top=12, bottom=12, left=16, right=16)
            ),
        )

    def check_port(self, _):
        ip, port = self.ip_field.value, self.port_field.value
        ip_error, port_error = validate_ip(ip), validate_port(port)
        
        self.ip_field.error_text = ip_error
        self.port_field.error_text = port_error

        if not (ip_error or port_error):
            status = is_port_open(ip, int(port))
            status_text = "ouvert" if status else "fermé"
            self.result_text.value = f"Le port {port} sur {ip} est {status_text}."
            self.result_text.color = ft.colors.GREEN if status else ft.colors.RED
            save_settings(ip, port)
            save_history(ip, port, status_text)
        else:
            self.result_text.value = "Veuillez corriger les erreurs dans les champs."
            self.result_text.color = ft.colors.RED

        self.page.update()

def validate_ip(ip):
    try:
        ip_address = ipaddress.ip_address(ip)
        if any([ip_address.is_private, ip_address.is_loopback, ip_address.is_link_local]):
            return "Cette adresse IP n'est pas autorisée"
        return None
    except ValueError:
        return "Adresse IP invalide"

def validate_port(port):
    try:
        port_num = int(port)
        return None if 1 <= port_num <= 65535 else "Port doit être entre 1 et 65535"
    except ValueError:
        return "Port doit être un nombre"

def create_appbar(page, title, with_back_button=False):
    actions = [] if with_back_button else [
        ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            icon_color=COLOR_PALETTE["background"],
            items=[
                ft.PopupMenuItem(text="Historique", on_click=lambda _: page.go("/history")),
                ft.PopupMenuItem(text="À propos", on_click=lambda _: page.go("/about")),
            ],
            bgcolor=COLOR_PALETTE["primary"],
        )
    ]
    return ft.AppBar(
        leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: page.go("/"),
                              icon_color=COLOR_PALETTE["background"]) if with_back_button else None,
        title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=COLOR_PALETTE["background"]),
        bgcolor=COLOR_PALETTE["primary"], actions=actions
    )

class HistoryView(ft.View):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.route = "/history"
        self.appbar = create_appbar(page, "Historique", True)
        self.controls = [self.appbar, self._build_history_list()]
        self.bgcolor = COLOR_PALETTE["background"]

    def _build_history_list(self):
        history = load_history()
        list_view = ft.ListView(spacing=10, padding=20, auto_scroll=True)
        
        for item in history:
            list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"IP: {item['ip']} | Port: {item['port']}", size=16, weight=ft.FontWeight.BOLD, color=COLOR_PALETTE["text"]),
                        ft.Text(f"Statut: {item['status']}", 
                                color=ft.colors.GREEN if item['status'] == "ouvert" else ft.colors.RED),
                        ft.Text(f"Date: {item['date']}", size=12, color=ft.colors.GREY_700)
                    ]),
                    bgcolor=COLOR_PALETTE["secondary"],
                    border_radius=8,
                    padding=10
                )
            )
        
        return ft.Container(content=list_view, expand=True)

def main(page: ft.Page):
    page.title = "Port Scanner"
    page.bgcolor = COLOR_PALETTE["background"]
    page.padding = 0
    page.window.width = 360
    page.window.min_width = 300
    page.window.max_width = 480
    port_scanner = PortScanner(page)

    def route_change(_):
        page.views.clear()
        if page.route == "/":
            page.views.append(ft.View("/", [create_appbar(page, "Port Scanner"), port_scanner],
                                      bgcolor=COLOR_PALETTE["background"]))
        elif page.route == "/history":
            page.views.append(HistoryView(page))
        elif page.route == "/about":
            page.views.append(ft.View("/about", [
                create_appbar(page, "À propos", True),
                ft.Container(content=ft.Column([
                    ft.Text("À propos", size=24, weight=ft.FontWeight.BOLD, color=COLOR_PALETTE["text"]),
                    ft.Text("Port Scanner est une application simple pour vérifier si un port spécifique est ouvert sur une adresse IP donnée.", 
                            size=16, color=COLOR_PALETTE["text"])
                ]), padding=40, bgcolor=COLOR_PALETTE["secondary"], border_radius=10, margin=20)
            ], bgcolor=COLOR_PALETTE["background"]))
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = lambda _: page.go("/")
    page.go(page.route)

ft.app(target=main)
