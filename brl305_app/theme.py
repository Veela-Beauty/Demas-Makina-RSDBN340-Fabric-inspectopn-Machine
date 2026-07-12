"""Sanad slate design tokens for the CustomTkinter UI. Light is the default; dark is a toggle.
Colours are (light, dark) tuples so one widget definition themes both modes."""
import customtkinter as ctk

# palette — (light, dark)
BG = ("#f8fafc", "#0a0e1a")
CARD = ("#ffffff", "#0f1626")
FG = ("#0f172a", "#f1f5f9")
MUTED = ("#64748b", "#94a3b8")
BORDER = ("#e2e8f0", "#29344a")
FIELD = ("#ffffff", "#131c30")
PRIMARY = ("#2563eb", "#3b82f6")
PRIMARY_HI = ("#1d4ed8", "#60a5fa")
SUCCESS = ("#16a34a", "#22c55e")
SUCCESS_HI = ("#15803d", "#16a34a")
DANGER = ("#dc2626", "#ef4444")
ON_ACCENT = "#ffffff"

RADIUS = 8
FAMILY = "Segoe UI"


def init(mode="light"):
    ctk.set_appearance_mode(mode if mode in ("light", "dark") else "light")
    ctk.set_default_color_theme("blue")


def font(size=13, weight="normal"):
    return ctk.CTkFont(family=FAMILY, size=size, weight=weight)


def primary_button(master, text, command, width=140):
    return ctk.CTkButton(master, text=text, command=command, corner_radius=RADIUS, width=width,
                         height=34, fg_color=PRIMARY, hover_color=PRIMARY_HI,
                         text_color=ON_ACCENT, font=font(13, "bold"))


def success_button(master, text, command, width=120):
    return ctk.CTkButton(master, text=text, command=command, corner_radius=RADIUS, width=width,
                         height=34, fg_color=SUCCESS, hover_color=SUCCESS_HI,
                         text_color=ON_ACCENT, font=font(13, "bold"))


def ghost_button(master, text, command, width=120):
    return ctk.CTkButton(master, text=text, command=command, corner_radius=RADIUS, width=width,
                         height=34, fg_color=FIELD, hover_color=BORDER, text_color=FG,
                         border_width=1, border_color=BORDER, font=font(13))


def card(master):
    return ctk.CTkFrame(master, corner_radius=RADIUS, fg_color=CARD,
                        border_width=1, border_color=BORDER)


def label(master, text, size=13, muted=False, weight="normal"):
    return ctk.CTkLabel(master, text=text, font=font(size, weight),
                        text_color=(MUTED if muted else FG))


def entry(master, width=180, show=None, placeholder="", textvariable=None, justify="left"):
    return ctk.CTkEntry(master, width=width, height=34, corner_radius=RADIUS, fg_color=FIELD,
                        border_color=BORDER, text_color=FG, font=font(13), show=show,
                        placeholder_text=placeholder, textvariable=textvariable, justify=justify)
