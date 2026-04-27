from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import tkinter.messagebox as msg
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw

from ..services import CarSharingService, SYSTEM_ADMIN_EMAIL


THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "appearance": "dark",
        "bg": "#0B1120",
        "panel": "#111827",
        "panel_alt": "#172033",
        "card": "#151F32",
        "border": "#1E293B",
        "muted": "#94A3B8",
        "text": "#E5E7EB",
        "text_strong": "#F8FAFC",
        "accent": "#38BDF8",
        "accent_dark": "#0284C7",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "input_bg": "#172033",
        "input_text": "#E5E7EB",
    },
    "light": {
        "appearance": "light",
        "bg": "#EEF2F7",
        "panel": "#FFFFFF",
        "panel_alt": "#F1F5F9",
        "card": "#FFFFFF",
        "border": "#E2E8F0",
        "muted": "#64748B",
        "text": "#0F172A",
        "text_strong": "#020617",
        "accent": "#0284C7",
        "accent_dark": "#0369A1",
        "success": "#15803D",
        "warning": "#B45309",
        "danger": "#B91C1C",
        "input_bg": "#F1F5F9",
        "input_text": "#0F172A",
    },
}

NAV_ITEMS = [
    ("ilanlar", "\U0001F697  Ilanlar"),
    ("araclarim", "\U0001F699  Araclarim"),
    ("ilanlarim", "\U0001F4CB  Ilanlarim"),
    ("ilan_olustur", "\u2795  Ilan Olustur"),
    ("kiralamalarim", "\U0001F511  Kiralamalarim"),
    ("destek", "\U0001F4AC  Destek Talebi"),
    ("bildirim", "\U0001F514  Bildirimler"),
    ("ayarlar", "\u2699\uFE0F  Ayarlar"),
]

ADMIN_ITEMS = [
    ("admin_users", "\U0001F465  Kullanici Yonetimi"),
    ("admin_listings", "\U0001F4DD  Ilan Onaylari"),
    ("admin_tickets", "\U0001F39F\uFE0F  Ticket Yonetimi"),
    ("admin_system", "\U0001F6E1\uFE0F  Sistem Yonetimi"),
]

PAGE_TITLES = {
    "ilanlar": "\U0001F697  Ilanlar",
    "araclarim": "\U0001F699  Araclarim",
    "ilanlarim": "\U0001F4CB  Ilanlarim",
    "ilan_olustur": "\u2795  Ilan Olustur",
    "kiralamalarim": "\U0001F511  Kiralamalarim",
    "destek": "\U0001F4AC  Destek Talebi",
    "bildirim": "\U0001F514  Bildirimler",
    "ayarlar": "\u2699\uFE0F  Ayarlar",
    "admin_users": "\U0001F465  Kullanici Yonetimi",
    "admin_listings": "\U0001F4DD  Ilan Onaylari",
    "admin_tickets": "\U0001F39F\uFE0F  Ticket Yonetimi",
    "admin_system": "\U0001F6E1\uFE0F  Sistem Yonetimi",
}


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Car Sharing Enterprise")
        self.geometry("1440x900")
        self.minsize(1200, 780)

        db_path = Path(__file__).resolve().parent.parent / "data" / "carshare.db"
        self.service = CarSharingService(db_path)
        self.service.admin_seed()

        self.current_user: dict | None = None
        self.active_page = ""
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.listings_cache: list[dict] = []
        self.image_cache: dict[str, ctk.CTkImage] = {}
        self.vehicle_preview_img: ctk.CTkImage | None = None
        self.detail_modal: ctk.CTkToplevel | None = None
        self.notification_cards: ctk.CTkScrollableFrame | None = None
        self._last_data_signature = ""
        self._auto_refresh_after_id: str | None = None
        self.selected_admin_user_id: int | None = None
        self.selected_admin_listing_id: int | None = None
        self.selected_admin_ticket_id: int | None = None
        self._admin_user_cards: dict[int, ctk.CTkFrame] = {}
        self._admin_listing_cards: dict[int, ctk.CTkFrame] = {}
        self._admin_ticket_cards: dict[int, ctk.CTkFrame] = {}
        self.system_stats_value_labels: dict[str, ctk.CTkLabel] = {}
        self.balance_modal: ctk.CTkToplevel | None = None
        self.ticket_modal: ctk.CTkToplevel | None = None
        self.listing_edit_modal: ctk.CTkToplevel | None = None
        self.rental_countdown_labels: dict[int, dict[str, ctk.CTkLabel]] = {}
        self._rental_tick_after_id: str | None = None
        self.reset_confirm_var: ctk.StringVar | None = None
        self._float_validate = (self.register(self._is_float_input), "%P")
        self._int_validate = (self.register(self._is_int_input), "%P")
        self._card_number_validate = (self.register(self._is_card_number_input), "%P")
        self._expiry_validate = (self.register(self._is_expiry_input), "%P")
        self._cvv_validate = (self.register(self._is_cvv_input), "%P")

        self.theme_name = ctk.StringVar(value="dark")
        self.auto_sync_var = ctk.BooleanVar(value=True)
        self.theme = THEMES[self.theme_name.get()]
        ctk.set_appearance_mode(self.theme["appearance"])
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.theme["bg"])

        self.auth_mode = ctk.StringVar(value="login")
        self.auth_container: ctk.CTkFrame | None = None
        self.main_container: ctk.CTkFrame | None = None

        self._show_auth_screen()
        self.bind("<Return>", self._on_enter_key)
        self.bind("<Escape>", self._on_escape_key)

    def _show_auth_screen(self) -> None:
        if self.main_container is not None:
            self.main_container.destroy()
            self.main_container = None
        if self.auth_container is not None:
            self.auth_container.destroy()
        self.auth_container = ctk.CTkFrame(self, fg_color=self.theme["bg"], corner_radius=0)
        self.auth_container.pack(fill="both", expand=True)
        self._build_auth_ui()

    def _build_auth_ui(self) -> None:
        shell = ctk.CTkScrollableFrame(self.auth_container, fg_color=self.theme["bg"])
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(shell, fg_color="transparent")
        content.grid(row=0, column=0, padx=24, pady=36)

        brand = ctk.CTkFrame(content, fg_color="transparent")
        brand.pack(fill="x", pady=(0, 18))
        ctk.CTkLabel(
            brand,
            text="CarShare Pro",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=34, weight="bold"),
        ).pack(anchor="center")
        ctk.CTkLabel(
            brand,
            text="Kurumsal arac kiralama ve ilan yonetim platformu",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=14),
        ).pack(anchor="center", pady=(6, 0))

        card = ctk.CTkFrame(
            content,
            width=520,
            fg_color=self.theme["panel"],
            corner_radius=22,
            border_width=1,
            border_color=self.theme["border"],
        )
        card.pack()
        card.pack_propagate(True)

        self.login_email = ctk.StringVar()
        self.login_pass = ctk.StringVar()
        self.reg_name = ctk.StringVar()
        self.reg_email = ctk.StringVar()
        self.reg_pass = ctk.StringVar()
        self.reg_license = ctk.StringVar()

        ctk.CTkSegmentedButton(
            card,
            values=["login", "register"],
            variable=self.auth_mode,
            command=self._render_auth_form,
            selected_color=self.theme["accent_dark"],
            selected_hover_color=self.theme["accent_dark"],
        ).pack(fill="x", padx=28, pady=(26, 16))

        self.auth_form = ctk.CTkFrame(card, fg_color="transparent", width=464)
        self.auth_form.pack(fill="x", padx=28, pady=(0, 24))
        self.auth_form.pack_propagate(True)
        self._render_auth_form("login")

    def _render_auth_form(self, mode: str) -> None:
        for child in self.auth_form.winfo_children():
            child.destroy()
        title = "Hesabina giris yap" if mode == "login" else "Yeni hesap olustur"
        subtitle = (
            "Enter tusu ile giris yapabilirsiniz."
            if mode == "login"
            else "Kayit sonrasi giris ekranina yonlendirilirsiniz."
        )
        ctk.CTkLabel(
            self.auth_form,
            text=title,
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(self.auth_form, text=subtitle, text_color=self.theme["muted"]).pack(
            anchor="w", pady=(0, 14)
        )
        if mode == "login":
            self._entry(self.auth_form, "Email", self.login_email)
            self._entry(self.auth_form, "Sifre", self.login_pass, hide=True)
            ctk.CTkButton(
                self.auth_form,
                text="Giris Yap",
                height=42,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                command=self._on_login,
            ).pack(fill="x", pady=(16, 4))
            return
        self._entry(self.auth_form, "Ad Soyad", self.reg_name)
        self._entry(self.auth_form, "Email", self.reg_email)
        self._entry(self.auth_form, "Sifre", self.reg_pass, hide=True)
        self._entry(self.auth_form, "Ehliyet No", self.reg_license)
        ctk.CTkButton(
            self.auth_form,
            text="Kayit Ol",
            height=42,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_register,
        ).pack(fill="x", pady=(16, 4))

    def _build_app_ui(self) -> None:
        if self.auth_container is not None:
            self.auth_container.destroy()
            self.auth_container = None
        if self.main_container is not None:
            self.main_container.destroy()
        self.pages = {}
        self.nav_buttons = {}
        self._admin_user_cards = {}
        self._admin_listing_cards = {}
        self._admin_ticket_cards = {}
        self.image_cache = {}

        self.configure(fg_color=self.theme["bg"])
        self.main_container = ctk.CTkFrame(self, fg_color=self.theme["bg"], corner_radius=0)
        self.main_container.pack(fill="both", expand=True)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self.main_container, width=270, fg_color=self.theme["panel"], corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.sidebar.grid_propagate(False)

        sidebar_top = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_top.pack(side="top", fill="x")
        ctk.CTkLabel(
            sidebar_top,
            text="CarShare Pro",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(20, 2))
        ctk.CTkLabel(
            sidebar_top,
            text="Enterprise Console",
            text_color=self.theme["muted"],
        ).pack(anchor="w", padx=22, pady=(0, 12))

        profile = ctk.CTkFrame(sidebar_top, fg_color=self.theme["panel_alt"], corner_radius=16)
        profile.pack(fill="x", padx=14, pady=(0, 12))
        initials = (self.current_user["ad"][:2].upper() if self.current_user else "")
        avatar = ctk.CTkLabel(
            profile,
            text=initials,
            text_color="#FFFFFF",
            fg_color=self.theme["accent_dark"],
            corner_radius=20,
            width=40,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=12, pady=12)
        ctk.CTkLabel(
            profile,
            text=self.current_user["ad"] if self.current_user else "",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(12, 0))
        ctk.CTkLabel(
            profile,
            text=(self.current_user["rol"].upper() if self.current_user else ""),
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 12))

        sidebar_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_bottom.pack(side="bottom", fill="x")
        sync_label = ctk.CTkLabel(
            sidebar_bottom,
            text="Otomatik senkronizasyon: acik",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=220,
        )
        sync_label.pack(anchor="w", padx=22, pady=(8, 14))
        self.sync_status_label = sync_label
        self._update_sync_label()

        self.nav_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color=self.theme["panel"],
            scrollbar_button_color=self.theme["accent_dark"],
            scrollbar_button_hover_color=self.theme["accent"],
        )
        self.nav_scroll.pack(side="top", fill="both", expand=True, padx=(0, 0), pady=(0, 0))

        ctk.CTkLabel(
            self.nav_scroll,
            text="ANA ISLEMLER",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(4, 6))
        for key, label in NAV_ITEMS:
            self._nav_button(key, label)

        if self.current_user and self.current_user["rol"] == "admin":
            ctk.CTkLabel(
                self.nav_scroll,
                text="ADMIN",
                text_color=self.theme["muted"],
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(anchor="w", padx=14, pady=(18, 6))
            for key, label in ADMIN_ITEMS:
                self._nav_button(key, label)

        self.header = ctk.CTkFrame(self.main_container, height=78, fg_color=self.theme["bg"], corner_radius=0)
        self.header.grid(row=0, column=1, sticky="ew")
        self.header.grid_propagate(False)
        self.page_title = ctk.CTkLabel(
            self.header,
            text="",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.page_title.pack(side="left", padx=22, pady=18)
        self.balance_label = ctk.CTkLabel(
            self.header,
            text="",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.balance_label.pack(side="right", padx=22)

        self.content = ctk.CTkFrame(self.main_container, fg_color=self.theme["bg"], corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(0, 16))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        page_keys = [item[0] for item in NAV_ITEMS]
        if self.current_user and self.current_user["rol"] == "admin":
            page_keys.extend(item[0] for item in ADMIN_ITEMS)
        for key in page_keys:
            page = ctk.CTkFrame(self.content, fg_color=self.theme["bg"], corner_radius=0)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page

        self._build_listings_page(self.pages["ilanlar"])
        self._build_my_vehicles_page(self.pages["araclarim"])
        self._build_my_listings_page(self.pages["ilanlarim"])
        self._build_create_listing_page(self.pages["ilan_olustur"])
        self._build_my_rentals_page(self.pages["kiralamalarim"])
        self._build_support_page(self.pages["destek"])
        self._build_notifications_page(self.pages["bildirim"])
        self._build_settings_page(self.pages["ayarlar"])
        if "admin_users" in self.pages:
            self._build_admin_users_page(self.pages["admin_users"])
            self._build_admin_listings_page(self.pages["admin_listings"])
            self._build_admin_tickets_page(self.pages["admin_tickets"])
            self._build_admin_system_page(self.pages["admin_system"])

        self._refresh_all()
        self._show_page("ilanlar")
        self._schedule_auto_refresh()

    def _nav_button(self, key: str, text: str) -> None:
        button = ctk.CTkButton(
            self.nav_scroll,
            text=text,
            anchor="w",
            height=42,
            corner_radius=12,
            fg_color="transparent",
            hover_color=self.theme["panel_alt"],
            text_color=self.theme["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda k=key: self._show_page(k),
        )
        button.pack(fill="x", padx=14, pady=4)
        self.nav_buttons[key] = button

    def _show_page(self, key: str) -> None:
        if key not in self.pages:
            return
        self.active_page = key
        self.page_title.configure(text=PAGE_TITLES.get(key, "Panel"))
        for page_key, button in self.nav_buttons.items():
            button.configure(
                fg_color=self.theme["accent_dark"] if page_key == key else "transparent",
                text_color="#FFFFFF" if page_key == key else self.theme["text"],
            )
        self.pages[key].tkraise()
        if key == "admin_system":
            self._render_system_stats()

    def _build_listings_page(self, page: ctk.CTkFrame) -> None:
        toolbar = self._panel(page)
        toolbar.pack(fill="x", padx=4, pady=(0, 12))
        self.filter_text = ctk.StringVar()
        self.sort_var = ctk.StringVar(value="En yeni")
        self.filter_text.trace_add("write", lambda *_: self._render_listing_cards())
        ctk.CTkEntry(
            toolbar,
            textvariable=self.filter_text,
            placeholder_text="Baslik, konum veya arac ara",
            width=360,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        ).pack(side="left", padx=14, pady=14)
        ctk.CTkComboBox(
            toolbar,
            values=["En yeni", "Fiyat artan", "Fiyat azalan", "Puan azalan"],
            variable=self.sort_var,
            command=lambda _v: self._render_listing_cards(),
            width=160,
            state="readonly",
        ).pack(side="left", padx=8)
        ctk.CTkLabel(
            toolbar,
            text="\u2139\uFE0F  Detay icin Detay butonunu kullanin.",
            text_color=self.theme["muted"],
        ).pack(side="right", padx=14)

        self.cards_area = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        self.cards_area.pack(fill="both", expand=True)

    def _build_my_vehicles_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        form = self._panel(scroll)
        form.pack(fill="x", padx=4, pady=(0, 14))
        self._section_title(
            form,
            "Yeni Arac Ekle",
            "Aracinizi kaydedin; ilan olusturma ayri sayfada yapilir.",
        )
        self.car_brand = ctk.StringVar()
        self.car_model = ctk.StringVar()
        self.car_km = ctk.StringVar()
        self.car_image = ctk.StringVar()
        grid = ctk.CTkFrame(form, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(4, 14))
        self._grid_entry(grid, "Marka", self.car_brand, 0)
        self._grid_entry(grid, "Model", self.car_model, 1)
        self._grid_entry(grid, "Kilometre", self.car_km, 2, validate=self._int_validate)
        self._grid_entry(grid, "Gorsel", self.car_image, 3, width=300)
        ctk.CTkButton(
            grid,
            text="\U0001F4C2  Dosya Sec",
            command=self._pick_vehicle_image,
            fg_color=self.theme["panel_alt"],
            text_color=self.theme["text"],
            hover_color=self.theme["border"],
        ).grid(row=2, column=3, padx=8, pady=(0, 8), sticky="w")
        self.preview_label = ctk.CTkLabel(
            grid,
            text="Onizleme",
            width=160,
            height=100,
            fg_color=self.theme["panel_alt"],
            text_color=self.theme["muted"],
            corner_radius=12,
        )
        self.preview_label.grid(row=1, column=4, rowspan=2, padx=12, pady=6)
        ctk.CTkButton(
            grid,
            text="\u2795  Ekle",
            width=98,
            height=34,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_add_car,
        ).grid(row=0, column=5, padx=12, pady=8, sticky="e")

        self.vehicle_cards = ctk.CTkFrame(scroll, fg_color="transparent")
        self.vehicle_cards.pack(fill="both", expand=True)

    def _build_create_listing_page(self, page: ctk.CTkFrame) -> None:
        panel = self._panel(page)
        panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            panel,
            "Ilan Olustur",
            "Sadece kayitli araclariniz icin ilan acabilirsiniz. Ilan admin onayindan sonra yayina cikar.",
        )
        self.user_vehicle = ctk.StringVar()
        self.list_title = ctk.StringVar()
        self.list_price = ctk.StringVar()
        self.list_location = ctk.StringVar()

        grid = ctk.CTkFrame(panel, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(2, 10))
        ctk.CTkLabel(grid, text="Arac", text_color=self.theme["muted"]).grid(
            row=0, column=0, padx=8, pady=6, sticky="w"
        )
        self.cmb_user_vehicle = ctk.CTkComboBox(
            grid, variable=self.user_vehicle, values=["-"], width=300, state="readonly"
        )
        self.cmb_user_vehicle.grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self._grid_entry(grid, "Baslik", self.list_title, 1, width=240)
        price_entry = self._grid_entry(grid, "Saatlik Ucret", self.list_price, 2, width=140, validate=self._float_validate)
        price_entry.configure(placeholder_text="100.00")
        self._grid_entry(grid, "Konum", self.list_location, 3, width=180)
        ctk.CTkLabel(grid, text="Aciklama", text_color=self.theme["muted"]).grid(
            row=2, column=0, padx=8, pady=(12, 6), sticky="w"
        )
        self.list_desc = ctk.CTkTextbox(grid, height=140, width=780, fg_color=self.theme["input_bg"], text_color=self.theme["input_text"])
        self.list_desc.grid(row=3, column=0, columnspan=4, padx=8, pady=(0, 10), sticky="ew")
        ctk.CTkButton(
            grid,
            text="\U0001F4E4  Gonder",
            width=110,
            height=34,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_create_listing,
        ).grid(row=0, column=4, padx=14, pady=8, sticky="e")

    def _build_my_listings_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        header = self._panel(scroll)
        header.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            header,
            "\U0001F4CB  Ilanlarim",
            "Olusturdugunuz tum ilanlari buradan goruntuleyin ve duzenleyin. Duzenlenen ilan tekrar admin onayina dusurulur.",
        )
        info_row = ctk.CTkFrame(header, fg_color="transparent")
        info_row.pack(fill="x", padx=14, pady=(0, 14))
        self.my_listings_count_label = ctk.CTkLabel(
            info_row,
            text="Toplam: 0 ilan",
            text_color=self.theme["accent"],
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.my_listings_count_label.pack(side="left")

        self.my_listings_area = ctk.CTkFrame(scroll, fg_color="transparent")
        self.my_listings_area.pack(fill="both", expand=True)

    def _refresh_my_listings(self) -> None:
        if not hasattr(self, "my_listings_area") or not self.current_user:
            return
        for child in self.my_listings_area.winfo_children():
            child.destroy()
        items = self.service.kullanici_ilanlari_getir(self.current_user["kullanici_id"])
        if hasattr(self, "my_listings_count_label"):
            self.my_listings_count_label.configure(text=f"Toplam: {len(items)} ilan")
        if not items:
            empty = self._panel(self.my_listings_area)
            empty.pack(fill="x", padx=4, pady=8)
            ctk.CTkLabel(
                empty,
                text="Henuz olusturdugunuz bir ilan yok.\nIlan Olustur sayfasindan yeni bir ilan acabilirsiniz.",
                text_color=self.theme["muted"],
                justify="left",
            ).pack(anchor="w", padx=14, pady=18)
            return

        status_meta = {
            "pending": ("\u23F3  Onay bekliyor", self.theme["warning"]),
            "approved": ("\u2705  Yayinda", self.theme["success"]),
            "rejected": ("\u26D4  Reddedildi", self.theme["danger"]),
        }

        for item in items:
            card = self._panel(self.my_listings_area)
            card.pack(fill="x", padx=4, pady=8)
            card.grid_columnconfigure(2, weight=1)

            thumb = ctk.CTkLabel(
                card,
                text="",
                image=self._image_for_path(item.get("gorsel_yolu") or "", (160, 110)),
                width=160,
                height=110,
                fg_color=self.theme["panel_alt"],
                corner_radius=12,
            )
            thumb.grid(row=0, column=0, rowspan=3, padx=14, pady=14)

            label_text, badge_color = status_meta.get(
                item["durum"], (item["durum"].upper(), self.theme["muted"])
            )
            ctk.CTkLabel(
                card,
                text=label_text,
                text_color="#FFFFFF",
                fg_color=badge_color,
                corner_radius=10,
                width=140,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=1, padx=8, pady=(14, 4), sticky="w")

            ctk.CTkLabel(
                card,
                text=f"#{item['ilan_id']}  -  {item['baslik']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w",
            ).grid(row=0, column=2, padx=8, pady=(14, 4), sticky="w")

            ctk.CTkLabel(
                card,
                text=(
                    f"\U0001F697  {item['marka']} {item['model']}  |  "
                    f"\U0001F4CD  {item['konum'] or '-'}  |  "
                    f"\U0001F4B0  {float(item['saatlik_ucret']):.2f} TL/sa"
                ),
                text_color=self.theme["muted"],
                anchor="w",
            ).grid(row=1, column=1, columnspan=2, padx=8, pady=(0, 4), sticky="w")

            preview = item["aciklama"]
            if len(preview) > 140:
                preview = preview[:140] + "..."
            ctk.CTkLabel(
                card,
                text=preview or "-",
                text_color=self.theme["text"],
                wraplength=620,
                justify="left",
                anchor="w",
            ).grid(row=2, column=1, columnspan=2, padx=8, pady=(0, 14), sticky="w")

            action_col = ctk.CTkFrame(card, fg_color="transparent")
            action_col.grid(row=0, column=3, rowspan=3, padx=14, pady=14)
            ctk.CTkButton(
                action_col,
                text="\u270F\uFE0F  Duzenle",
                width=140,
                height=34,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda i=item: self._open_listing_edit(i),
            ).pack(pady=(0, 6))
            ctk.CTkButton(
                action_col,
                text="\U0001F50D  Detay",
                width=140,
                height=32,
                fg_color=self.theme["panel_alt"],
                text_color=self.theme["text"],
                hover_color=self.theme["border"],
                command=lambda i=item: self._open_listing_detail(i),
            ).pack()

    def _open_listing_edit(self, listing: dict) -> None:
        if self.listing_edit_modal and self.listing_edit_modal.winfo_exists():
            self.listing_edit_modal.destroy()
        modal = ctk.CTkToplevel(self)
        self.listing_edit_modal = modal
        modal.title(f"Ilan Duzenle - #{listing['ilan_id']}")
        modal.geometry("640x680")
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=self.theme["bg"])

        shell = ctk.CTkScrollableFrame(modal, fg_color=self.theme["bg"])
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        info = self._panel(shell)
        info.pack(fill="x", pady=(0, 12))
        info.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            info,
            text="",
            image=self._image_for_path(listing.get("gorsel_yolu") or "", (140, 95)),
            width=140,
            height=95,
            fg_color=self.theme["panel_alt"],
            corner_radius=12,
        ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
        ctk.CTkLabel(
            info,
            text=f"\U0001F697  {listing['marka']} {listing['model']}",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 0))
        ctk.CTkLabel(
            info,
            text=(
                f"#{listing['ilan_id']}  |  Mevcut durum: {listing['durum'].upper()}  |  "
                f"Olusturma: {listing['created_at']}"
            ),
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 14))

        form = self._panel(shell)
        form.pack(fill="both", expand=True)
        self._section_title(
            form,
            "\u270F\uFE0F  Ilan Bilgileri",
            "Degisiklik kaydedildikten sonra ilan tekrar admin onayina dusurulur ve onaylanana kadar yayindan kaldirilir.",
        )

        title_var = ctk.StringVar(value=listing["baslik"])
        price_var = ctk.StringVar(value=f"{float(listing['saatlik_ucret']):.2f}")
        location_var = ctk.StringVar(value=listing["konum"] or "")

        title_row = ctk.CTkFrame(form, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(title_row, text="Baslik", text_color=self.theme["muted"]).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        ctk.CTkEntry(
            title_row,
            textvariable=title_var,
            width=560,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        ).pack(anchor="w", padx=8, pady=(0, 8))

        meta_row = ctk.CTkFrame(form, fg_color="transparent")
        meta_row.pack(fill="x", padx=14, pady=(0, 4))
        price_col = ctk.CTkFrame(meta_row, fg_color="transparent")
        price_col.pack(side="left", padx=(0, 24))
        ctk.CTkLabel(price_col, text="Saatlik Ucret", text_color=self.theme["muted"]).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        money_holder = ctk.CTkFrame(price_col, fg_color="transparent")
        money_holder.pack(anchor="w", padx=4, pady=(0, 8))
        self._money_entry(money_holder, price_var, width=180)
        loc_col = ctk.CTkFrame(meta_row, fg_color="transparent")
        loc_col.pack(side="left")
        ctk.CTkLabel(loc_col, text="Konum", text_color=self.theme["muted"]).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        ctk.CTkEntry(
            loc_col,
            textvariable=location_var,
            width=300,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        ).pack(anchor="w", padx=8, pady=(0, 8))

        ctk.CTkLabel(form, text="Aciklama", text_color=self.theme["muted"]).pack(
            anchor="w", padx=22, pady=(4, 4)
        )
        desc_box = ctk.CTkTextbox(
            form,
            height=160,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        desc_box.pack(fill="x", padx=22, pady=(0, 10))
        desc_box.insert("1.0", listing["aciklama"] or "")

        warn = ctk.CTkLabel(
            form,
            text=(
                "\u26A0\uFE0F  Aktif kiralamasi bulunan ilan duzenlenemez. Kaydettiginizde "
                "ilan otomatik olarak 'pending' (onay bekliyor) durumuna alinir."
            ),
            text_color=self.theme["warning"],
            wraplength=560,
            justify="left",
        )
        warn.pack(anchor="w", padx=22, pady=(0, 10))

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(4, 14))
        ctk.CTkButton(
            actions,
            text="Iptal",
            width=110,
            fg_color=self.theme["panel_alt"],
            text_color=self.theme["text"],
            hover_color=self.theme["border"],
            command=modal.destroy,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="\U0001F4BE  Degisiklikleri Kaydet",
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._submit_listing_edit(
                listing["ilan_id"],
                title_var.get(),
                desc_box.get("1.0", "end"),
                price_var.get(),
                location_var.get(),
                modal,
            ),
        ).pack(side="right")

    def _submit_listing_edit(
        self,
        ilan_id: int,
        baslik: str,
        aciklama: str,
        price: str,
        konum: str,
        modal: ctk.CTkToplevel,
    ) -> None:
        try:
            tutar = self._safe_float(price)
            self.service.ilan_guncelle(
                ilan_id,
                self.current_user["kullanici_id"],
                baslik,
                aciklama,
                tutar,
                konum,
            )
            if modal.winfo_exists():
                modal.destroy()
            self._refresh_all()
            msg.showinfo(
                "Basarili",
                "Ilan guncellendi. Yayina cikabilmesi icin admin onayi bekliyor.",
            )
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _build_my_rentals_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        header = self._panel(scroll)
        header.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            header,
            "\U0001F511  Kiralamalarim",
            "Aktif kiralamalarinizdaki kalan kullanim suresini canli olarak takip edin. Sure dolduktan sonra kiralama otomatik olarak tamamlanir.",
        )
        info_row = ctk.CTkFrame(header, fg_color="transparent")
        info_row.pack(fill="x", padx=14, pady=(0, 14))
        self.rentals_active_count = ctk.CTkLabel(
            info_row,
            text="Aktif: 0",
            text_color=self.theme["success"],
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.rentals_active_count.pack(side="left", padx=(0, 18))
        self.rentals_total_count = ctk.CTkLabel(
            info_row,
            text="Toplam: 0",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=13),
        )
        self.rentals_total_count.pack(side="left")

        self.rentals_active_area = ctk.CTkFrame(scroll, fg_color="transparent")
        self.rentals_active_area.pack(fill="x", expand=False, pady=(0, 6))

        history_panel = self._panel(scroll)
        history_panel.pack(fill="x", padx=4, pady=(8, 6))
        self._section_title(
            history_panel,
            "\U0001F4DC  Gecmis Kiralamalar",
            "Tamamlanmis kiralamalariniz arsivlenir. Suresi dolan kayitlari buradan inceleyebilirsiniz.",
        )
        self.rentals_history_area = ctk.CTkFrame(history_panel, fg_color="transparent")
        self.rentals_history_area.pack(fill="x", padx=14, pady=(0, 14))

    def _refresh_my_rentals(self) -> None:
        if not hasattr(self, "rentals_active_area") or not self.current_user:
            return
        for child in self.rentals_active_area.winfo_children():
            child.destroy()
        for child in self.rentals_history_area.winfo_children():
            child.destroy()
        self.rental_countdown_labels = {}

        rentals = self.service.kullanici_kiralamalari(self.current_user["kullanici_id"])
        active = [r for r in rentals if r["durum"] == "active"]
        history = [r for r in rentals if r["durum"] != "active"]
        if hasattr(self, "rentals_active_count"):
            self.rentals_active_count.configure(text=f"Aktif: {len(active)}")
        if hasattr(self, "rentals_total_count"):
            self.rentals_total_count.configure(text=f"Toplam: {len(rentals)}")

        if not active:
            empty = self._panel(self.rentals_active_area)
            empty.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(
                empty,
                text="Aktif bir kiralamaniz yok. Ilanlar sayfasindan bir arac kiralayabilirsiniz.",
                text_color=self.theme["muted"],
                anchor="w",
            ).pack(anchor="w", padx=14, pady=18)
        else:
            for rental in active:
                self._render_active_rental_card(rental)

        if not history:
            ctk.CTkLabel(
                self.rentals_history_area,
                text="Henuz tamamlanmis bir kiralama yok.",
                text_color=self.theme["muted"],
                anchor="w",
            ).pack(anchor="w", padx=4, pady=10)
        else:
            for rental in history[:20]:
                self._render_history_rental_card(rental)

        self._tick_rental_countdowns()

    def _render_active_rental_card(self, rental: dict) -> None:
        card = ctk.CTkFrame(
            self.rentals_active_area,
            fg_color=self.theme["panel"],
            corner_radius=18,
            border_width=2,
            border_color=self.theme["accent_dark"],
        )
        card.pack(fill="x", padx=4, pady=8)
        card.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            card,
            text="",
            image=self._image_for_path(rental.get("gorsel_yolu") or "", (200, 130)),
            width=200,
            height=130,
            fg_color=self.theme["panel_alt"],
            corner_radius=14,
        ).grid(row=0, column=0, rowspan=4, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text="\U0001F7E2  AKTIF",
            text_color="#FFFFFF",
            fg_color=self.theme["success"],
            corner_radius=10,
            width=110,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=1, padx=8, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=f"#{rental['kiralama_id']}  -  {rental['baslik']}",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=2, padx=8, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=(
                f"\U0001F697  {rental['marka']} {rental['model']}  ({int(rental['kilometre'])} km)  |  "
                f"\U0001F464  {rental['sahip_ad']}"
            ),
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=1, column=1, columnspan=2, padx=8, pady=(0, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=(
                f"\U0001F4CD  {rental['konum'] or '-'}  |  "
                f"\U0001F4B0  {float(rental['toplam_tutar']):.2f} TL  |  "
                f"\u23F1\uFE0F  {int(rental['kira_saat'])} saat"
            ),
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=2, column=1, columnspan=2, padx=8, pady=(0, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=f"Baslangic: {rental['baslangic_saati']}",
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=3, column=1, columnspan=2, padx=8, pady=(0, 12), sticky="w")

        countdown_panel = ctk.CTkFrame(card, fg_color=self.theme["panel_alt"], corner_radius=14)
        countdown_panel.grid(row=0, column=3, rowspan=4, padx=16, pady=16, sticky="ns")
        ctk.CTkLabel(
            countdown_panel,
            text="\u23F3  KALAN SURE",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=14, pady=(12, 4))
        digits_row = ctk.CTkFrame(countdown_panel, fg_color="transparent")
        digits_row.pack(padx=14, pady=(0, 8))
        units = [("days", "GUN"), ("hours", "SAAT"), ("minutes", "DAK"), ("seconds", "SN")]
        unit_labels: dict[str, ctk.CTkLabel] = {}
        for idx, (key, lbl) in enumerate(units):
            cell = ctk.CTkFrame(digits_row, fg_color=self.theme["bg"], corner_radius=10)
            cell.grid(row=0, column=idx, padx=4)
            value_lbl = ctk.CTkLabel(
                cell,
                text="00",
                text_color=self.theme["accent"],
                font=ctk.CTkFont(size=24, weight="bold"),
                width=58,
            )
            value_lbl.pack(padx=8, pady=(8, 2))
            ctk.CTkLabel(
                cell,
                text=lbl,
                text_color=self.theme["muted"],
                font=ctk.CTkFont(size=10, weight="bold"),
            ).pack(padx=8, pady=(0, 8))
            unit_labels[key] = value_lbl

        progress = ctk.CTkProgressBar(
            countdown_panel,
            progress_color=self.theme["accent_dark"],
            fg_color=self.theme["bg"],
            height=10,
            width=260,
        )
        progress.set(0)
        progress.pack(padx=14, pady=(2, 6))
        status_lbl = ctk.CTkLabel(
            countdown_panel,
            text="",
            text_color=self.theme["muted"],
            font=ctk.CTkFont(size=11),
        )
        status_lbl.pack(padx=14, pady=(0, 4))

        end_btn = ctk.CTkButton(
            countdown_panel,
            text="\U0001F6D1  Kiralamayi Bitir",
            width=210,
            height=34,
            fg_color=self.theme["danger"],
            hover_color=self.theme["accent_dark"],
            command=lambda rid=rental["kiralama_id"]: self._on_end_rental(rid),
        )
        end_btn.pack(padx=14, pady=(4, 14))

        baslangic = self._parse_dt(rental["baslangic_saati"])
        end_time = baslangic + timedelta(hours=int(rental["kira_saat"])) if baslangic else None
        self.rental_countdown_labels[int(rental["kiralama_id"])] = {
            "labels": unit_labels,
            "progress": progress,
            "status": status_lbl,
            "end_time": end_time,
            "start_time": baslangic,
            "kira_saat": int(rental["kira_saat"]),
        }

    def _render_history_rental_card(self, rental: dict) -> None:
        card = ctk.CTkFrame(self.rentals_history_area, fg_color=self.theme["panel_alt"], corner_radius=12)
        card.pack(fill="x", padx=2, pady=4)
        card.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(
            card,
            text=("\u2705  TAMAMLANDI" if rental["durum"] == "completed" else rental["durum"].upper()),
            text_color="#FFFFFF",
            fg_color=self.theme["muted"],
            corner_radius=8,
            width=140,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkLabel(
            card,
            text=f"#{rental['kiralama_id']}  -  {rental['baslik']}",
            text_color=self.theme["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=6, pady=10, sticky="w")
        ctk.CTkLabel(
            card,
            text=(
                f"{rental['marka']} {rental['model']}  |  "
                f"{int(rental['kira_saat'])} sa  |  "
                f"{float(rental['toplam_tutar']):.2f} TL  |  "
                f"{rental['baslangic_saati']} -> {rental['bitis_saati'] or '-'}"
            ),
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=0, column=2, padx=6, pady=10, sticky="w")

    def _parse_dt(self, value: str | None):
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _tick_rental_countdowns(self) -> None:
        if self._rental_tick_after_id is not None:
            try:
                self.after_cancel(self._rental_tick_after_id)
            except Exception:  # noqa: BLE001
                pass
            self._rental_tick_after_id = None
        if not self.rental_countdown_labels:
            return
        now = datetime.now()
        finished_ids: list[int] = []
        for rid, ctx in list(self.rental_countdown_labels.items()):
            end_time = ctx.get("end_time")
            start_time = ctx.get("start_time")
            kira_saat = int(ctx.get("kira_saat") or 0)
            labels: dict[str, ctk.CTkLabel] = ctx.get("labels", {})
            progress: ctk.CTkProgressBar = ctx.get("progress")
            status: ctk.CTkLabel = ctx.get("status")
            if not end_time or not start_time or kira_saat <= 0:
                continue
            try:
                if not all(lbl.winfo_exists() for lbl in labels.values()):
                    finished_ids.append(rid)
                    continue
            except Exception:  # noqa: BLE001
                finished_ids.append(rid)
                continue
            remaining = (end_time - now).total_seconds()
            total = float(kira_saat) * 3600.0
            if remaining <= 0:
                for key in ("days", "hours", "minutes", "seconds"):
                    if key in labels:
                        labels[key].configure(text="00", text_color=self.theme["danger"])
                if progress is not None:
                    progress.set(1.0)
                if status is not None:
                    status.configure(text="Kiralama suresi doldu, sonlandirin.", text_color=self.theme["danger"])
                continue
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            for key, val in (("days", days), ("hours", hours), ("minutes", minutes), ("seconds", seconds)):
                if key in labels:
                    labels[key].configure(text=f"{val:02d}")
            elapsed = max(0.0, total - remaining)
            ratio = max(0.0, min(1.0, elapsed / total))
            if progress is not None:
                progress.set(ratio)
            if status is not None:
                pct = int(ratio * 100)
                status.configure(
                    text=f"%{pct} kullanildi  |  Sona erme: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    text_color=self.theme["muted"],
                )
        for rid in finished_ids:
            self.rental_countdown_labels.pop(rid, None)
        if self.rental_countdown_labels:
            self._rental_tick_after_id = self.after(1000, self._tick_rental_countdowns)

    def _on_end_rental(self, kiralama_id: int) -> None:
        if not self.current_user:
            return
        if not msg.askyesno(
            "Kiralamayi Bitir",
            "Bu kiralamayi sonlandirmak istediginize emin misiniz?",
        ):
            return
        try:
            self.service.kiralama_bitir(kiralama_id, self.current_user["kullanici_id"])
            self._refresh_all()
            msg.showinfo("Tamamlandi", "Kiralama basarili sekilde sonlandirildi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _build_support_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        form = self._panel(scroll)
        form.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            form,
            "Destek Talebi Ac",
            "Tek konu icin tek ticket acin; yanitlari asagidaki kartlardan takip edin.",
        )
        self.ticket_title = ctk.StringVar()
        self.ticket_msg = ctk.StringVar()
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))
        self._grid_entry(row, "Baslik", self.ticket_title, 0, width=260)
        self._grid_entry(row, "Mesaj", self.ticket_msg, 1, width=560)
        ctk.CTkButton(
            row,
            text="\U0001F39F\uFE0F  Ac",
            width=110,
            height=34,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_create_ticket,
        ).grid(row=0, column=2, padx=12, pady=6, sticky="e")

        self.support_cards_area = ctk.CTkFrame(scroll, fg_color="transparent")
        self.support_cards_area.pack(fill="both", expand=True, pady=(4, 4))

    def _build_notifications_page(self, page: ctk.CTkFrame) -> None:
        summary = self._panel(page)
        summary.pack(fill="x", padx=4, pady=(0, 12))
        self.notification_summary = ctk.CTkLabel(
            summary,
            text="Bildirimler yukleniyor...",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.notification_summary.pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkLabel(
            summary,
            text="Sistem hareketleri, ilan onaylari ve ticket yanitlari burada kart olarak gorunur.",
            text_color=self.theme["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 14))

        self.notification_cards = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        self.notification_cards.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_settings_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        appearance = self._panel(scroll)
        appearance.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            appearance,
            "\U0001F3A8  Gorunum",
            "Tema modunu degistirin; uygulama anlik olarak yeniden cizilir.",
        )
        appearance_row = ctk.CTkFrame(appearance, fg_color="transparent")
        appearance_row.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkLabel(
            appearance_row,
            text="Tema modu",
            text_color=self.theme["muted"],
        ).pack(side="left", padx=(0, 12))
        ctk.CTkSegmentedButton(
            appearance_row,
            values=["dark", "light"],
            variable=self.theme_name,
            command=self._on_change_theme,
            selected_color=self.theme["accent_dark"],
            selected_hover_color=self.theme["accent"],
        ).pack(side="left")

        sync_panel = self._panel(scroll)
        sync_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            sync_panel,
            "\U0001F501  Senkronizasyon",
            "Otomatik senkronizasyon kapaliyken sayfalar veriyi yalnizca etkilesimde gunceller.",
        )
        sync_row = ctk.CTkFrame(sync_panel, fg_color="transparent")
        sync_row.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkSwitch(
            sync_row,
            text="Otomatik yenileme",
            variable=self.auto_sync_var,
            command=self._on_toggle_auto_sync,
            progress_color=self.theme["accent_dark"],
        ).pack(side="left")
        ctk.CTkButton(
            sync_row,
            text="\U0001F504  Simdi Yenile",
            width=160,
            height=34,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_manual_refresh,
        ).pack(side="left", padx=18)
        self.last_refresh_label = ctk.CTkLabel(
            sync_row,
            text="Son yenileme: -",
            text_color=self.theme["muted"],
        )
        self.last_refresh_label.pack(side="left", padx=12)

        balance_panel = self._panel(scroll)
        balance_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            balance_panel,
            "\U0001F4B3  Bakiye Yukleme",
            "Sanal kart simulatoru ile guvenli sekilde bakiye yukleyin.",
        )
        balance_info = ctk.CTkLabel(
            balance_panel,
            text="Mevcut bakiye: -",
            text_color=self.theme["accent"],
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        balance_info.pack(anchor="w", padx=14, pady=(0, 4))
        self.settings_balance_label = balance_info
        balance_row = ctk.CTkFrame(balance_panel, fg_color="transparent")
        balance_row.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkButton(
            balance_row,
            text="\U0001F4B3  Kart ile Bakiye Yukle",
            width=220,
            height=38,
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_balance_simulator,
        ).pack(side="left")
        ctk.CTkLabel(
            balance_row,
            text="VISA / MASTER / TROY destekli (simulasyon)",
            text_color=self.theme["muted"],
        ).pack(side="left", padx=14)

        about_panel = self._panel(scroll)
        about_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            about_panel,
            "\u2139\uFE0F  Hakkinda",
            "CarShare Pro Enterprise Edition. Versiyon 1.5.0",
        )
        ctk.CTkLabel(
            about_panel,
            text="Profesyonel arac paylasim ve ilan platformu.",
            text_color=self.theme["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 16))

        logout_panel = self._panel(scroll)
        logout_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            logout_panel,
            "\U0001F511  Oturum",
            "Hesabinizdan guvenli sekilde cikis yapin.",
        )
        logout_row = ctk.CTkFrame(logout_panel, fg_color="transparent")
        logout_row.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkButton(
            logout_row,
            text="\U0001F6AA  Cikis Yap",
            width=180,
            height=38,
            fg_color=self.theme["danger"],
            hover_color="#7F1D1D",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._logout,
        ).pack(side="left")

    def _build_admin_users_page(self, page: ctk.CTkFrame) -> None:
        actions = self._panel(page)
        actions.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            actions,
            "Kullanici Yonetimi",
            "Listeden bir kullanici secin, ardindan rol/durum guncelleyin veya bakiye yukleyin.",
        )
        self.role_var = ctk.StringVar(value="user")
        self.active_var = ctk.StringVar(value="Aktif")
        self.balance_var = ctk.StringVar()
        action_row = ctk.CTkFrame(actions, fg_color="transparent")
        action_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(action_row, text="Rol", text_color=self.theme["muted"]).pack(side="left", padx=(0, 4))
        ctk.CTkComboBox(
            action_row,
            values=["user", "admin"],
            variable=self.role_var,
            width=120,
            state="readonly",
        ).pack(side="left", padx=8)
        ctk.CTkLabel(action_row, text="Durum", text_color=self.theme["muted"]).pack(side="left", padx=(12, 4))
        ctk.CTkComboBox(
            action_row,
            values=["Aktif", "Pasif"],
            variable=self.active_var,
            width=110,
            state="readonly",
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            action_row,
            text="\U0001F501  Rol/Durum Guncelle",
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            command=self._on_admin_update_user,
        ).pack(side="left", padx=8)
        balance_row = ctk.CTkFrame(actions, fg_color="transparent")
        balance_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(balance_row, text="Bakiye", text_color=self.theme["muted"]).pack(side="left", padx=(0, 4))
        self._money_entry(balance_row, self.balance_var, width=160)
        ctk.CTkButton(
            balance_row,
            text="\U0001F4B0  Bakiye Yukle",
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            command=self._on_admin_load_balance,
        ).pack(side="left", padx=12)

        self.admin_user_cards_area = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        self.admin_user_cards_area.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _build_admin_listings_page(self, page: ctk.CTkFrame) -> None:
        actions = self._panel(page)
        actions.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            actions,
            "Ilan Onaylari",
            "Bekleyen, onaylanan ve reddedilen tum ilanlari kart gorunumunde yonetin.",
        )
        action_row = ctk.CTkFrame(actions, fg_color="transparent")
        action_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(
            action_row,
            text="\u2705  Onayla",
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            command=lambda: self._on_admin_listing_status("approved"),
        ).pack(side="left", padx=4, pady=4)
        ctk.CTkButton(
            action_row,
            text="\u274C  Reddet",
            fg_color=self.theme["danger"],
            hover_color="#7F1D1D",
            command=lambda: self._on_admin_listing_status("rejected"),
        ).pack(side="left", padx=4, pady=4)
        ctk.CTkButton(
            action_row,
            text="\u23F8\uFE0F  Beklet",
            fg_color=self.theme["warning"],
            hover_color="#92400E",
            command=lambda: self._on_admin_listing_status("pending"),
        ).pack(side="left", padx=4, pady=4)

        self.admin_listing_cards_area = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        self.admin_listing_cards_area.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _build_admin_tickets_page(self, page: ctk.CTkFrame) -> None:
        header = self._panel(page)
        header.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            header,
            "\U0001F39F\uFE0F  Ticket Yonetimi",
            "Bir ticket karti uzerindeki 'Ac' butonu ile detayini acin; yanit ve durum guncellemesi modal icinden yapilir.",
        )

        self.admin_ticket_cards_area = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        self.admin_ticket_cards_area.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _build_admin_system_page(self, page: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(page, fg_color=self.theme["bg"])
        scroll.pack(fill="both", expand=True)

        stats_panel = self._panel(scroll)
        stats_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            stats_panel,
            "\U0001F4CA  Sistem Ozeti",
            "Veritabanindaki guncel kayit sayilarini takip edin.",
        )
        stats_row = ctk.CTkFrame(stats_panel, fg_color="transparent")
        stats_row.pack(fill="x", padx=14, pady=(0, 16))
        for col in range(4):
            stats_row.grid_columnconfigure(col, weight=1, uniform="stats")
        stat_defs = [
            ("users", "\U0001F465 Kullanici"),
            ("listings", "\U0001F4DD Ilan"),
            ("active_rentals", "\U0001F511 Aktif Kira"),
            ("open_tickets", "\U0001F3AB Acik Ticket"),
        ]
        self.system_stats_value_labels = {}
        for idx, (key, label) in enumerate(stat_defs):
            tile = ctk.CTkFrame(stats_row, fg_color=self.theme["panel_alt"], corner_radius=14)
            tile.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")
            ctk.CTkLabel(tile, text=label, text_color=self.theme["muted"]).pack(anchor="w", padx=14, pady=(12, 2))
            value = ctk.CTkLabel(
                tile,
                text="0",
                text_color=self.theme["accent"],
                font=ctk.CTkFont(size=22, weight="bold"),
            )
            value.pack(anchor="w", padx=14, pady=(0, 14))
            self.system_stats_value_labels[key] = value

        backup_panel = self._panel(scroll)
        backup_panel.pack(fill="x", padx=4, pady=(0, 12))
        self._section_title(
            backup_panel,
            "\U0001F4BE  Veritabani Yedek",
            "Mevcut veritabaninin tam kopyasini sectiginiz konuma kaydedin.",
        )
        backup_row = ctk.CTkFrame(backup_panel, fg_color="transparent")
        backup_row.pack(fill="x", padx=14, pady=(0, 16))
        ctk.CTkButton(
            backup_row,
            text="\U0001F4E5  Yedek Olustur",
            width=200,
            height=38,
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_backup_database,
        ).pack(side="left")
        ctk.CTkLabel(
            backup_row,
            text="Onerilen uzanti: .db",
            text_color=self.theme["muted"],
        ).pack(side="left", padx=14)

        danger = ctk.CTkFrame(
            scroll,
            fg_color=self.theme["panel"],
            corner_radius=18,
            border_width=2,
            border_color=self.theme["danger"],
        )
        danger.pack(fill="x", padx=4, pady=(0, 12))
        ctk.CTkLabel(
            danger,
            text="\u26A0\uFE0F  TEHLIKELI BOLGE",
            text_color="#FFFFFF",
            fg_color=self.theme["danger"],
            corner_radius=10,
            width=180,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(14, 6))
        ctk.CTkLabel(
            danger,
            text="Veritabani Sifirlama",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(2, 0))
        ctk.CTkLabel(
            danger,
            text=(
                "Tum kullanici, ilan, kiralama, yorum, puan, ticket ve bildirim verileri silinir. "
                "Sadece sistem yoneticisi (" + SYSTEM_ADMIN_EMAIL + ") korunur."
            ),
            text_color=self.theme["muted"],
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(2, 12))
        confirm_row = ctk.CTkFrame(danger, fg_color="transparent")
        confirm_row.pack(fill="x", padx=14, pady=(0, 16))
        self.reset_confirm_var = ctk.StringVar()
        ctk.CTkLabel(
            confirm_row,
            text="Onaylamak icin SIFIRLA yazin:",
            text_color=self.theme["muted"],
        ).pack(side="left", padx=(0, 10))
        ctk.CTkEntry(
            confirm_row,
            textvariable=self.reset_confirm_var,
            width=160,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        ).pack(side="left")
        ctk.CTkButton(
            confirm_row,
            text="\U0001F5D1\uFE0F  Veritabanini Sifirla",
            fg_color=self.theme["danger"],
            hover_color="#7F1D1D",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_reset_database,
        ).pack(side="left", padx=14)

    def _panel(self, parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=self.theme["panel"],
            corner_radius=18,
            border_width=1,
            border_color=self.theme["border"],
        )

    def _section_title(self, parent: ctk.CTkFrame, title: str, subtitle: str) -> None:
        ctk.CTkLabel(
            parent,
            text=title,
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkLabel(parent, text=subtitle, text_color=self.theme["muted"]).pack(anchor="w", padx=14, pady=(0, 12))

    def _entry(self, parent: ctk.CTkFrame, label: str, variable: ctk.StringVar, hide: bool = False) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=self.theme["muted"]).pack(anchor="w", pady=(8, 2))
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            show="*" if hide else "",
            height=38,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        entry.pack(fill="x")
        entry.bind("<Return>", self._on_enter_key)
        return entry

    def _grid_entry(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        col: int,
        width: int = 170,
        validate: tuple[str, str] | None = None,
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=self.theme["muted"]).grid(
            row=0, column=col, padx=8, pady=(8, 2), sticky="w"
        )
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            width=width,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        if validate is not None:
            entry.configure(validate="key", validatecommand=validate)
        entry.grid(row=1, column=col, padx=8, pady=(0, 8), sticky="w")
        return entry

    def _money_entry(self, parent: ctk.CTkFrame, variable: ctk.StringVar, width: int = 160) -> ctk.CTkFrame:
        wrapper = ctk.CTkFrame(parent, fg_color=self.theme["input_bg"], corner_radius=8)
        wrapper.pack(side="left", padx=4, pady=4)
        ctk.CTkLabel(
            wrapper,
            text="TL",
            text_color="#FFFFFF",
            fg_color=self.theme["accent_dark"],
            corner_radius=6,
            width=44,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=4, pady=4)
        entry = ctk.CTkEntry(
            wrapper,
            textvariable=variable,
            width=width,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
            border_width=0,
            placeholder_text="0.00",
            validate="key",
            validatecommand=self._float_validate,
        )
        entry.pack(side="left", padx=(2, 6), pady=4)
        return wrapper

    def _is_float_input(self, value: str) -> bool:
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return value.endswith(".") and value.count(".") == 1 and value[:-1].replace(".", "").isdigit()

    def _is_int_input(self, value: str) -> bool:
        if value == "":
            return True
        return value.isdigit()

    def _is_card_number_input(self, value: str) -> bool:
        if value == "":
            return True
        digits = "".join(ch for ch in value if ch.isdigit())
        return value == digits and len(digits) <= 16

    def _is_expiry_input(self, value: str) -> bool:
        if value == "":
            return True
        if len(value) > 5:
            return False
        for idx, ch in enumerate(value):
            if idx == 2:
                if ch != "/":
                    return False
            else:
                if not ch.isdigit():
                    return False
        return True

    def _is_cvv_input(self, value: str) -> bool:
        if value == "":
            return True
        return value.isdigit() and len(value) <= 4

    def _safe_float(self, value: str) -> float:
        text = (value or "").strip().replace(",", ".")
        if not text:
            raise ValueError("Sayisal deger giriniz.")
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError("Gecerli bir sayi giriniz.") from exc

    def _safe_int(self, value: str) -> int:
        text = (value or "").strip()
        if not text:
            raise ValueError("Sayisal deger giriniz.")
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError("Gecerli bir tam sayi giriniz.") from exc

    def _image_for_path(self, path: str | None, size: tuple[int, int]) -> ctk.CTkImage:
        key = f"{path or 'placeholder'}-{size[0]}x{size[1]}-{self.theme_name.get()}"
        if key in self.image_cache:
            return self.image_cache[key]
        if path and Path(path).exists():
            try:
                image = Image.open(path).convert("RGB").resize(size)
            except Exception:
                image = self._placeholder_image(size)
        else:
            image = self._placeholder_image(size)
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        self.image_cache[key] = ctk_image
        return ctk_image

    def _placeholder_image(self, size: tuple[int, int]) -> Image.Image:
        bg = "#1E293B" if self.theme_name.get() == "dark" else "#E2E8F0"
        line = "#334155" if self.theme_name.get() == "dark" else "#94A3B8"
        text = "#94A3B8" if self.theme_name.get() == "dark" else "#475569"
        image = Image.new("RGB", size, bg)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=line)
        draw.text((size[0] // 2 - 28, size[1] // 2 - 8), "No Image", fill=text)
        return image

    def _on_enter_key(self, _event: object | None = None) -> None:
        if self.current_user is None:
            if self.auth_mode.get() == "login":
                self._on_login()
            else:
                self._on_register()

    def _on_escape_key(self, _event: object | None = None) -> None:
        if self.detail_modal and self.detail_modal.winfo_exists():
            self.detail_modal.destroy()

    def _on_login(self) -> None:
        try:
            self.current_user = self.service.login(self.login_email.get(), self.login_pass.get())
            self._build_app_ui()
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Login Hatasi", str(exc))

    def _on_register(self) -> None:
        try:
            self.service.register(
                self.reg_name.get(),
                self.reg_email.get(),
                self.reg_pass.get(),
                self.reg_license.get(),
                "user",
            )
            msg.showinfo("Basarili", "Kayit tamamlandi. Giris yapabilirsiniz.")
            self.auth_mode.set("login")
            self._render_auth_form("login")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Kayit Hatasi", str(exc))

    def _logout(self) -> None:
        if self._auto_refresh_after_id is not None:
            self.after_cancel(self._auto_refresh_after_id)
            self._auto_refresh_after_id = None
        self.current_user = None
        self._last_data_signature = ""
        self._show_auth_screen()

    def _on_change_theme(self, mode: str) -> None:
        if mode not in THEMES:
            return
        self.theme = THEMES[mode]
        ctk.set_appearance_mode(self.theme["appearance"])
        if self.current_user:
            self._build_app_ui()
            self._show_page("ayarlar")
        else:
            self._show_auth_screen()

    def _on_toggle_auto_sync(self) -> None:
        if self.auto_sync_var.get():
            self._schedule_auto_refresh()
        else:
            if self._auto_refresh_after_id is not None:
                self.after_cancel(self._auto_refresh_after_id)
                self._auto_refresh_after_id = None
        self._update_sync_label()

    def _update_sync_label(self) -> None:
        if not hasattr(self, "sync_status_label"):
            return
        state = "acik" if self.auto_sync_var.get() else "kapali"
        self.sync_status_label.configure(text=f"Otomatik senkronizasyon: {state}")

    def _refresh_all(self) -> None:
        if not self.current_user:
            return
        self.current_user = self.service.kullanici_getir(self.current_user["kullanici_id"])
        balance_text = f"{self.current_user['ad']}  |  \U0001F4B0 {float(self.current_user['bakiye']):.2f} TL"
        self.balance_label.configure(text=balance_text)
        if hasattr(self, "settings_balance_label"):
            self.settings_balance_label.configure(
                text=f"Mevcut bakiye: {float(self.current_user['bakiye']):.2f} TL"
            )
        self.listings_cache = self.service.ilanlar_getir(
            sadece_onayli=self.current_user["rol"] != "admin"
        )
        self._render_listing_cards()
        self._render_vehicle_cards()
        self._refresh_my_listings()
        self._refresh_my_rentals()
        self._refresh_create_listing_choices()
        self._refresh_support()
        self._refresh_notifications()
        if self.current_user["rol"] == "admin":
            self._refresh_admin_pages()
        self._last_data_signature = self._data_signature()

    def _data_signature(self) -> str:
        if not self.current_user:
            return ""
        user_id = self.current_user["kullanici_id"]
        parts: list[str] = [
            repr(self.service.kullanici_getir(user_id)),
            repr(self.service.ilanlar_getir(sadece_onayli=self.current_user["rol"] != "admin")),
            repr(self.service.kullanici_araclari_getir(user_id)),
            repr(self.service.kullanici_kiralamalari(user_id)),
            repr(self.service.ticketleri_getir(user_id)),
            repr(self.service.bildirimleri_getir(user_id)),
        ]
        if self.current_user["rol"] == "admin":
            parts.extend(
                [
                    repr(self.service.kullanicilar_listesi()),
                    repr(self.service.ilanlar_getir()),
                    repr(self.service.ticketleri_getir()),
                ]
            )
        return "|".join(parts)

    def _schedule_auto_refresh(self) -> None:
        if not self.auto_sync_var.get():
            return
        if self._auto_refresh_after_id is not None:
            self.after_cancel(self._auto_refresh_after_id)
        self._auto_refresh_after_id = self.after(4500, self._auto_refresh_if_changed)

    def _auto_refresh_if_changed(self) -> None:
        self._auto_refresh_after_id = None
        if not self.current_user or not self.auto_sync_var.get():
            return
        try:
            signature = self._data_signature()
            if self._last_data_signature and signature != self._last_data_signature:
                self._refresh_all()
            else:
                self._last_data_signature = signature
        finally:
            self._schedule_auto_refresh()

    def _stars_text(self, ortalama: float) -> str:
        full = int(round(ortalama))
        return ("*" * full).ljust(5, "-")

    def _render_listing_cards(self) -> None:
        for child in self.cards_area.winfo_children():
            child.destroy()
        query = self.filter_text.get().strip().lower()
        data = [
            item
            for item in self.listings_cache
            if query in item["baslik"].lower()
            or query in item["konum"].lower()
            or query in item["marka"].lower()
            or query in item["model"].lower()
        ]
        sort = self.sort_var.get()
        if sort == "Fiyat artan":
            data.sort(key=lambda x: float(x["saatlik_ucret"]))
        elif sort == "Fiyat azalan":
            data.sort(key=lambda x: float(x["saatlik_ucret"]), reverse=True)
        elif sort == "Puan azalan":
            data.sort(key=lambda x: self.service.puan_ozeti(x["ilan_id"])["ortalama"], reverse=True)
        else:
            data.sort(key=lambda x: int(x["ilan_id"]), reverse=True)

        if not data:
            ctk.CTkLabel(
                self.cards_area,
                text="Bu filtreye uygun ilan bulunamadi.",
                text_color=self.theme["muted"],
            ).pack(pady=30)
            return

        self.cards_area.grid_columnconfigure(0, weight=1, uniform="cards")
        self.cards_area.grid_columnconfigure(1, weight=1, uniform="cards")

        for row_index, item in enumerate(data):
            card = self._panel(self.cards_area)
            card.grid(row=row_index // 2, column=row_index % 2, sticky="nsew", padx=10, pady=10)
            card.grid_columnconfigure(0, weight=0)
            card.grid_columnconfigure(1, weight=1)

            thumb_frame = ctk.CTkFrame(card, fg_color=self.theme["panel_alt"], corner_radius=14)
            thumb_frame.grid(row=0, column=0, rowspan=4, padx=14, pady=14, sticky="ns")
            thumb = ctk.CTkLabel(
                thumb_frame,
                text="",
                image=self._image_for_path(item["gorsel_yolu"], (240, 160)),
                fg_color="transparent",
            )
            thumb.pack(padx=6, pady=6)

            ctk.CTkLabel(
                card,
                text=item["baslik"],
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(16, 2))
            ctk.CTkLabel(
                card,
                text=f"{item['marka']} {item['model']} | {item['konum']} | {item['kilometre']} km",
                text_color=self.theme["muted"],
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8)
            ctk.CTkLabel(
                card,
                text=f"{float(item['saatlik_ucret']):.2f} TL / saat",
                text_color=self.theme["accent"],
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w",
            ).grid(row=2, column=1, sticky="w", padx=8, pady=(6, 2))

            footer = ctk.CTkFrame(card, fg_color="transparent")
            footer.grid(row=3, column=1, sticky="ew", padx=8, pady=(4, 14))
            footer.grid_columnconfigure(0, weight=1)
            like_count = self.service.begeni_sayisi(item["ilan_id"])
            rating = self.service.puan_ozeti(item["ilan_id"])
            stars_text = self._stars_text(rating["ortalama"]) if rating["adet"] else "-----"
            avg_text = f"{rating['ortalama']:.1f}" if rating["adet"] else "-"
            ctk.CTkLabel(
                footer,
                text=f"\u2764\uFE0F {like_count}    \u2B50 {avg_text}/5  {stars_text}",
                text_color=self.theme["muted"],
                anchor="w",
                font=ctk.CTkFont(size=12),
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
            ctk.CTkLabel(
                footer,
                text=f"Sahip: {item['sahip_ad']}",
                text_color=self.theme["muted"],
                anchor="w",
                font=ctk.CTkFont(size=12),
            ).grid(row=1, column=0, sticky="w")
            ctk.CTkButton(
                footer,
                text="\U0001F50D  Detay",
                width=110,
                height=34,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda i=item: self._open_listing_detail(i),
            ).grid(row=1, column=1, sticky="e", padx=(8, 0))

    def _render_vehicle_cards(self) -> None:
        if not hasattr(self, "vehicle_cards"):
            return
        for child in self.vehicle_cards.winfo_children():
            child.destroy()
        vehicles = self.service.kullanici_araclari_getir(self.current_user["kullanici_id"])
        if not vehicles:
            ctk.CTkLabel(
                self.vehicle_cards,
                text="Kayitli araciniz yok.",
                text_color=self.theme["muted"],
            ).pack(pady=20)
            return
        for vehicle in vehicles:
            card = self._panel(self.vehicle_cards)
            card.pack(fill="x", padx=4, pady=8)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card,
                text="",
                image=self._image_for_path(vehicle["gorsel_yolu"], (170, 110)),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            ctk.CTkLabel(
                card,
                text=f"{vehicle['marka']} {vehicle['model']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=17, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(18, 2))
            status = "Musait" if vehicle["musait_mi"] else "Kirada"
            ctk.CTkLabel(
                card,
                text=f"{vehicle['kilometre']} km | Durum: {status}",
                text_color=self.theme["muted"],
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 18))

    def _refresh_create_listing_choices(self) -> None:
        vehicles = self.service.kullanici_araclari_getir(self.current_user["kullanici_id"])
        choices = [f'{v["arac_id"]} - {v["marka"]} {v["model"]}' for v in vehicles]
        self.cmb_user_vehicle.configure(values=choices if choices else ["-"])
        if self.user_vehicle.get() not in choices:
            self.user_vehicle.set(choices[0] if choices else "-")

    def _refresh_support(self) -> None:
        if not hasattr(self, "support_cards_area"):
            return
        for child in self.support_cards_area.winfo_children():
            child.destroy()
        tickets = self.service.ticketleri_getir(self.current_user["kullanici_id"])
        if not tickets:
            ctk.CTkLabel(
                self.support_cards_area,
                text="Henuz acilmis bir ticketiniz yok.",
                text_color=self.theme["muted"],
            ).pack(pady=20)
            return
        for ticket in tickets:
            card = self._panel(self.support_cards_area)
            card.pack(fill="x", padx=4, pady=6)
            card.grid_columnconfigure(1, weight=1)
            badge_color = {
                "open": self.theme["warning"],
                "in_progress": self.theme["accent_dark"],
                "closed": self.theme["success"],
            }.get(ticket["durum"], self.theme["muted"])
            ctk.CTkLabel(
                card,
                text=ticket["durum"].upper(),
                text_color="#FFFFFF",
                fg_color=badge_color,
                corner_radius=10,
                width=110,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            ctk.CTkLabel(
                card,
                text=f"#{ticket['ticket_id']} - {ticket['baslik']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 2))
            preview = (ticket["yanit"][:96] + "...") if ticket["yanit"] and len(ticket["yanit"]) > 96 else (
                ticket["yanit"] or "Henuz yanit yok"
            )
            yanitlayan = (
                f" | Yanitlayan: {ticket['yanitlayan_ad']}" if ticket.get("yanitlayan_ad") else ""
            )
            ctk.CTkLabel(
                card,
                text=f"Yanit: {preview}{yanitlayan}",
                text_color=self.theme["muted"],
                wraplength=720,
                justify="left",
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 14))
            ctk.CTkButton(
                card,
                text="\U0001F4C2  Ac",
                width=110,
                height=32,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                command=lambda tid=ticket["ticket_id"]: self._open_ticket_detail(tid, can_reply=False),
            ).grid(row=0, column=2, rowspan=2, padx=14, pady=14)

    def _refresh_notifications(self) -> None:
        if not self.notification_cards:
            return
        for child in self.notification_cards.winfo_children():
            child.destroy()
        notifications = self.service.bildirimleri_getir(self.current_user["kullanici_id"])
        unread_count = len([n for n in notifications if not n["okundu_mu"]])
        self.notification_summary.configure(text=f"{len(notifications)} bildirim | {unread_count} yeni")
        if not notifications:
            ctk.CTkLabel(
                self.notification_cards,
                text="Henuz bildiriminiz yok.",
                text_color=self.theme["muted"],
                font=ctk.CTkFont(size=15),
            ).pack(pady=28)
            return
        for notification in notifications:
            is_unread = notification["okundu_mu"] == 0
            card = self._panel(self.notification_cards)
            card.pack(fill="x", padx=6, pady=7)
            card.grid_columnconfigure(1, weight=1)
            accent = self.theme["accent"] if is_unread else self.theme["muted"]
            ctk.CTkLabel(
                card,
                text="YENI" if is_unread else "OK",
                text_color="#FFFFFF",
                fg_color=self.theme["accent_dark"] if is_unread else "#475569",
                corner_radius=10,
                width=58,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            ctk.CTkLabel(
                card,
                text=notification["baslik"],
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 2))
            ctk.CTkLabel(
                card,
                text=notification["mesaj"],
                text_color=self.theme["muted"],
                wraplength=720,
                justify="left",
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 14))
            ctk.CTkLabel(
                card,
                text=notification["created_at"],
                text_color=accent,
            ).grid(row=0, column=2, padx=14, pady=14, sticky="e")
            if is_unread:
                ctk.CTkButton(
                    card,
                    text="Okundu",
                    width=82,
                    height=30,
                    fg_color=self.theme["accent_dark"],
                    hover_color=self.theme["accent"],
                    command=lambda nid=notification["bildirim_id"]: self._on_mark_notification(nid),
                ).grid(row=1, column=2, padx=14, pady=(0, 14), sticky="e")

    def _refresh_admin_pages(self) -> None:
        self._render_admin_users()
        self._render_admin_listings()
        self._render_admin_tickets()
        self._render_system_stats()

    def _render_system_stats(self) -> None:
        if not self.system_stats_value_labels:
            return
        stats = self.service.dashboard_stats()
        for key, label in self.system_stats_value_labels.items():
            label.configure(text=str(stats.get(key, 0)))

    def _render_admin_users(self) -> None:
        for child in self.admin_user_cards_area.winfo_children():
            child.destroy()
        self._admin_user_cards = {}
        users = self.service.kullanicilar_listesi()
        if not users:
            ctk.CTkLabel(
                self.admin_user_cards_area,
                text="Kullanici bulunamadi.",
                text_color=self.theme["muted"],
            ).pack(pady=20)
            return
        for user in users:
            card = self._panel(self.admin_user_cards_area)
            card.pack(fill="x", padx=4, pady=6)
            card.grid_columnconfigure(2, weight=1)
            uid = int(user["kullanici_id"])
            self._admin_user_cards[uid] = card
            initials = (user["ad"][:2].upper() if user["ad"] else "??")
            ctk.CTkLabel(
                card,
                text=initials,
                text_color="#FFFFFF",
                fg_color=self.theme["accent_dark"],
                corner_radius=20,
                width=44,
                height=44,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            role_color = self.theme["accent_dark"] if user["rol"] == "admin" else self.theme["panel_alt"]
            role_text_color = "#FFFFFF" if user["rol"] == "admin" else self.theme["muted"]
            ctk.CTkLabel(
                card,
                text=user["rol"].upper(),
                text_color=role_text_color,
                fg_color=role_color,
                corner_radius=8,
                width=70,
                height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=1, padx=4, pady=(16, 4), sticky="w")
            status_color = self.theme["success"] if user["aktif_mi"] else self.theme["danger"]
            ctk.CTkLabel(
                card,
                text="Aktif" if user["aktif_mi"] else "Pasif",
                text_color="#FFFFFF",
                fg_color=status_color,
                corner_radius=8,
                width=64,
                height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=1, column=1, padx=4, pady=(0, 16), sticky="w")
            ctk.CTkLabel(
                card,
                text=f"{user['ad']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).grid(row=0, column=2, sticky="w", padx=10, pady=(16, 2))
            ctk.CTkLabel(
                card,
                text=f"{user['email']}  |  Ehliyet: {user['ehliyet_no']}",
                text_color=self.theme["muted"],
                anchor="w",
            ).grid(row=1, column=2, sticky="w", padx=10, pady=(0, 16))
            ctk.CTkLabel(
                card,
                text=f"#{uid}\n{float(user['bakiye']):.2f} TL",
                text_color=self.theme["accent"],
                font=ctk.CTkFont(size=13, weight="bold"),
                justify="right",
            ).grid(row=0, column=3, rowspan=2, padx=14, pady=14, sticky="e")
            select_btn = ctk.CTkButton(
                card,
                text="Sec",
                width=70,
                height=30,
                fg_color=self.theme["panel_alt"],
                text_color=self.theme["text"],
                hover_color=self.theme["border"],
                command=lambda u=user: self._select_admin_user(u),
            )
            select_btn.grid(row=0, column=4, rowspan=2, padx=14, pady=14)
        if self.selected_admin_user_id is not None:
            self._highlight_selection(self._admin_user_cards, self.selected_admin_user_id)

    def _select_admin_user(self, user: dict) -> None:
        self.selected_admin_user_id = int(user["kullanici_id"])
        self.role_var.set(user["rol"])
        self.active_var.set("Aktif" if user["aktif_mi"] else "Pasif")
        self._highlight_selection(self._admin_user_cards, self.selected_admin_user_id)

    def _render_admin_listings(self) -> None:
        for child in self.admin_listing_cards_area.winfo_children():
            child.destroy()
        self._admin_listing_cards = {}
        listings = self.service.ilanlar_getir()
        if not listings:
            ctk.CTkLabel(
                self.admin_listing_cards_area,
                text="Ilan bulunamadi.",
                text_color=self.theme["muted"],
            ).pack(pady=20)
            return
        for listing in listings:
            card = self._panel(self.admin_listing_cards_area)
            card.pack(fill="x", padx=4, pady=6)
            card.grid_columnconfigure(2, weight=1)
            lid = int(listing["ilan_id"])
            self._admin_listing_cards[lid] = card
            ctk.CTkLabel(
                card,
                text="",
                image=self._image_for_path(listing["gorsel_yolu"], (140, 90)),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            status_color = {
                "approved": self.theme["success"],
                "rejected": self.theme["danger"],
                "pending": self.theme["warning"],
            }.get(listing["durum"], self.theme["muted"])
            ctk.CTkLabel(
                card,
                text=listing["durum"].upper(),
                text_color="#FFFFFF",
                fg_color=status_color,
                corner_radius=8,
                width=110,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=1, padx=4, pady=(16, 4), sticky="w")
            ctk.CTkLabel(
                card,
                text=f"{float(listing['saatlik_ucret']):.2f} TL/saat",
                text_color=self.theme["accent"],
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=1, column=1, padx=4, pady=(0, 16), sticky="w")
            ctk.CTkLabel(
                card,
                text=f"#{lid} - {listing['baslik']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).grid(row=0, column=2, sticky="w", padx=10, pady=(16, 2))
            ctk.CTkLabel(
                card,
                text=f"{listing['marka']} {listing['model']}  |  Sahip: {listing['sahip_ad']}  |  {listing['konum']}",
                text_color=self.theme["muted"],
                anchor="w",
            ).grid(row=1, column=2, sticky="w", padx=10, pady=(0, 16))
            ctk.CTkButton(
                card,
                text="Detay",
                width=78,
                height=30,
                fg_color=self.theme["panel_alt"],
                text_color=self.theme["text"],
                hover_color=self.theme["border"],
                command=lambda i=listing: self._open_listing_detail(i),
            ).grid(row=0, column=3, padx=10, pady=(16, 4), sticky="e")
            ctk.CTkButton(
                card,
                text="Sec",
                width=78,
                height=30,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                command=lambda i=listing: self._select_admin_listing(i),
            ).grid(row=1, column=3, padx=10, pady=(0, 16), sticky="e")
        if self.selected_admin_listing_id is not None:
            self._highlight_selection(self._admin_listing_cards, self.selected_admin_listing_id)

    def _select_admin_listing(self, listing: dict) -> None:
        self.selected_admin_listing_id = int(listing["ilan_id"])
        self._highlight_selection(self._admin_listing_cards, self.selected_admin_listing_id)

    def _render_admin_tickets(self) -> None:
        for child in self.admin_ticket_cards_area.winfo_children():
            child.destroy()
        self._admin_ticket_cards = {}
        tickets = self.service.ticketleri_getir()
        if not tickets:
            ctk.CTkLabel(
                self.admin_ticket_cards_area,
                text="Ticket bulunamadi.",
                text_color=self.theme["muted"],
            ).pack(pady=20)
            return
        for ticket in tickets:
            card = self._panel(self.admin_ticket_cards_area)
            card.pack(fill="x", padx=4, pady=6)
            card.grid_columnconfigure(1, weight=1)
            tid = int(ticket["ticket_id"])
            self._admin_ticket_cards[tid] = card
            badge_color = {
                "open": self.theme["warning"],
                "in_progress": self.theme["accent_dark"],
                "closed": self.theme["success"],
            }.get(ticket["durum"], self.theme["muted"])
            ctk.CTkLabel(
                card,
                text=ticket["durum"].upper(),
                text_color="#FFFFFF",
                fg_color=badge_color,
                corner_radius=10,
                width=110,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=14, pady=14)
            ctk.CTkLabel(
                card,
                text=f"#{tid} - {ticket['baslik']}",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 2))
            yanitlayan = (
                f" | Yanitlayan: {ticket['yanitlayan_ad']}" if ticket.get("yanitlayan_ad") else ""
            )
            ctk.CTkLabel(
                card,
                text=f"Acan: {ticket['ad']}  |  Yanit: {ticket['yanit'] or 'Henuz yanit yok'}{yanitlayan}",
                text_color=self.theme["muted"],
                wraplength=820,
                justify="left",
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 14))
            ctk.CTkButton(
                card,
                text="\U0001F4C2  Ac",
                width=120,
                height=40,
                fg_color=self.theme["accent_dark"],
                hover_color=self.theme["accent"],
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda tid_local=tid: self._open_ticket_detail(tid_local, can_reply=True),
            ).grid(row=0, column=2, rowspan=2, padx=14, pady=14)

    def _highlight_selection(self, cards: dict[int, ctk.CTkFrame], selected_id: int) -> None:
        for cid, card in cards.items():
            if cid == selected_id:
                card.configure(border_color=self.theme["accent"], border_width=2)
            else:
                card.configure(border_color=self.theme["border"], border_width=1)

    def _open_ticket_detail(self, ticket_id: int, can_reply: bool) -> None:
        try:
            ticket = self.service.ticket_getir(ticket_id)
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))
            return
        if self.ticket_modal and self.ticket_modal.winfo_exists():
            self.ticket_modal.destroy()
        modal = ctk.CTkToplevel(self)
        self.ticket_modal = modal
        modal.title(f"Ticket #{ticket['ticket_id']} - {ticket['baslik']}")
        modal.geometry("780x700")
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=self.theme["bg"])

        shell = ctk.CTkScrollableFrame(modal, fg_color=self.theme["bg"])
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        header = self._panel(shell)
        header.pack(fill="x", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)
        badge_color = {
            "open": self.theme["warning"],
            "in_progress": self.theme["accent_dark"],
            "closed": self.theme["success"],
        }.get(ticket["durum"], self.theme["muted"])
        ctk.CTkLabel(
            header,
            text=ticket["durum"].upper(),
            text_color="#FFFFFF",
            fg_color=badge_color,
            corner_radius=10,
            width=120,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, rowspan=3, padx=14, pady=14)
        ctk.CTkLabel(
            header,
            text=f"#{ticket['ticket_id']}  -  {ticket['baslik']}",
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 2))
        acan_email = ticket.get("email", "")
        ctk.CTkLabel(
            header,
            text=f"\U0001F464  Acan: {ticket['ad']}  ({acan_email})",
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=8)
        ctk.CTkLabel(
            header,
            text=f"\U0001F4C5  Olusturma: {ticket['created_at']}  |  Son guncelleme: {ticket['updated_at']}",
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=2, column=1, sticky="w", padx=8, pady=(0, 14))

        message_panel = self._panel(shell)
        message_panel.pack(fill="x", pady=(0, 12))
        self._section_title(
            message_panel,
            "\U0001F4DD  Kullanici Mesaji",
            f"{ticket['ad']} tarafindan acilan ticket icerigi.",
        )
        ctk.CTkLabel(
            message_panel,
            text=ticket["mesaj"],
            text_color=self.theme["text"],
            wraplength=680,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(0, 14), fill="x")

        reply_panel = self._panel(shell)
        reply_panel.pack(fill="both", expand=True)
        self._section_title(
            reply_panel,
            "\U0001F4AC  Yetkili Yaniti",
            "Destek ekibinin verdigi resmi yanit.",
        )
        if ticket.get("yanit"):
            yanit_card = ctk.CTkFrame(reply_panel, fg_color=self.theme["panel_alt"], corner_radius=12)
            yanit_card.pack(fill="x", padx=14, pady=(0, 10))
            yanit_card.grid_columnconfigure(1, weight=1)
            initials = (ticket.get("yanitlayan_ad") or "AD")[:2].upper()
            ctk.CTkLabel(
                yanit_card,
                text=initials,
                text_color="#FFFFFF",
                fg_color=self.theme["accent_dark"],
                corner_radius=20,
                width=44,
                height=44,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, rowspan=3, padx=12, pady=12)
            ctk.CTkLabel(
                yanit_card,
                text=ticket.get("yanitlayan_ad") or "Bilinmiyor",
                text_color=self.theme["text_strong"],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=(12, 0))
            rol_text = (ticket.get("yanitlayan_rol") or "yetkili").upper()
            ctk.CTkLabel(
                yanit_card,
                text=f"\U0001F6E1\uFE0F  {rol_text}  |  {ticket.get('yanit_tarihi') or ticket['updated_at']}",
                text_color=self.theme["muted"],
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))
            ctk.CTkLabel(
                yanit_card,
                text=ticket["yanit"],
                text_color=self.theme["text"],
                wraplength=620,
                justify="left",
                anchor="w",
            ).grid(row=2, column=1, sticky="w", padx=8, pady=(0, 12))
        else:
            ctk.CTkLabel(
                reply_panel,
                text="Henuz bir yanit bulunmuyor. Destek ekibimiz en kisa surede donus yapacak.",
                text_color=self.theme["muted"],
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(0, 14))

        if can_reply:
            form = self._panel(shell)
            form.pack(fill="x", pady=(12, 0))
            self._section_title(
                form,
                "\u270D\uFE0F  Yanit Yaz",
                "Yaniti girin ve durumu belirleyerek kaydedin. Yanitlayan kullaniciniz olarak kaydedilir.",
            )
            reply_var = ctk.StringVar(value=ticket.get("yanit") or "")
            status_var = ctk.StringVar(value=ticket["durum"])
            entry = ctk.CTkTextbox(
                form,
                height=120,
                fg_color=self.theme["input_bg"],
                text_color=self.theme["input_text"],
            )
            entry.pack(fill="x", padx=14, pady=(0, 10))
            entry.insert("1.0", reply_var.get())
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(0, 14))
            ctk.CTkLabel(row, text="Durum", text_color=self.theme["muted"]).pack(side="left", padx=(0, 4))
            ctk.CTkComboBox(
                row,
                values=["open", "in_progress", "closed"],
                variable=status_var,
                width=160,
                state="readonly",
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                row,
                text="Iptal",
                width=110,
                fg_color=self.theme["panel_alt"],
                text_color=self.theme["text"],
                hover_color=self.theme["border"],
                command=modal.destroy,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                row,
                text="\U0001F4E4  Yaniti Kaydet",
                fg_color=self.theme["success"],
                hover_color=self.theme["accent_dark"],
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda: self._submit_ticket_reply_from_modal(
                    ticket_id, entry.get("1.0", "end"), status_var.get(), modal
                ),
            ).pack(side="right", padx=4)

    def _submit_ticket_reply_from_modal(
        self, ticket_id: int, reply: str, status: str, modal: ctk.CTkToplevel
    ) -> None:
        try:
            text = reply.strip()
            if not text:
                raise ValueError("Yanit bos olamaz.")
            self.service.ticket_yanitla(
                ticket_id, text, status, self.current_user["kullanici_id"]
            )
            modal.destroy()
            self._refresh_all()
            msg.showinfo("Basarili", "Ticket guncellendi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _open_listing_detail(self, listing: dict) -> None:
        if self.detail_modal and self.detail_modal.winfo_exists():
            self.detail_modal.destroy()
        self.detail_modal = ctk.CTkToplevel(self)
        self.detail_modal.title(f"Ilan Detayi #{listing['ilan_id']}")
        self.detail_modal.geometry("960x780")
        self.detail_modal.transient(self)
        self.detail_modal.grab_set()
        self.detail_modal.configure(fg_color=self.theme["bg"])

        shell = ctk.CTkScrollableFrame(self.detail_modal, fg_color=self.theme["bg"])
        shell.pack(fill="both", expand=True, padx=18, pady=18)
        top = self._panel(shell)
        top.pack(fill="x", pady=(0, 12))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            top,
            text="",
            image=self._image_for_path(listing["gorsel_yolu"], (340, 220)),
        ).grid(row=0, column=0, rowspan=6, padx=16, pady=16)
        ctk.CTkLabel(
            top,
            text=listing["baslik"],
            text_color=self.theme["text_strong"],
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=10, pady=(18, 4))
        ctk.CTkLabel(
            top,
            text=f"{listing['marka']} {listing['model']} | {listing['kilometre']} km | {listing['konum']}",
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=10)
        ctk.CTkLabel(
            top,
            text=f"{float(listing['saatlik_ucret']):.2f} TL / saat",
            text_color=self.theme["accent"],
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=2, column=1, sticky="w", padx=10, pady=(10, 4))
        rating = self.service.puan_ozeti(listing["ilan_id"])
        rating_text = (
            f"Puan: {rating['ortalama']:.1f}/5 [{self._stars_text(rating['ortalama'])}] ({rating['adet']} oy)"
            if rating["adet"]
            else "Puan: henuz oylama yok"
        )
        ctk.CTkLabel(
            top,
            text=rating_text,
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=3, column=1, sticky="w", padx=10, pady=(2, 2))
        ctk.CTkLabel(
            top,
            text=f"Sahip: {listing['sahip_ad']} | Durum: {listing['durum']}",
            text_color=self.theme["muted"],
            anchor="w",
        ).grid(row=4, column=1, sticky="w", padx=10)
        ctk.CTkLabel(
            top,
            text=listing["aciklama"],
            text_color=self.theme["text"],
            wraplength=480,
            justify="left",
            anchor="w",
        ).grid(row=5, column=1, sticky="nw", padx=10, pady=(10, 16))

        action = self._panel(shell)
        action.pack(fill="x", pady=(0, 12))
        hours = ctk.StringVar(value="1")
        total = ctk.StringVar(value=f"Toplam: {float(listing['saatlik_ucret']):.2f} TL")

        def update_total(*_args: object) -> None:
            try:
                cost = self.service.kira_tutar_hesapla(
                    listing["ilan_id"], self._safe_int(hours.get())
                )
                total.set(f"Toplam: {cost:.2f} TL")
            except Exception:
                total.set("Toplam: -")

        hours.trace_add("write", update_total)
        ctk.CTkLabel(action, text="Kiralama Suresi (saat)", text_color=self.theme["muted"]).pack(
            side="left", padx=(14, 8), pady=14
        )
        hours_entry = ctk.CTkEntry(
            action,
            textvariable=hours,
            width=82,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
            validate="key",
            validatecommand=self._int_validate,
        )
        hours_entry.pack(side="left", padx=8)
        ctk.CTkLabel(
            action,
            textvariable=total,
            text_color=self.theme["accent"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=18)
        ctk.CTkButton(
            action,
            text="\u2764\uFE0F  Begeni",
            width=110,
            fg_color=self.theme["panel_alt"],
            text_color=self.theme["text"],
            hover_color=self.theme["border"],
            command=lambda: self._like_from_modal(listing["ilan_id"]),
        ).pack(side="right", padx=8)
        ctk.CTkButton(
            action,
            text="\U0001F511  Kirala",
            width=130,
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._rent_from_modal(listing["ilan_id"], hours),
        ).pack(side="right", padx=8)

        user_id = self.current_user["kullanici_id"]
        is_owner = int(listing.get("ilan_sahibi_id", 0)) == int(user_id)
        renter = self.service.kullanici_kiraladi_mi(listing["ilan_id"], user_id)
        already_rated = bool(
            self.service.kullanici_puani(listing["ilan_id"], user_id)
        )
        already_commented = self.service.kullanici_yorumladi_mi(
            listing["ilan_id"], user_id
        )

        rate_panel = self._panel(shell)
        rate_panel.pack(fill="x", pady=(0, 12))
        self._section_title(
            rate_panel,
            "Puan Ver",
            "Her ilana yalnizca 1 kez puan verebilirsiniz.",
        )
        rate_row = ctk.CTkFrame(rate_panel, fg_color="transparent")
        rate_row.pack(fill="x", padx=14, pady=(0, 14))
        if is_owner:
            ctk.CTkLabel(
                rate_row,
                text="Kendi ilaniniza puan veremezsiniz.",
                text_color=self.theme["muted"],
            ).pack(side="left", padx=8)
        elif not renter:
            ctk.CTkLabel(
                rate_row,
                text="Puan vermek icin once bu ilanin aracini kiralamalisiniz.",
                text_color=self.theme["muted"],
            ).pack(side="left", padx=8)
        elif already_rated:
            current_rating = self.service.kullanici_puani(listing["ilan_id"], user_id)
            for i in range(1, 6):
                ctk.CTkButton(
                    rate_row,
                    text=str(i),
                    width=46,
                    height=36,
                    corner_radius=10,
                    fg_color=self.theme["accent_dark"] if i <= current_rating else self.theme["panel_alt"],
                    text_color="#FFFFFF" if i <= current_rating else self.theme["muted"],
                    hover_color=self.theme["panel_alt"],
                    font=ctk.CTkFont(size=14, weight="bold"),
                    state="disabled",
                ).pack(side="left", padx=4)
            ctk.CTkLabel(
                rate_row,
                text=f"\u2705 Puaniniz: {current_rating}/5  (degistirilemez)",
                text_color=self.theme["success"],
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=14)
        else:
            rating_var = ctk.IntVar(value=0)
            star_buttons: list[ctk.CTkButton] = []

            def _redraw_stars(value: int) -> None:
                for idx, btn in enumerate(star_buttons, start=1):
                    btn.configure(
                        fg_color=self.theme["accent_dark"] if idx <= value else self.theme["panel_alt"],
                        text_color="#FFFFFF" if idx <= value else self.theme["muted"],
                    )

            for i in range(1, 6):
                btn = ctk.CTkButton(
                    rate_row,
                    text=str(i),
                    width=46,
                    height=36,
                    corner_radius=10,
                    fg_color=self.theme["panel_alt"],
                    text_color=self.theme["muted"],
                    hover_color=self.theme["accent"],
                    font=ctk.CTkFont(size=14, weight="bold"),
                    command=lambda v=i: (rating_var.set(v), _redraw_stars(v)),
                )
                btn.pack(side="left", padx=4)
                star_buttons.append(btn)
            _redraw_stars(rating_var.get())
            ctk.CTkButton(
                rate_row,
                text="\u2B50  Puani Kaydet",
                fg_color=self.theme["success"],
                hover_color=self.theme["accent_dark"],
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda: self._submit_rating(listing["ilan_id"], rating_var.get()),
            ).pack(side="left", padx=14)

        comments_panel = self._panel(shell)
        comments_panel.pack(fill="both", expand=True)
        self._section_title(
            comments_panel,
            "Yorumlar",
            "Her ilana yalnizca 1 kez yorum yapabilirsiniz.",
        )
        comments_box = ctk.CTkTextbox(
            comments_panel,
            height=200,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        comments_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._populate_comments(comments_box, listing["ilan_id"])
        new_comment = ctk.StringVar()
        row = ctk.CTkFrame(comments_panel, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))

        if is_owner:
            placeholder = "Kendi ilaniniza yorum yapamazsiniz."
            allow_comment = False
        elif not renter:
            placeholder = "Yorum yapmak icin once kiralamalisiniz"
            allow_comment = False
        elif already_commented:
            placeholder = "Bu ilana zaten yorum yaptiniz (1 yorum hakkiniz var)."
            allow_comment = False
        else:
            placeholder = "Yorum yaz (en fazla 500 karakter)"
            allow_comment = True

        comment_entry = ctk.CTkEntry(
            row,
            textvariable=new_comment,
            placeholder_text=placeholder,
            height=38,
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        comment_entry.pack(side="left", fill="x", expand=True)
        if not allow_comment:
            comment_entry.configure(state="disabled")
        ctk.CTkButton(
            row,
            text="\U0001F4DD  Yorum Ekle",
            fg_color=self.theme["accent_dark"],
            hover_color=self.theme["accent"],
            state="normal" if allow_comment else "disabled",
            command=lambda: self._add_comment_from_modal(listing["ilan_id"], new_comment, comments_box),
        ).pack(side="right", padx=(10, 0))

    def _populate_comments(self, box: ctk.CTkTextbox, listing_id: int) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        for comment in self.service.yorumlari_getir(listing_id):
            puan_text = ""
            if comment.get("puan"):
                puan_text = f" [{int(comment['puan'])}/5]"
            box.insert(
                "end",
                f"{comment['ad']}{puan_text} ({comment['created_at']}):\n{comment['yorum']}\n\n",
            )
        box.configure(state="disabled")

    def _submit_rating(self, listing_id: int, rating: int) -> None:
        try:
            if rating < 1 or rating > 5:
                raise ValueError("Puan secmediniz.")
            self.service.puan_ver(listing_id, self.current_user["kullanici_id"], rating)
            msg.showinfo("Basarili", f"Puaniniz kaydedildi: {rating}/5")
            if self.detail_modal and self.detail_modal.winfo_exists():
                self.detail_modal.destroy()
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _like_from_modal(self, listing_id: int) -> None:
        try:
            self.service.begen_toggle(listing_id, self.current_user["kullanici_id"])
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _rent_from_modal(self, listing_id: int, hours: ctk.StringVar) -> None:
        try:
            saat = self._safe_int(hours.get())
            self.service.kiralama_baslat(
                listing_id,
                self.current_user["kullanici_id"],
                saat,
            )
            if self.detail_modal and self.detail_modal.winfo_exists():
                self.detail_modal.destroy()
            self._refresh_all()
            self._show_page("kiralamalarim")
            msg.showinfo(
                "Kiralama Basarili",
                f"Kiralama olusturuldu. {saat} saatlik sayaciniz Kiralamalarim sekmesinde calisiyor.",
            )
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _add_comment_from_modal(
        self, listing_id: int, comment_var: ctk.StringVar, box: ctk.CTkTextbox
    ) -> None:
        try:
            self.service.yorum_ekle(
                listing_id, self.current_user["kullanici_id"], comment_var.get()
            )
            comment_var.set("")
            self._populate_comments(box, listing_id)
            msg.showinfo(
                "Yorum Eklendi",
                "Yorumunuz kaydedildi. Bu ilana ait yorum hakkinizi kullandiniz.",
            )
            if self.detail_modal and self.detail_modal.winfo_exists():
                self.detail_modal.destroy()
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _pick_vehicle_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Arac Gorseli Sec",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp"), ("All files", "*.*")],
        )
        if not path:
            return
        self.car_image.set(path)
        try:
            image = Image.open(path).convert("RGB").resize((160, 100))
            self.vehicle_preview_img = ctk.CTkImage(light_image=image, dark_image=image, size=(160, 100))
            self.preview_label.configure(image=self.vehicle_preview_img, text="")
        except Exception:
            self.preview_label.configure(image=None, text="Onizleme acilamadi")

    def _on_add_car(self) -> None:
        try:
            km = self._safe_int(self.car_km.get())
            self.service.arac_ekle(
                self.current_user["kullanici_id"],
                self.car_brand.get(),
                self.car_model.get(),
                km,
                self.car_image.get(),
            )
            self.car_brand.set("")
            self.car_model.set("")
            self.car_km.set("")
            self.car_image.set("")
            self.preview_label.configure(image=None, text="Onizleme")
            self._refresh_all()
            msg.showinfo("Basarili", "Arac eklendi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_create_listing(self) -> None:
        try:
            choice = self.user_vehicle.get()
            if choice == "-":
                raise ValueError("Ilan icin arac seciniz.")
            price = self._safe_float(self.list_price.get())
            self.service.ilan_olustur(
                self.current_user["kullanici_id"],
                int(choice.split(" - ")[0]),
                self.list_title.get(),
                self.list_desc.get("1.0", "end").strip(),
                price,
                self.list_location.get(),
            )
            self.list_title.set("")
            self.list_price.set("")
            self.list_location.set("")
            self.list_desc.delete("1.0", "end")
            self._refresh_all()
            msg.showinfo("Basarili", "Ilan admin onayina gonderildi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_create_ticket(self) -> None:
        try:
            self.service.ticket_olustur(
                self.current_user["kullanici_id"],
                self.ticket_title.get(),
                self.ticket_msg.get(),
            )
            self.ticket_title.set("")
            self.ticket_msg.set("")
            self._refresh_all()
            msg.showinfo("Basarili", "Ticket olusturuldu.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_mark_notification(self, notification_id: int) -> None:
        try:
            self.service.bildirim_okundu_yap(
                notification_id, self.current_user["kullanici_id"]
            )
            self._refresh_all()
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_manual_refresh(self) -> None:
        try:
            self._refresh_all()
            if hasattr(self, "last_refresh_label"):
                self.last_refresh_label.configure(
                    text=f"Son yenileme: {datetime.now().strftime('%H:%M:%S')}"
                )
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _open_balance_simulator(self) -> None:
        if self.balance_modal and self.balance_modal.winfo_exists():
            self.balance_modal.destroy()
        modal = ctk.CTkToplevel(self)
        self.balance_modal = modal
        modal.title("Bakiye Yukle - Sanal Kart Simulatoru")
        modal.geometry("560x720")
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=self.theme["bg"])

        wrapper = ctk.CTkFrame(modal, fg_color=self.theme["bg"])
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)

        card_visual = ctk.CTkFrame(wrapper, fg_color=self.theme["accent_dark"], corner_radius=18, height=200)
        card_visual.pack(fill="x", pady=(0, 14))
        card_visual.pack_propagate(False)
        ctk.CTkLabel(
            card_visual,
            text="\U0001F4B3  CarShare Pro",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(16, 6))
        card_number_label = ctk.CTkLabel(
            card_visual,
            text="\u2022\u2022\u2022\u2022  \u2022\u2022\u2022\u2022  \u2022\u2022\u2022\u2022  \u2022\u2022\u2022\u2022",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        card_number_label.pack(anchor="w", padx=18, pady=(8, 12))
        card_meta_row = ctk.CTkFrame(card_visual, fg_color="transparent")
        card_meta_row.pack(anchor="w", padx=18, fill="x")
        ctk.CTkLabel(
            card_meta_row, text="KART SAHIBI", text_color="#E2E8F0", font=ctk.CTkFont(size=10)
        ).pack(side="left")
        card_exp_label = ctk.CTkLabel(
            card_meta_row, text="MM/YY", text_color="#E2E8F0", font=ctk.CTkFont(size=10)
        )
        card_exp_label.pack(side="right")
        ctk.CTkLabel(
            card_visual,
            text=self.current_user["ad"].upper() if self.current_user else "AD SOYAD",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(2, 12))

        form = self._panel(wrapper)
        form.pack(fill="both", expand=True)
        self._section_title(
            form,
            "\U0001F510  Kart Bilgileri",
            "Tum islemler simulasyondur; gercek odeme alinmaz.",
        )

        card_number_var = ctk.StringVar()
        card_exp_var = ctk.StringVar()
        card_cvv_var = ctk.StringVar()
        amount_var = ctk.StringVar()

        num_lock = [False]
        exp_lock = [False]
        cvv_lock = [False]

        def normalize_card_number(*_a: object) -> None:
            if num_lock[0]:
                return
            raw = card_number_var.get()
            digits = "".join(ch for ch in raw if ch.isdigit())[:16]
            if digits != raw:
                num_lock[0] = True
                card_number_var.set(digits)
                num_lock[0] = False
            padded = digits.ljust(16, "\u2022")
            card_number_label.configure(
                text=f"{padded[0:4]}  {padded[4:8]}  {padded[8:12]}  {padded[12:16]}"
            )

        def normalize_expiry(*_a: object) -> None:
            if exp_lock[0]:
                return
            raw = card_exp_var.get()
            digits = "".join(ch for ch in raw if ch.isdigit())[:4]
            formatted = digits if len(digits) <= 2 else digits[:2] + "/" + digits[2:]
            if formatted != raw:
                exp_lock[0] = True
                card_exp_var.set(formatted)
                exp_lock[0] = False
            card_exp_label.configure(text=formatted or "MM/YY")

        def normalize_cvv(*_a: object) -> None:
            if cvv_lock[0]:
                return
            raw = card_cvv_var.get()
            digits = "".join(ch for ch in raw if ch.isdigit())[:4]
            if digits != raw:
                cvv_lock[0] = True
                card_cvv_var.set(digits)
                cvv_lock[0] = False

        card_number_var.trace_add("write", normalize_card_number)
        card_exp_var.trace_add("write", normalize_expiry)
        card_cvv_var.trace_add("write", normalize_cvv)

        grid = ctk.CTkFrame(form, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(grid, text="Kart Numarasi (16 hane)", text_color=self.theme["muted"]).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2)
        )
        card_entry = ctk.CTkEntry(
            grid,
            textvariable=card_number_var,
            width=380,
            placeholder_text="4242424242424242",
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        card_entry.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="w")

        ctk.CTkLabel(grid, text="Son Kullanma (MM/YY)", text_color=self.theme["muted"]).grid(
            row=2, column=0, sticky="w", padx=8, pady=(8, 2)
        )
        exp_entry = ctk.CTkEntry(
            grid,
            textvariable=card_exp_var,
            width=180,
            placeholder_text="12/29",
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        exp_entry.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="w")

        ctk.CTkLabel(grid, text="CVV (3-4 hane)", text_color=self.theme["muted"]).grid(
            row=2, column=1, sticky="w", padx=8, pady=(8, 2)
        )
        cvv_entry = ctk.CTkEntry(
            grid,
            textvariable=card_cvv_var,
            width=120,
            placeholder_text="123",
            show="*",
            fg_color=self.theme["input_bg"],
            text_color=self.theme["input_text"],
        )
        cvv_entry.grid(row=3, column=1, padx=8, pady=(0, 8), sticky="w")

        ctk.CTkLabel(grid, text="Tutar", text_color=self.theme["muted"]).grid(
            row=4, column=0, sticky="w", padx=8, pady=(8, 2)
        )
        amount_wrapper = ctk.CTkFrame(grid, fg_color="transparent")
        amount_wrapper.grid(row=5, column=0, columnspan=2, padx=0, pady=(0, 8), sticky="w")
        amount_holder = self._money_entry(amount_wrapper, amount_var, width=220)

        quick = ctk.CTkFrame(form, fg_color="transparent")
        quick.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(quick, text="Hizli secim", text_color=self.theme["muted"]).pack(side="left", padx=(0, 8))
        quick_buttons: list[ctk.CTkButton] = []
        for amount in (50, 100, 250, 500, 1000):
            qb = ctk.CTkButton(
                quick,
                text=f"{amount} TL",
                width=72,
                height=30,
                fg_color=self.theme["panel_alt"],
                text_color=self.theme["text"],
                hover_color=self.theme["border"],
                command=lambda a=amount: amount_var.set(str(a)),
            )
            qb.pack(side="left", padx=4)
            quick_buttons.append(qb)

        status_panel = ctk.CTkFrame(form, fg_color="transparent")
        status_panel.pack(fill="x", padx=14, pady=(2, 0))
        spinner_label = ctk.CTkLabel(
            status_panel,
            text="",
            text_color=self.theme["accent"],
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        spinner_label.pack(side="left", padx=(0, 8))
        status_text = ctk.CTkLabel(status_panel, text="", text_color=self.theme["muted"])
        status_text.pack(side="left")
        progress = ctk.CTkProgressBar(form, mode="indeterminate", progress_color=self.theme["accent_dark"])
        progress.pack(fill="x", padx=14, pady=(8, 6))
        progress.set(0)

        action_row = ctk.CTkFrame(form, fg_color="transparent")
        action_row.pack(fill="x", padx=14, pady=(4, 14))
        cancel_btn = ctk.CTkButton(
            action_row,
            text="Iptal",
            width=110,
            fg_color=self.theme["panel_alt"],
            text_color=self.theme["text"],
            hover_color=self.theme["border"],
            command=modal.destroy,
        )
        cancel_btn.pack(side="right", padx=(8, 0))
        submit_btn = ctk.CTkButton(
            action_row,
            text="\U0001F4B3  Yukle",
            width=180,
            height=40,
            fg_color=self.theme["success"],
            hover_color=self.theme["accent_dark"],
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        submit_btn.pack(side="right")

        widgets_to_lock: list[ctk.CTkBaseClass] = [
            card_entry, exp_entry, cvv_entry, cancel_btn, submit_btn, *quick_buttons
        ]
        for child in amount_holder.winfo_children():
            if isinstance(child, ctk.CTkEntry):
                widgets_to_lock.append(child)

        spinner_state = {"active": False, "frame": 0, "after_id": None}
        spinner_frames = ["\u280B", "\u2819", "\u2839", "\u2838", "\u283C", "\u2834", "\u2826", "\u2827", "\u2807", "\u280F"]

        def stop_spinner() -> None:
            spinner_state["active"] = False
            if spinner_state["after_id"] is not None:
                self.after_cancel(spinner_state["after_id"])
                spinner_state["after_id"] = None
            spinner_label.configure(text="")
            try:
                progress.stop()
            except Exception:  # noqa: BLE001
                pass
            progress.set(0)

        def animate_spinner() -> None:
            if not spinner_state["active"]:
                return
            spinner_label.configure(text=spinner_frames[spinner_state["frame"] % len(spinner_frames)])
            spinner_state["frame"] += 1
            spinner_state["after_id"] = self.after(80, animate_spinner)

        def lock_form(disabled: bool) -> None:
            state = "disabled" if disabled else "normal"
            for w in widgets_to_lock:
                try:
                    w.configure(state=state)
                except Exception:  # noqa: BLE001
                    pass

        def submit() -> None:
            try:
                digits = card_number_var.get()
                if len(digits) != 16:
                    raise ValueError("Kart numarasi 16 hane olmalidir.")
                exp = card_exp_var.get()
                if len(exp) != 5 or exp[2] != "/" or not (exp[:2].isdigit() and exp[3:].isdigit()):
                    raise ValueError("Son kullanma tarihi MM/YY formatinda olmalidir.")
                month = int(exp[:2])
                if month < 1 or month > 12:
                    raise ValueError("Ay degeri 01-12 araliginda olmalidir.")
                year = int(exp[3:])
                current_year = datetime.now().year % 100
                current_month = datetime.now().month
                if (year < current_year) or (year == current_year and month < current_month):
                    raise ValueError("Kartin son kullanma tarihi gecmis.")
                cvv = card_cvv_var.get()
                if not (3 <= len(cvv) <= 4):
                    raise ValueError("CVV 3 veya 4 hane olmalidir.")
                tutar = self._safe_float(amount_var.get())
                if tutar < 1:
                    raise ValueError("Tutar en az 1 TL olmalidir.")
                if tutar > 100000:
                    raise ValueError("Tek seferlik islem limiti 100.000 TL.")
            except Exception as exc:  # noqa: BLE001
                msg.showerror("Odeme Hatasi", str(exc))
                return

            lock_form(True)
            submit_btn.configure(text="Isleniyor...")
            status_text.configure(
                text=f"Banka onayi bekleniyor... {tutar:.2f} TL",
                text_color=self.theme["accent"],
            )
            spinner_state["active"] = True
            spinner_state["frame"] = 0
            try:
                progress.start()
            except Exception:  # noqa: BLE001
                pass
            animate_spinner()
            self.after(2200, lambda: complete(tutar, digits))

        def complete(tutar: float, digits: str) -> None:
            stop_spinner()
            try:
                self.service.bakiye_yukle(
                    self.current_user["kullanici_id"],
                    tutar,
                    f"Kart simulasyonu **** {digits[-4:]}",
                )
            except Exception as exc:  # noqa: BLE001
                lock_form(False)
                submit_btn.configure(text="\U0001F4B3  Yukle")
                status_text.configure(text="Islem basarisiz.", text_color=self.theme["danger"])
                msg.showerror("Odeme Hatasi", str(exc))
                return
            spinner_label.configure(text="\u2705", text_color=self.theme["success"])
            status_text.configure(
                text=f"Odeme basarili! {tutar:.2f} TL bakiyenize eklendi.",
                text_color=self.theme["success"],
            )
            submit_btn.configure(text="\u2713  Tamamlandi", fg_color=self.theme["success"])
            self._refresh_all()
            self.after(1400, lambda: modal.destroy() if modal.winfo_exists() else None)

        submit_btn.configure(command=submit)
        normalize_card_number()
        normalize_expiry()

    def _on_admin_update_user(self) -> None:
        try:
            if self.selected_admin_user_id is None:
                raise ValueError("Once bir kullanici secin.")
            aktif_mi = 1 if self.active_var.get() == "Aktif" else 0
            self.service.kullanici_rol_durum_guncelle(
                self.selected_admin_user_id, self.role_var.get(), aktif_mi
            )
            self._refresh_all()
            msg.showinfo("Basarili", "Kullanici guncellendi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_admin_load_balance(self) -> None:
        try:
            if self.selected_admin_user_id is None:
                raise ValueError("Once bir kullanici secin.")
            tutar = self._safe_float(self.balance_var.get())
            self.service.bakiye_yukle(
                self.selected_admin_user_id, tutar, "Admin bakiye yukleme"
            )
            self.balance_var.set("")
            self._refresh_all()
            msg.showinfo("Basarili", f"{tutar:.2f} TL bakiye yuklendi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_admin_listing_status(self, status: str) -> None:
        try:
            if self.selected_admin_listing_id is None:
                raise ValueError("Once bir ilan secin.")
            listing_id = self.selected_admin_listing_id
            self.service.ilan_durum_guncelle(listing_id, status)
            listing = next(
                (item for item in self.service.ilanlar_getir() if item["ilan_id"] == listing_id),
                None,
            )
            if listing:
                self.service.bildirim_ekle(
                    listing["sahip_id"],
                    "Ilan durumu guncellendi",
                    f"Ilan #{listing_id} durumu: {status}",
                )
            self._refresh_all()
            msg.showinfo("Basarili", "Ilan durumu guncellendi.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Hata", str(exc))

    def _on_backup_database(self) -> None:
        try:
            default_name = f"carshare_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            target = filedialog.asksaveasfilename(
                title="Veritabani Yedegi Kaydet",
                defaultextension=".db",
                initialfile=default_name,
                filetypes=[("SQLite veritabani", "*.db"), ("Tum dosyalar", "*.*")],
            )
            if not target:
                return
            saved = self.service.backup_database(Path(target))
            msg.showinfo("Yedek Olusturuldu", f"Yedek basariyla kaydedildi:\n{saved}")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Yedek Hatasi", str(exc))

    def _on_reset_database(self) -> None:
        try:
            if not self.current_user or self.current_user.get("email") != SYSTEM_ADMIN_EMAIL:
                raise ValueError(
                    "Bu islemi yalnizca sistem yoneticisi (" + SYSTEM_ADMIN_EMAIL + ") gerceklestirebilir."
                )
            confirm = (self.reset_confirm_var.get() if self.reset_confirm_var else "").strip()
            if confirm != "SIFIRLA":
                raise ValueError("Onaylamak icin metin alanina SIFIRLA yazin.")
            if not msg.askyesno(
                "Onay",
                "Tum veriler silinecek. Sadece sistem yoneticisi korunur.\nDevam etmek istediginize emin misiniz?",
                icon="warning",
            ):
                return
            self.service.reset_database()
            if self.reset_confirm_var is not None:
                self.reset_confirm_var.set("")
            self.selected_admin_user_id = None
            self.selected_admin_listing_id = None
            self.selected_admin_ticket_id = None
            self.current_user = self.service.kullanici_getir(self.current_user["kullanici_id"])
            self._refresh_all()
            msg.showinfo("Sifirlama Tamam", "Veritabani sifirlandi. Sistem yoneticisi korundu.")
        except Exception as exc:  # noqa: BLE001
            msg.showerror("Sifirlama Hatasi", str(exc))
