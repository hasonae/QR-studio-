# -*- coding: utf-8 -*-
"""QR Studio - offline QR maker built with Kivy."""

__version__ = "1.0.0"

import io
import json
import os
import re
import time
import hashlib
from datetime import datetime

import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image as PILImage, ImageDraw

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard


# ------------------------------ Visual system ------------------------------
BG = "#0A1020"
SURFACE = "#111C30"
SURFACE_2 = "#17243A"
BORDER = "#263750"
TEXT = "#F4F7FB"
MUTED = "#9AAAC0"
ACCENT = "#35D6C0"
ACCENT_DARK = "#123C43"
DANGER = "#FF7777"
WHITE = "#FFFFFF"

FG_PALETTE = [
    ("Ink", "#111827"),
    ("Navy", "#102A43"),
    ("Teal", "#087F78"),
    ("Berry", "#7C2D55"),
    ("Forest", "#245B42"),
]
BG_PALETTE = [
    ("White", "#FFFFFF"),
    ("Ivory", "#FFF8E8"),
    ("Mist", "#EAF2F7"),
]
ERROR_LEVELS = {
    "Low · 7%": ERROR_CORRECT_L,
    "Medium · 15%": ERROR_CORRECT_M,
    "High · 25%": ERROR_CORRECT_Q,
    "Best · 30%": ERROR_CORRECT_H,
}

TYPE_LABELS = {
    "url": "Website",
    "text": "Text",
    "wifi": "Wi-Fi",
    "contact": "Contact",
    "email": "Email",
    "phone": "Phone",
    "sms": "SMS",
}


class RoundedPanel(BoxLayout):
    bg_color = ListProperty(get_color_from_hex(SURFACE))
    radius = ListProperty([dp(18)])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = kwargs.get("padding", dp(14))
        self.spacing = kwargs.get("spacing", dp(8))
        with self.canvas.before:
            self._bg_color = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._update_canvas, size=self._update_canvas, bg_color=self._update_color)

    def _update_canvas(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_color(self, *_):
        self._bg_color.rgba = self.bg_color


class SoftButton(Button):
    """Compact custom button with rounded background and no platform chrome."""
    fill = ListProperty(get_color_from_hex(SURFACE_2))
    text_color = ListProperty(get_color_from_hex(TEXT))
    radius = ListProperty([dp(13)])
    outline = ListProperty([0, 0, 0, 0])

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", get_color_from_hex(TEXT))
        kwargs.setdefault("font_size", sp(13))
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill_instruction = Color(*self.fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
            self._line_color = Color(*self.outline)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(13)), width=1)
        self.bind(pos=self._sync, size=self._sync, fill=self._sync_fill, outline=self._sync_outline, text_color=self._sync_text)
        self.bind(state=self._state_changed)
        self.color = self.text_color

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(13))

    def _sync_fill(self, *_):
        self._fill_instruction.rgba = self.fill

    def _sync_outline(self, *_):
        self._line_color.rgba = self.outline

    def _sync_text(self, *_):
        self.color = self.text_color

    def _state_changed(self, *_):
        self.opacity = 0.78 if self.state == "down" else 1


class FieldBlock(BoxLayout):
    def __init__(self, title, hint="", multiline=False, password=False, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(6), size_hint_y=None, height=dp(82), **kwargs)
        self.add_widget(Label(text=title, color=get_color_from_hex(MUTED), font_size=sp(12), bold=True,
                              size_hint_y=None, height=dp(19), halign="left", valign="middle", text_size=(None, None)))
        self.input = TextInput(
            hint_text=hint, multiline=multiline, password=password, size_hint_y=None, height=dp(54),
            padding=[dp(13), dp(13), dp(13), dp(10)], font_size=sp(14),
            foreground_color=get_color_from_hex(TEXT), hint_text_color=get_color_from_hex("#71839B"),
            background_normal="", background_active="", background_color=get_color_from_hex(SURFACE_2),
            cursor_color=get_color_from_hex(ACCENT), selection_color=get_color_from_hex("#236C70"),
        )
        self.add_widget(self.input)


class SectionTitle(BoxLayout):
    def __init__(self, title, caption=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(47), spacing=dp(2), **kwargs)
        self.add_widget(Label(text=title, color=get_color_from_hex(TEXT), font_size=sp(15), bold=True,
                              halign="left", valign="middle", text_size=(None, None)))
        if caption:
            self.add_widget(Label(text=caption, color=get_color_from_hex(MUTED), font_size=sp(11),
                                  halign="left", valign="middle", text_size=(None, None)))


# -------------------------------- Main app ----------------------------------
class QRStudioApp(App):
    title = "QR Studio"

    def build(self):
        Window.clearcolor = get_color_from_hex(BG)
        self.user_dir = self.user_data_dir
        self.export_dir = os.path.join(self.user_dir, "exports")
        os.makedirs(self.export_dir, exist_ok=True)
        self.history_path = os.path.join(self.user_dir, "history.json")
        self.history = self._load_history()
        self.selected_type = "url"
        self.fg_name, self.fg_hex = FG_PALETTE[0]
        self.bg_name, self.bg_hex = BG_PALETTE[0]
        self.error_label = "Medium · 15%"
        self.current_png = None
        self.current_payload = ""
        self.current_title = ""
        self.current_type = ""
        self.current_content_uri = None
        self.field_inputs = {}
        self.active_tab = "create"

        self.root = BoxLayout(orientation="vertical", spacing=0)
        self._build_header()
        self.content_host = BoxLayout(orientation="vertical")
        self.root.add_widget(self.content_host)
        self._build_bottom_nav()
        self.show_create()
        return self.root

    def _load_history(self):
        try:
            with open(self.history_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            return []

    def _save_history_file(self):
        temp = self.history_path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.history[:100], handle, ensure_ascii=False, indent=2)
        os.replace(temp, self.history_path)

    def _build_header(self):
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(76), padding=[dp(20), dp(10)], spacing=dp(12))
        brand = BoxLayout(orientation="vertical", spacing=0)
        brand.add_widget(Label(text="QR STUDIO", color=get_color_from_hex(TEXT), font_size=sp(20), bold=True,
                               halign="left", valign="middle", text_size=(None, None)))
        brand.add_widget(Label(text="MAKE IT SCANNABLE.", color=get_color_from_hex(MUTED), font_size=sp(9), bold=True,
                               halign="left", valign="middle", text_size=(None, None)))
        header.add_widget(brand)
        header.add_widget(Widget())
        mark = SoftButton(text="▦", size_hint=(None, None), size=(dp(43), dp(43)), fill=get_color_from_hex(ACCENT_DARK),
                          text_color=get_color_from_hex(ACCENT), font_size=sp(22))
        mark.disabled = True
        header.add_widget(mark)
        self.root.add_widget(header)

    def _build_bottom_nav(self):
        nav = BoxLayout(size_hint_y=None, height=dp(66), padding=[dp(14), dp(8)], spacing=dp(10))
        self.nav_create = SoftButton(text="＋   Create", fill=get_color_from_hex(ACCENT_DARK), text_color=get_color_from_hex(ACCENT))
        self.nav_library = SoftButton(text="▤   Library", fill=get_color_from_hex(SURFACE_2), text_color=get_color_from_hex(MUTED))
        self.nav_create.bind(on_release=lambda *_: self.show_create())
        self.nav_library.bind(on_release=lambda *_: self.show_library())
        nav.add_widget(self.nav_create)
        nav.add_widget(self.nav_library)
        self.root.add_widget(nav)

    def _set_nav(self, tab):
        self.nav_create.fill = get_color_from_hex(ACCENT_DARK if tab == "create" else SURFACE_2)
        self.nav_create.text_color = get_color_from_hex(ACCENT if tab == "create" else MUTED)
        self.nav_library.fill = get_color_from_hex(ACCENT_DARK if tab == "library" else SURFACE_2)
        self.nav_library.text_color = get_color_from_hex(ACCENT if tab == "library" else MUTED)
        self.active_tab = tab

    def _clear_content(self):
        self.content_host.clear_widgets()

    def show_create(self):
        self._set_nav("create")
        self._clear_content()
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["bars", "content"])
        page = BoxLayout(orientation="vertical", padding=[dp(18), dp(8), dp(18), dp(22)], spacing=dp(15), size_hint_y=None)
        page.bind(minimum_height=page.setter("height"))

        hero = RoundedPanel(orientation="vertical", size_hint_y=None, height=dp(112), padding=dp(17), spacing=dp(4), bg_color=get_color_from_hex("#12313C"))
        hero.add_widget(Label(text="Turn anything into a QR.", color=get_color_from_hex(TEXT), font_size=sp(19), bold=True,
                              halign="left", valign="middle", text_size=(None, None)))
        hero.add_widget(Label(text="Create, customize and save — all on your device.", color=get_color_from_hex("#B8D7D7"),
                              font_size=sp(12), halign="left", valign="middle", text_size=(None, None)))
        hero.add_widget(Label(text="●  OFFLINE READY     ·     PRIVATE BY DESIGN", color=get_color_from_hex(ACCENT),
                              font_size=sp(9), bold=True, halign="left", valign="middle", text_size=(None, None)))
        page.add_widget(hero)

        page.add_widget(SectionTitle("01  ·  Content type", "Choose what your QR code should contain"))
        type_grid = GridLayout(cols=4, spacing=dp(7), size_hint_y=None, height=dp(104))
        self.type_buttons = {}
        types = [("url", "↗", "Web"), ("text", "T", "Text"), ("wifi", "⌁", "Wi-Fi"),
                 ("contact", "♙", "Contact"), ("email", "✉", "Email"), ("phone", "☎", "Phone"),
                 ("sms", "▤", "SMS")]
        for kind, symbol, label in types:
            btn = SoftButton(text=f"{symbol}\n{label}", font_size=sp(11), fill=get_color_from_hex(SURFACE_2),
                             text_color=get_color_from_hex(MUTED))
            btn.bind(on_release=lambda _btn, k=kind: self.select_type(k))
            type_grid.add_widget(btn)
            self.type_buttons[kind] = btn
        page.add_widget(type_grid)

        page.add_widget(SectionTitle("02  ·  Your content", "Only the fields needed for this QR type are shown"))
        self.fields_panel = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.fields_panel.bind(minimum_height=self.fields_panel.setter("height"))
        page.add_widget(self.fields_panel)

        page.add_widget(SectionTitle("03  ·  Style your code", "Choose a strong contrast for reliable scanning"))
        style_panel = RoundedPanel(orientation="vertical", size_hint_y=None, height=dp(176), padding=dp(13), spacing=dp(9))
        style_panel.add_widget(Label(text="FOREGROUND", color=get_color_from_hex(MUTED), font_size=sp(10), bold=True,
                                     size_hint_y=None, height=dp(17), halign="left", text_size=(None, None)))
        fg_row = BoxLayout(size_hint_y=None, height=dp(33), spacing=dp(8))
        self.fg_buttons = []
        for name, hx in FG_PALETTE:
            dot = SoftButton(text="", fill=get_color_from_hex(hx), outline=get_color_from_hex("#607086"),
                             size_hint=(None, None), size=(dp(34), dp(30)))
            dot.bind(on_release=lambda _b, n=name, h=hx: self.set_palette("fg", n, h))
            fg_row.add_widget(dot)
            self.fg_buttons.append((dot, name, hx))
        style_panel.add_widget(fg_row)
        style_panel.add_widget(Label(text="BACKGROUND", color=get_color_from_hex(MUTED), font_size=sp(10), bold=True,
                                     size_hint_y=None, height=dp(17), halign="left", text_size=(None, None)))
        bg_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        self.bg_buttons = []
        for name, hx in BG_PALETTE:
            chip = SoftButton(text=name, fill=get_color_from_hex(hx), text_color=get_color_from_hex("#172033"),
                              font_size=sp(10), outline=get_color_from_hex("#607086"))
            chip.bind(on_release=lambda _b, n=name, h=hx: self.set_palette("bg", n, h))
            bg_row.add_widget(chip)
            self.bg_buttons.append((chip, name, hx))
        style_panel.add_widget(bg_row)
        page.add_widget(style_panel)

        options = RoundedPanel(orientation="vertical", size_hint_y=None, height=dp(87), padding=dp(12), spacing=dp(5))
        options.add_widget(Label(text="ERROR CORRECTION", color=get_color_from_hex(MUTED), font_size=sp(10), bold=True,
                                 size_hint_y=None, height=dp(17), halign="left", text_size=(None, None)))
        self.error_buttons = []
        erow = BoxLayout(size_hint_y=None, height=dp(37), spacing=dp(6))
        for label in ERROR_LEVELS:
            b = SoftButton(text=label.split(" ·")[0], font_size=sp(10), fill=get_color_from_hex(SURFACE_2),
                           text_color=get_color_from_hex(MUTED))
            b.bind(on_release=lambda _b, x=label: self.set_error_level(x))
            erow.add_widget(b)
            self.error_buttons.append((b, label))
        options.add_widget(erow)
        page.add_widget(options)

        self.preview_panel = RoundedPanel(orientation="vertical", size_hint_y=None, height=dp(330), padding=dp(14), spacing=dp(9))
        preview_head = BoxLayout(size_hint_y=None, height=dp(27))
        preview_head.add_widget(Label(text="04  ·  QR preview", color=get_color_from_hex(TEXT), font_size=sp(15), bold=True,
                                      halign="left", valign="middle", text_size=(None, None)))
        self.preview_status = Label(text="NOT GENERATED", color=get_color_from_hex(MUTED), font_size=sp(9), bold=True,
                                    size_hint_x=None, width=dp(112), halign="right")
        preview_head.add_widget(self.preview_status)
        self.preview_panel.add_widget(preview_head)
        self.preview_area = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(232), padding=dp(6))
        self.preview_placeholder = Label(text="▦\nYour QR code will appear here", color=get_color_from_hex(MUTED),
                                         font_size=sp(15), halign="center")
        self.preview_area.add_widget(self.preview_placeholder)
        self.preview_panel.add_widget(self.preview_area)
        self.preview_hint = Label(text="High-resolution PNG · Scan-ready quiet zone", color=get_color_from_hex(MUTED),
                                  font_size=sp(10), size_hint_y=None, height=dp(18))
        self.preview_panel.add_widget(self.preview_hint)
        page.add_widget(self.preview_panel)

        actions = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(7))
        generate = SoftButton(text="✦   Generate QR", fill=get_color_from_hex(ACCENT), text_color=get_color_from_hex("#062B2A"),
                              font_size=sp(14))
        generate.bind(on_release=lambda *_: self.generate_qr())
        save = SoftButton(text="↓   Save PNG", fill=get_color_from_hex(SURFACE_2), text_color=get_color_from_hex(TEXT),
                          outline=get_color_from_hex(BORDER))
        save.bind(on_release=lambda *_: self.save_qr())
        share = SoftButton(text="↗", size_hint_x=None, width=dp(48), fill=get_color_from_hex(SURFACE_2),
                           text_color=get_color_from_hex(ACCENT), outline=get_color_from_hex(BORDER))
        share.bind(on_release=lambda *_: self.share_qr())
        actions.add_widget(generate)
        actions.add_widget(save)
        actions.add_widget(share)
        page.add_widget(actions)

        self.message_label = Label(text="Your codes stay on this device.", color=get_color_from_hex(MUTED), font_size=sp(10),
                                   size_hint_y=None, height=dp(20))
        page.add_widget(self.message_label)

        scroll.add_widget(page)
        self.content_host.add_widget(scroll)
        self.select_type(self.selected_type)
        self._refresh_style_buttons()

    def select_type(self, kind):
        self.selected_type = kind
        for k, btn in self.type_buttons.items():
            active = k == kind
            btn.fill = get_color_from_hex(ACCENT_DARK if active else SURFACE_2)
            btn.text_color = get_color_from_hex(ACCENT if active else MUTED)
        self.fields_panel.clear_widgets()
        self.field_inputs = {}
        definitions = {
            "url": [("URL", "https://example.com", "url")],
            "text": [("TEXT", "Write your message...", "text")],
            "wifi": [("NETWORK NAME (SSID)", "Your Wi-Fi name", "ssid"),
                     ("PASSWORD", "Wi-Fi password", "password"), ("SECURITY", "WPA / WEP / nopass", "security")],
            "contact": [("FULL NAME", "Name shown in contacts", "name"), ("PHONE", "+420...", "phone"),
                        ("EMAIL", "name@example.com", "email"), ("ORGANIZATION", "Company (optional)", "org"),
                        ("WEBSITE", "https://example.com (optional)", "url")],
            "email": [("EMAIL ADDRESS", "hello@example.com", "email"), ("SUBJECT", "Subject (optional)", "subject"),
                      ("MESSAGE", "Your message (optional)", "body")],
            "phone": [("PHONE NUMBER", "+420...", "phone")],
            "sms": [("PHONE NUMBER", "+420...", "phone"), ("MESSAGE", "Your text message", "body")],
        }
        for title, hint, key in definitions[kind]:
            block = FieldBlock(title, hint, multiline=(key in ("text", "body")), password=(key == "password"))
            if key in self.field_inputs:
                key = key + "_2"
            self.field_inputs[key] = block.input
            self.fields_panel.add_widget(block)
        if kind == "wifi":
            self.field_inputs["security"].text = "WPA"

    def set_palette(self, which, name, hx):
        if which == "fg":
            self.fg_name, self.fg_hex = name, hx
        else:
            self.bg_name, self.bg_hex = name, hx
        self._refresh_style_buttons()

    def _refresh_style_buttons(self):
        if hasattr(self, "fg_buttons"):
            for btn, name, _hx in self.fg_buttons:
                btn.outline = get_color_from_hex(ACCENT if name == self.fg_name else "#607086")
        if hasattr(self, "bg_buttons"):
            for btn, name, _hx in self.bg_buttons:
                btn.outline = get_color_from_hex(ACCENT if name == self.bg_name else "#607086")
        if hasattr(self, "error_buttons"):
            for btn, label in self.error_buttons:
                active = label == self.error_label
                btn.fill = get_color_from_hex(ACCENT_DARK if active else SURFACE_2)
                btn.text_color = get_color_from_hex(ACCENT if active else MUTED)

    def set_error_level(self, label):
        self.error_label = label
        self._refresh_style_buttons()

    def _value(self, key):
        widget = self.field_inputs.get(key)
        return widget.text.strip() if widget else ""

    @staticmethod
    def _clean_vcard(value):
        return value.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")

    def _make_payload(self):
        kind = self.selected_type
        if kind == "url":
            value = self._value("url")
            if not value:
                raise ValueError("Enter a website address first.")
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
                value = "https://" + value
            return value, self._value("title") or "Website QR"
        if kind == "text":
            value = self._value("text")
            if not value:
                raise ValueError("Write some text before generating your QR.")
            return value, "Text QR"
        if kind == "wifi":
            ssid = self._value("ssid")
            password = self._value("password")
            security = (self._value("security") or "WPA").upper()
            if not ssid:
                raise ValueError("Enter the Wi-Fi network name (SSID).")
            if security not in ("WPA", "WPA2", "WEP", "NOPASS", "OPEN"):
                raise ValueError("Security must be WPA, WEP, or nopass.")
            if security in ("OPEN", "NOPASS"):
                security = "nopass"
                password = ""
            else:
                security = "WPA" if security == "WPA2" else security
                if not password:
                    raise ValueError("Enter the Wi-Fi password or choose nopass.")
            esc = lambda s: s.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace(":", r"\:").replace('"', r'\"')
            return f"WIFI:T:{security};S:{esc(ssid)};P:{esc(password)};;", f"Wi-Fi · {ssid}"
        if kind == "contact":
            name = self._value("name")
            if not name:
                raise ValueError("Enter the contact name.")
            lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{self._clean_vcard(name)}"]
            if self._value("phone"):
                lines.append(f"TEL;TYPE=CELL:{self._clean_vcard(self._value('phone'))}")
            if self._value("email"):
                lines.append(f"EMAIL:{self._clean_vcard(self._value('email'))}")
            if self._value("org"):
                lines.append(f"ORG:{self._clean_vcard(self._value('org'))}")
            if self._value("url"):
                lines.append(f"URL:{self._clean_vcard(self._value('url'))}")
            lines.append("END:VCARD")
            return "\r\n".join(lines), name
        if kind == "email":
            address = self._value("email")
            if not address or "@" not in address:
                raise ValueError("Enter a valid email address.")
            from urllib.parse import quote
            params = []
            if self._value("subject"):
                params.append("subject=" + quote(self._value("subject")))
            if self._value("body"):
                params.append("body=" + quote(self._value("body")))
            payload = "mailto:" + address
            if params:
                payload += "?" + "&".join(params)
            return payload, "Email · " + address
        if kind == "phone":
            phone = self._value("phone")
            if not phone:
                raise ValueError("Enter a phone number.")
            return "tel:" + phone, "Phone · " + phone
        if kind == "sms":
            phone = self._value("phone")
            if not phone:
                raise ValueError("Enter a phone number.")
            from urllib.parse import quote
            body = self._value("body")
            payload = "SMSTO:" + phone + (":" + body if body else "")
            return payload, "SMS · " + phone
        raise ValueError("Unsupported QR type.")

    def generate_qr(self):
        try:
            payload, title = self._make_payload()
            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_LEVELS[self.error_label],
                # Keep every QR module on an exact integer pixel grid.
                # Arbitrary resizing (for example, 444x444 -> 1024x1024)
                # distorts module widths and can make the code difficult to scan.
                box_size=16,
                border=4,
            )
            qr.add_data(payload)
            qr.make(fit=True)
            image = qr.make_image(fill_color=self.fg_hex, back_color=self.bg_hex).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            self.current_png = buffer.getvalue()
            self.current_payload = payload
            self.current_title = title[:64]
            self.current_type = self.selected_type
            self._show_preview(self.current_png)
            self.preview_status.text = "READY TO SAVE"
            self.preview_status.color = get_color_from_hex(ACCENT)
            self.message_label.text = "QR generated successfully. Save it to add it to your library."
            self.message_label.color = get_color_from_hex(ACCENT)
        except ValueError as exc:
            self._notify(str(exc), error=True)
        except Exception as exc:
            self._notify("Could not generate QR: " + str(exc), error=True)

    def _show_preview(self, png_bytes):
        self.preview_area.clear_widgets()
        image = Image(allow_stretch=True, keep_ratio=True, size_hint=(1, 1))
        try:
            image.texture = CoreImage(io.BytesIO(png_bytes), ext="png").texture
        except Exception:
            # Fallback path for Kivy providers that do not accept BytesIO.
            temp = os.path.join(self.user_dir, "preview.png")
            with open(temp, "wb") as handle:
                handle.write(png_bytes)
            image.source = temp
            image.reload()
        self.preview_area.add_widget(image)

    def _notify(self, message, error=False):
        if hasattr(self, "message_label"):
            self.message_label.text = message
            self.message_label.color = get_color_from_hex(DANGER if error else ACCENT)

    def _safe_filename(self, title):
        clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_-")[:36] or "QR_Code"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{clean}_{stamp}.png"

    def save_qr(self):
        """Save the actual QR generated from the payload, never the app icon/preview placeholder."""
        if not self.current_payload:
            self._notify("Generate a QR code before saving it.", error=True)
            return
        filename = self._safe_filename(self.current_title)
        local_path = os.path.join(self.export_dir, filename)
        try:
            # Re-render from the exact encoded data at save time. This prevents any
            # Kivy widget texture, placeholder, or launcher icon from being saved.
            png_bytes = self._render_payload(
                self.current_payload,
                self.fg_hex or "#111827",
                self.bg_hex or "#FFFFFF",
            )
            # Verify that the bytes are a valid PNG and can be decoded before saving.
            with PILImage.open(io.BytesIO(png_bytes)) as check:
                check.verify()
            if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Generated image is not a valid PNG.")

            with open(local_path, "wb") as handle:
                handle.write(png_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            # Read back the exact file written; this is also the source for MediaStore.
            with open(local_path, "rb") as handle:
                saved_bytes = handle.read()
            with PILImage.open(io.BytesIO(saved_bytes)) as check:
                check.verify()

            self.current_png = saved_bytes
            record = {
                "id": hashlib.sha1((self.current_payload + str(time.time())).encode("utf-8")).hexdigest()[:12],
                "title": self.current_title,
                "type": self.current_type,
                "payload": self.current_payload,
                "filename": filename,
                "path": local_path,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "foreground": self.fg_hex,
                "background": self.bg_hex,
            }
            self.history.insert(0, record)
            self.history = self.history[:100]
            self._save_history_file()
            self.current_content_uri = None
            gallery_message = self._save_to_android_gallery(filename, saved_bytes)
            if gallery_message:
                self._notify(gallery_message)
            else:
                self._notify("QR PNG saved in QR Studio app storage. Open the app export folder to view it.")
            self._toast("QR saved")
        except Exception as exc:
            self._notify("Save failed: " + str(exc), error=True)

    def _save_to_android_gallery(self, filename, png_bytes):
        """Use MediaStore on Android 10+; no broad storage permission is needed."""
        try:
            from jnius import autoclass
            import base64
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            ContentValues = autoclass("android.content.ContentValues")
            MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")
            MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
            Environment = autoclass("android.os.Environment")
            AndroidBase64 = autoclass("android.util.Base64")
            values = ContentValues()
            values.put(MediaColumns.DISPLAY_NAME, filename)
            values.put(MediaColumns.MIME_TYPE, "image/png")
            values.put(MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/QR Studio")
            values.put(MediaColumns.IS_PENDING, 1)
            resolver = activity.getContentResolver()
            uri = resolver.insert(MediaStoreImages.EXTERNAL_CONTENT_URI, values)
            if uri is None:
                return None
            stream = resolver.openOutputStream(uri)
            encoded = base64.b64encode(png_bytes).decode("ascii")
            byte_array = AndroidBase64.decode(encoded, AndroidBase64.DEFAULT)
            stream.write(byte_array)
            stream.flush()
            stream.close()
            values2 = ContentValues()
            values2.put(MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values2, None, None)
            self.current_content_uri = str(uri.toString())
            return "Saved to Pictures / QR Studio and your library."
        except Exception:
            # Desktop and non-Android runs fall back to the app's own export folder.
            return None


    def share_qr(self):
        if not self.current_png:
            self._notify("Generate a QR code before sharing it.", error=True)
            return
        if not self.current_content_uri:
            try:
                Clipboard.copy(self.current_payload)
                self._notify("QR image is not in the gallery yet. Its content was copied instead.")
            except Exception:
                self._notify("Save the QR first, then share it from your gallery.", error=True)
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("image/png")
            intent.putExtra(Intent.EXTRA_STREAM, Uri.parse(self.current_content_uri))
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            chooser = Intent.createChooser(intent, "Share QR image")
            PythonActivity.mActivity.startActivity(chooser)
        except Exception:
            try:
                Clipboard.copy(self.current_payload)
                self._notify("Sharing is unavailable here; QR content copied to clipboard.")
            except Exception:
                self._notify("Could not open Android sharing.", error=True)

    def _toast(self, message):
        try:
            from plyer import notification
            notification.notify(title="QR Studio", message=message, timeout=2)
        except Exception:
            pass

    def show_library(self):
        self._set_nav("library")
        self._clear_content()
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        page = BoxLayout(orientation="vertical", padding=[dp(18), dp(8), dp(18), dp(22)], spacing=dp(14), size_hint_y=None)
        page.bind(minimum_height=page.setter("height"))
        page.add_widget(SectionTitle("Your QR library", f"{len(self.history)} saved code(s) · Stored on this device"))
        if not self.history:
            empty = RoundedPanel(orientation="vertical", size_hint_y=None, height=dp(190), padding=dp(20), spacing=dp(8))
            empty.add_widget(Label(text="▦", color=get_color_from_hex(ACCENT), font_size=sp(38)))
            empty.add_widget(Label(text="Nothing saved yet", color=get_color_from_hex(TEXT), font_size=sp(16), bold=True))
            empty.add_widget(Label(text="Your generated codes will appear here.\nCreate your first QR code to get started.",
                                   color=get_color_from_hex(MUTED), font_size=sp(12), halign="center"))
            page.add_widget(empty)
        else:
            for record in self.history:
                card = RoundedPanel(orientation="horizontal", size_hint_y=None, height=dp(92), padding=dp(11), spacing=dp(10))
                icon_box = RoundedPanel(size_hint=(None, None), size=(dp(62), dp(62)), padding=dp(4),
                                        bg_color=get_color_from_hex("#FFFFFF"))
                mini = Image(allow_stretch=True, keep_ratio=True)
                path = record.get("path", "")
                if path and os.path.exists(path):
                    mini.source = path
                    mini.reload()
                else:
                    mini.color = get_color_from_hex("#111827")
                icon_box.add_widget(mini)
                card.add_widget(icon_box)
                info = BoxLayout(orientation="vertical", spacing=dp(3))
                info.add_widget(Label(text=record.get("title", "QR Code"), color=get_color_from_hex(TEXT),
                                      font_size=sp(13), bold=True, halign="left", valign="middle", text_size=(None, None)))
                info.add_widget(Label(text=f"{TYPE_LABELS.get(record.get('type'), 'QR')}  ·  {record.get('created', '')}",
                                      color=get_color_from_hex(MUTED), font_size=sp(10), halign="left", valign="middle", text_size=(None, None)))
                info.add_widget(Label(text=record.get("filename", ""), color=get_color_from_hex("#71839B"), font_size=sp(9),
                                      halign="left", valign="middle", text_size=(None, None)))
                card.add_widget(info)
                actions = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(62), spacing=dp(5))
                open_btn = SoftButton(text="Open", font_size=sp(10), fill=get_color_from_hex(ACCENT_DARK),
                                      text_color=get_color_from_hex(ACCENT), size_hint_y=None, height=dp(33))
                open_btn.bind(on_release=lambda _b, r=record: self.reopen_record(r))
                delete_btn = SoftButton(text="Delete", font_size=sp(9), fill=get_color_from_hex("#3A2531"),
                                        text_color=get_color_from_hex("#FFAAAA"), size_hint_y=None, height=dp(30))
                delete_btn.bind(on_release=lambda _b, rid=record.get("id"): self.delete_record(rid))
                actions.add_widget(open_btn)
                actions.add_widget(delete_btn)
                card.add_widget(actions)
                page.add_widget(card)
        if self.history:
            clear_btn = SoftButton(text="Clear library", size_hint_y=None, height=dp(45), fill=get_color_from_hex("#3A2531"),
                                   text_color=get_color_from_hex("#FFAAAA"))
            clear_btn.bind(on_release=lambda *_: self.clear_library())
            page.add_widget(clear_btn)
        scroll.add_widget(page)
        self.content_host.add_widget(scroll)

    def reopen_record(self, record):
        self.selected_type = record.get("type", "text")
        self.fg_name = "Saved"
        self.fg_hex = record.get("foreground", "#111827")
        self.bg_name = "Saved"
        self.bg_hex = record.get("background", "#FFFFFF")
        self.current_payload = record.get("payload", "")
        self.current_title = record.get("title", "QR Code")
        self.current_type = record.get("type", "text")
        self.current_content_uri = None
        path = record.get("path", "")
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as handle:
                    self.current_png = handle.read()
            except OSError:
                self.current_png = None
        if not self.current_png:
            self.current_png = self._render_payload(self.current_payload, record.get("foreground", "#111827"),
                                                    record.get("background", "#FFFFFF"))
        self.show_create()
        self._populate_fields_from_payload(record.get("type", "text"), self.current_payload)
        self._show_preview(self.current_png)
        self.preview_status.text = "FROM LIBRARY"
        self.preview_status.color = get_color_from_hex(ACCENT)
        self._notify("Loaded from your library. Edit the fields or save another copy.")

    def _populate_fields_from_payload(self, kind, payload):
        """Best-effort form restoration for common QR payload formats."""
        from urllib.parse import urlparse, parse_qs, unquote

        def put(key, value):
            if key in self.field_inputs:
                self.field_inputs[key].text = value

        def unescape_wifi(value):
            return re.sub(r"\\(.)", r"\1", value)

        if kind == "url":
            put("url", payload)
        elif kind == "text":
            put("text", payload)
        elif kind == "phone":
            put("phone", payload[4:] if payload.startswith("tel:") else payload)
        elif kind == "sms":
            body = ""
            rest = payload[6:] if payload.startswith("SMSTO:") else payload
            parts = rest.split(":", 1)
            put("phone", parts[0])
            if len(parts) > 1:
                put("body", parts[1])
        elif kind == "email":
            parsed = urlparse(payload)
            put("email", parsed.path)
            params = parse_qs(parsed.query)
            put("subject", unquote(params.get("subject", [""])[0]))
            put("body", unquote(params.get("body", [""])[0]))
        elif kind == "wifi":
            match = re.search(r"WIFI:T:([^;]*);S:((?:\\.|[^;])*);P:((?:\\.|[^;])*);", payload)
            if match:
                put("security", match.group(1))
                put("ssid", unescape_wifi(match.group(2)))
                put("password", unescape_wifi(match.group(3)))
        elif kind == "contact":
            for line in payload.replace("\r", "").split("\n"):
                if line.startswith("FN:"):
                    put("name", line[3:])
                elif line.startswith("TEL") and ":" in line:
                    put("phone", line.split(":", 1)[1])
                elif line.startswith("EMAIL:"):
                    put("email", line[6:])
                elif line.startswith("ORG:"):
                    put("org", line[4:])
                elif line.startswith("URL:"):
                    put("url", line[4:])

    def _render_payload(self, payload, fg, bg):
        # Render directly at the QR library's native module-aligned resolution.
        qr = qrcode.QRCode(version=None, error_correction=ERROR_LEVELS["Medium · 15%"], box_size=16, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        im = qr.make_image(fill_color=fg, back_color=bg).convert("RGB")
        out = io.BytesIO()
        im.save(out, format="PNG")
        return out.getvalue()

    def delete_record(self, record_id):
        record = next((r for r in self.history if r.get("id") == record_id), None)
        self.history = [r for r in self.history if r.get("id") != record_id]
        if record:
            path = record.get("path", "")
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._save_history_file()
        self.show_library()

    def clear_library(self):
        for record in self.history:
            try:
                path = record.get("path", "")
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self.history = []
        self._save_history_file()
        self.show_library()


if __name__ == "__main__":
    QRStudioApp().run()
