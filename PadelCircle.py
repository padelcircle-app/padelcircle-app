"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   PADEL CIRCLE  ·  COMMAND CENTER                                            ║
║   Once in. Never out.                                                        ║
║                                                                              ║
║   Padel Circle GmbH · Wasserwerkweg 59 · 87700 Memmingen                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

START:   streamlit run PadelCircle.py
PAKETE:  siehe requirements.txt
SETUP:   siehe Setup-Anleitung.docx
"""

import streamlit as st
import pandas as pd
from rapidfuzz import fuzz
from datetime import datetime, date, timedelta
from calendar import monthrange
import time
import random
import re
import secrets
import json
import hashlib

import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go


# ══════════════════════════════════════════════════════════════════════════════
#
#   ⚙️  KONFIGURATION
#
#   Alles mit  ← AUSFÜLLEN  trägst du noch ein.
#   Alles andere ist bereits korrekt auf Padel Circle eingestellt.
#
# ══════════════════════════════════════════════════════════════════════════════

CONFIG = {

    # ── Firma ────────────────────────────────────────────────────────────────
    "name":       "Padel Circle",
    "claim":      "Once in. Never out.",
    "firma":      "Padel Circle GmbH",
    "adresse":    "Wasserwerkweg 59",
    "plz":        "87700",
    "stadt":      "Memmingen",
    "land":       "Deutschland",
    "email":      "info@padelcircle.de",
    "telefon":    "+49 15567 596821",
    "website":    "padelcircle.de",
    "hrb":        "HRB 751430 (Amtsgericht Ulm)",
    "ust_id":     "DE460853012",
    "playtomic":  "https://playtomic.com/de/clubs/padel-circle-memmingen",
    "whatsapp_community": "https://chat.whatsapp.com/Kmn3GnnHYeW9h0GKmGRjug",
    "instagram":  "https://www.instagram.com/padelcircle.de/",

    # ── Anlage ───────────────────────────────────────────────────────────────
    "courts_double":  5,
    "courts_single":  1,
    "oeffnung_von":   6,      # 06:00
    "oeffnung_bis":  24,      # 24:00

    # ── Preise Double Court (€ / 60 Min) ─────────────────────────────────────
    "preis_double_frueh":  28.0,   # Mo–Fr  06:00–12:00
    "preis_double_mittag": 32.0,   # Mo–Fr  12:00–16:00
    "preis_double_prime":  36.0,   # Mo–Fr ab 16:00  +  Sa/So ganztags

    # ── Preise Single Court (€ / 60 Min) ─────────────────────────────────────
    "preis_single_tag":    18.0,   # Mo–Fr  bis 16:00
    "preis_single_prime":  22.0,   # Mo–Fr ab 16:00  +  Sa/So ganztags

    # ── Training ─────────────────────────────────────────────────────────────
    "preis_training":      55.0,   # pro Stunde, Court separat

    # ── EGYM Wellpass ────────────────────────────────────────────────────────
    # Wellpass zahlt 13 € pro Check-in, davon bekommst du 95 %.
    "wellpass_brutto":     13.00,
    "wellpass_anteil":      0.95,
    "admin_gebuehr":       15.00,   # Gebühr wenn Check-in vergessen wurde

    "egym_gym_id":         "1042620",                          # ← AUSFÜLLEN
    "egym_einrichtung":    "Padel Circle Memmingen",    # ← PRÜFEN (exakt wie bei EGYM)
    "wellpass_qr_link":    "https://cdn.jsdelivr.net/gh/padelcircle-app/padelcircle-assets/wellpass.jpg",                          # ← AUSFÜLLEN nach QR-Hosting

    # ── Wellpass-Erkennung ───────────────────────────────────────────────────
    # Wer einen Wellpass-Rabatt bekam, musste einchecken.
    # Double 28–36 € ÷ 4 Spieler = 7–9 € pro Kopf → alles unter 7 € ist Zuzahlung.
    "wellpass_zuzahlung_max":  7.0,
    "single_payer_min":       20.0,   # Zahlt einer ≥ 20 €, zahlt er für die Gruppe

    # ── Ziele ────────────────────────────────────────────────────────────────
    "monatsziel_default":  12000.0,   # € — im Modul Einstellungen änderbar

    # ── Team: zählt nicht als Kunde, bekommt keine Reminder ──────────────────
    "mitarbeiter": [
        "Marcel Sidorov",
        "Mattia Mauta",
        "Mattia Niklas Mauta",
        "Spieler 1", "Spieler 2", "Spieler 3", "Spieler 4",
        "Playtomic",
        # ← ERGÄNZEN: Trainer, Aushilfen
    ],

    # ── Familie / Dauergäste ohne Wellpass-Pflicht ───────────────────────────
    "immer_gruen": [
        "Marcel Sidorov",
        "Mattia Mauta",
        "Mattia Niklas Mauta",
        "Bernd Schelenz",
        # ← ERGÄNZEN
    ],
}


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#   🎨  BRANDING  —  identisch zur Website padelcircle.de
# ══════════════════════════════════════════════════════════════════════════════

C = {
    # Hintergrund-Ebenen (dunkel, wie auf der Website)
    "ink0":       "#0B0C10",   # Seitenhintergrund
    "ink1":       "#111218",   # Karten
    "ink2":       "#15171F",   # erhöhte Flächen
    "ink3":       "#1C1F28",   # Eingabefelder, Hover

    # Akzent
    "volt":       "#DFFF00",   # Signalfarbe
    "volt_dim":   "#B8D400",
    "volt_glow":  "rgba(223,255,0,.30)",
    "flash":      "#FF3131",

    # Blau
    "blue":       "#1244A8",
    "blue_soft":  "#2E5BC9",
    "anthracite": "#373A49",

    # Text
    "text":       "#F2F3F5",
    "dim":        "#9BA0AB",
    "faint":      "#5A606E",

    # Linien
    "line":       "rgba(255,255,255,.08)",
    "line_str":   "rgba(255,255,255,.14)",

    # Status
    "ok":         "#4ADE80",
    "warn":       "#FBBF24",
    "err":        "#FF5A5A",

    # Radien
    "r_sm":       "8px",
    "r":          "14px",
    "r_lg":       "22px",
}

# Logo aus der Website (Padel-Schläger + Swoosh)
LOGO_SVG = """<svg viewBox="100 220 780 540" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="m861 334c12.77-47.61-30.12-81.79-73.33-85.67-43.21-3.88-90.3 8.51-124.42 34.92-34.13 26.41-53.28 52.94-69.94 92.06-16.67 39.11-23.94 95.8-20.31 139.69 3.64 43.88 23.72 79.82 64.98 97.03 41.25 17.2 94.37 5.29 130.33-15.72 35.95-21.02 62.66-46.41 76.69-85.31-13.48 8-22.68 24.73-39 27-0.54-5.36 4.23-9.04 5-14-28.66 15.16-53.05 41.87-87 45 6.04-9.14 13.86-17.63 20.08-26.92 6.22-9.28 12.81-18.4 19.67-27.33 6.86-8.93 13.47-17.01 22.02-24.98 8.55-7.97 18.16-13.04 28.55-18.45 10.39-5.41 28.02-4.36 36.98 1.38 8.97 5.73 13.84 27.12 22.93 16.53 9.08-10.6 1.14-25.29-7.15-33.31-8.28-8.02-26.62-8.69-38.06-6.9-11.43 1.8-23.39 7.72-32.94 14.06-9.56 6.34-18.39 12.9-26.31 20.69-7.92 7.79-14.61 16.38-22.02 24.98-7.4 8.6-13.83 17.36-20.5 26.5-6.67 9.14-13.29 16.78-23.55 22.45-10.27 5.66-27.9 6.3-38.45 0.05-10.56-6.24-16.89-12.96-23.5-23.5-6.6-10.55-9.55-23.49-10.42-36.58-0.87-13.09-0.59-31.97 1.68-44.66 2.26-12.69 5.03-23.78 13.24-33.76 8.21-9.98 21.67-10.44 32.73-14.27 11.05-3.84 22.94-7.23 32.79-13.21 9.85-5.98 19.24-11.26 27.31-19.69 8.07-8.43 14.47-16.66 20-27 5.52-10.35 9.21-20.34 17.17-29.83 7.96-9.5 23.98-9.02 28.82 3.68 4.85 12.7 0.39 27.22-4.76 38.38-5.16 11.15-10.98 18.71-17.31 28.69 8.8-0.41 13.95-9.28 22-12 3.23 12.26-5.13 23.71-5 36 21.3-12.92 41.23-34.56 51-57 6.74 1.95 11.94 7.08 15.08 13.92 3.14 6.85 6.41 12.99 7.93 21.07 1.52 8.08 3.62 15.8 3.99 25.01 0.37 9.21 2.81 17.24 1 28-1.81 10.76 6.15 16.24 7.67 4.67 1.52-11.57 3.39-15.51 3.33-25.67-0.06-10.16 0.5-19.74-0.22-28.78-0.72-9.04-3.54-15.42-5.8-23.2-2.27-7.77-5.31-13.22-9.23-19.77-3.92-6.56-8.23-9.33-13.75-14.25zm-101-29c-14.81 43.31-56.02 80.34-102 86 19.82-40.38 58.12-75.89 102-86z"/><path fill="currentColor" d="m437 545c37.94-11.05 69.71-34.63 96.23-65.77 26.52-31.14 48.96-75.98 32.08-117.53-16.89-41.56-64.51-58.56-107.31-54.7-42.8 3.86-85.33 15.53-120 41 17.12-4.88 33.96-11.11 51-16-29.76 14.87-59.14 28.52-85.25 50.75-26.11 22.24-51.76 54.03-43.75 90.25 16.99-26.31 43.27-42.59 68.25-59.75 24.99-17.15 58.86-31.4 86.53-41.47 27.66-10.08 83.17-21.3 93.89 14.55 10.72 35.85-20.3 61.02-40.97 84.37-20.67 23.35-50.6 38.4-78.7 48.3 1.42-9.73 5.78-19.32 8.22-28.78 2.45-9.46 6.86-18.29 9.45-27.55 2.6-9.25 6.32-18.74 9.4-27.6 3.08-8.86 8.18-20.68 3.93-28.07-3.69 10.93-8.34 24.28-18 31-0.14-7.45 0.78-15.23-2-22-9.97 7.85-12.33 21.43-18.23 32.77-5.9 11.35-10.75 22.28-15.32 34.28-4.57 12-9.9 22.68-14.22 35.22-4.32 12.55-19.63 13.4-31.23 15.5-11.59 2.09-28.71 3.55-43 4 7.35 24.04 41.49 20.32 62 20-8.16 31.15-16.98 62.12-26 93-20.25 4.37-45.09 11.42-66 11-20.91-0.42-48.26 3.36-60.69-15.3-12.44-18.67 13.99-37.04 18.69-52.7-17.89 11.95-43.79 39.31-29 62 1.45 1.9 5.16 5.59 7 7 21.63 14.1 51.21 13 77 13 2.09-0.2 5.23-1 8-1 14.07 0.23 27.24-3.11 41-4-0.08 6.35-4.18 11.6-4 18 8.29 1.7 9.2-19.24 17.92-14.92 8.72 4.33 13.09-1.7 22.08-4.08 1.83 18.87 10.47 1.58 12.68-7.32 2.2-8.91 18.31-9.72 26.3-13.7 7.98-3.99 20.01-7.18 28.33-11.67 8.31-4.5 17.47-8.57 26-13 8.52-4.44 17.54-9.13 25.46-14.53 7.92-5.4 17.09-9.51 24.48-15.52 7.39-6.01 15.37-11.47 22.5-17.5 7.13-6.02 14.39-12.09 19.25-19.75-51.41 34.64-108.19 61.08-167 79 3.5-14.59 7.42-31.96 12.07-45.93 4.66-13.96 4.12-33.54 18.91-38.09 14.78-4.56 28.72-9.59 42.33-15.67 13.6-6.09 24.03-12.81 35.69-21.31 1.64-1.94 3.89-3.45 6-5-0.65 3.93-5.53 5.23-8 8-9.69 8.32-19 17.08-29 25z"/><path fill="currentColor" d="m208 534c-3.48 4.69-9.75 9.75-14 14-34.32 29.33-70.94 76.55-43.23 122.23 27.71 45.68 93.9 49.98 139.24 40.38 45.33-9.6 91.51-29.73 132.22-50.78 40.71-21.05 74.83-43.37 109.77-73.23 7.34-6.27 14.68-13.61 21-21 3.4-3.98 6.34-8.53 10-12 4.63 15.8 10.8 31.64 21 45 0.75 1.68 2.43 3.04 4 4-0.84 1.29-1.92 2.83-3 4-45.42 38.81-88.34 68.58-143.22 92.78-54.89 24.19-124.2 49.22-186.78 49.22-8.67 0-17.33 0-26 0-47.22 0-116-26.13-116-83 0-2.33-0.04-4.67 0-7 0.48-27.51 16.76-54.21 35.25-73.75 18.48-19.54 37.7-37.27 61.75-47.25 0.76 2.19-1.3 3.32-2 5z"/><path fill="currentColor" d="m314 757c116.34-7.9 235.89-42.71 317-132-10.84-2.93-19.72-10.67-28.92-17.08-9.2-6.41-15.81 9.56-24 15.16-8.19 5.6-16.49 12.94-25.63 18.62-9.14 5.68-18.39 11.59-28 17-9.61 5.41-18.88 10.98-29.16 15.84-10.27 4.87-21.16 9.54-31.84 14.16-10.69 4.61-21.81 7.94-33 12-11.19 4.05-21.99 8.08-34 10.98-12.01 2.9-23.59 6.37-36.22 8.79-12.63 2.42-25.08 4.66-38.33 6.67-13.25 2.01-27.75 1.99-41.67 3.33-13.92 1.34-30.43-2.67-44-1-1.38-2.14-4.81-0.48-7-1 1 1.36 3.36 1.62 5 2 17.12 3.98 36.07 6 54 6 2.04 0.2 5.23 1 8 1 11.67 0 23.33 0 35 0 2.77 0 5.91-0.8 8-1z"/><path fill="currentColor" d="m670 636c-12.92-0.26-26.12-7.69-33.25 2.75-7.12 10.45-15.2 14.3-23 23-7.79 8.7-16.94 13.1-25.67 20.33-8.72 7.23-19.4 10.87-28.85 17.15-9.46 6.27-19.52 10.28-30 15-10.48 4.72-21.08 9.85-32.16 13.84-11.08 4-22.57 8.29-34.06 11.94-11.49 3.65-24.02 6.81-35.78 10.21-11.77 3.4-24.25 5.95-36.23 8.78-1.9-0.23-3.95 0.57-5 2 5.64 0.72 12.07-0.52 17-1 4.33 0 8.67 0.12 13 0 2.19-0.06 4.42-0.75 6-1 100.95-12.49 201.5-48.63 276-122-7 -0.1-14 0.14-21 0-1.7-0.16-4.59-0.95-7-1z"/></svg>"""

LOADING = {
    "laden": [
        "🔵 Der Circle öffnet sich…",
        "⚡ Bandeja im Anflug…",
        "👀 Sechs Courts im Blick…",
        "🎾 Vibora wird geschärft…",
        "😏 Once in. Never out.",
    ],
    "verarbeite": [
        "⚡ Rechne den Circle durch…",
        "👀 Zahlen im Glaskasten…",
        "🎾 Punkt für Punkt…",
        "🔵 Memmingen wird vermessen…",
    ],
    "speichere": [
        "🔵 Im Circle gesichert…",
        "⚡ Punkt gespeichert…",
        "🎾 Match dokumentiert…",
        "😏 Never out.",
    ],
}

# ── Abgeleitet ────────────────────────────────────────────────────────────────

WELLPASS_WERT   = round(CONFIG["wellpass_brutto"] * CONFIG["wellpass_anteil"], 2)   # 12.35
ADMIN_GEBUEHR   = CONFIG["admin_gebuehr"]
QR_LINK         = CONFIG["wellpass_qr_link"]
COURTS_GESAMT   = CONFIG["courts_double"] + CONFIG["courts_single"]
OEFFNUNGSSTUNDEN = CONFIG["oeffnung_bis"] - CONFIG["oeffnung_von"]                  # 18
KAPAZITAET_TAG  = COURTS_GESAMT * OEFFNUNGSSTUNDEN                                  # 108 Court-Stunden

MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]
WOCHENTAGE_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
                 "Freitag", "Samstag", "Sonntag"]
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def court_preis(zeitpunkt: datetime, single: bool = False) -> float:
    """Listenpreis für einen Slot — für Auslastungs- und Potenzialrechnungen."""
    ist_we = zeitpunkt.weekday() >= 5
    stunde = zeitpunkt.hour
    if single:
        if ist_we or stunde >= 16:
            return CONFIG["preis_single_prime"]
        return CONFIG["preis_single_tag"]
    if ist_we or stunde >= 16:
        return CONFIG["preis_double_prime"]
    if stunde >= 12:
        return CONFIG["preis_double_mittag"]
    return CONFIG["preis_double_frueh"]


# ══════════════════════════════════════════════════════════════════════════════
#   🔧  HELPER
# ══════════════════════════════════════════════════════════════════════════════

def lade_text(art: str = "laden") -> str:
    return random.choice(LOADING.get(art, ["⏳ Einen Moment…"]))


def normalize_name(name) -> str:
    """Namen vereinheitlichen für den Abgleich Buchung ↔ Check-in."""
    if name is None:
        return ""
    try:
        if pd.isna(name):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(name).strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("-", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


MITARBEITER_NORM = {normalize_name(n) for n in CONFIG["mitarbeiter"]}
IMMER_GRUEN_NORM = {normalize_name(n) for n in CONFIG["immer_gruen"]}
TEAM_NORM = MITARBEITER_NORM | IMMER_GRUEN_NORM


def is_true(val) -> bool:
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    return val in (True, "True", "true", "TRUE", 1, "1", "Ja", "ja", "JA")


_DATE_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                 "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y",
                 "%m/%d/%Y", "%Y/%m/%d")


def parse_date_safe(val):
    if val is None or val == "" or val == "-":
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        d = pd.to_datetime(s, errors="coerce", dayfirst=True)
        return d.date() if pd.notna(d) else None
    except Exception:
        return None


def parse_datetime_safe(val):
    """Wie parse_date_safe, gibt aber datetime inkl. Uhrzeit zurück."""
    if val is None or val == "":
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        d = pd.to_datetime(s, errors="coerce", dayfirst=True)
        return d.to_pydatetime() if pd.notna(d) else None
    except Exception:
        return None


def parse_betrag(val) -> float:
    if val is None:
        return 0.0
    try:
        if pd.isna(val):
            return 0.0
    except (TypeError, ValueError):
        pass
    s = str(val).replace("€", "").replace(" ", "").replace("\xa0", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def euro(val) -> str:
    try:
        return f"{float(val):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "0,00 €"


def euro_kurz(val) -> str:
    """1234.5 → '1,2k €'  ·  für enge Kacheln"""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "0 €"
    if abs(v) >= 1000:
        return f"{v/1000:.1f}k €".replace(".", ",")
    return f"{v:.0f} €"


def prozent(teil, ganz) -> float:
    try:
        return (float(teil) / float(ganz) * 100) if float(ganz) else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def telefon_normalisieren(phone) -> str:
    if phone is None or str(phone).strip() == "":
        return ""
    try:
        if pd.isna(phone):
            return ""
    except (TypeError, ValueError):
        pass
    p = re.sub(r"[^\d+]", "", str(phone).strip())
    if not p:
        return ""
    if p.startswith("+"):
        return p
    if p.startswith("00"):
        return "+" + p[2:]
    if p.startswith("0"):
        return "+49" + p[1:]
    if p.startswith("49"):
        return "+" + p
    return "+49" + p


def datum_lang(datum_str: str) -> str:
    """'2026-07-21' → 'Dienstag, 21.07.2026'"""
    try:
        d = datetime.strptime(str(datum_str), "%Y-%m-%d").date()
        return f"{WOCHENTAGE_DE[d.weekday()]}, {d.strftime('%d.%m.%Y')}"
    except (ValueError, TypeError):
        return str(datum_str)


def datum_kurz(datum_str: str) -> str:
    try:
        d = datetime.strptime(str(datum_str), "%Y-%m-%d").date()
        return d.strftime("%d.%m.")
    except (ValueError, TypeError):
        return str(datum_str)


def split_name(vollname: str):
    teile = str(vollname).strip().split()
    if not teile:
        return "", ""
    if len(teile) == 1:
        return teile[0], ""
    return teile[0], " ".join(teile[1:])


def stunde_aus_zeit(zeit_str) -> int:
    """'18:30' → 18   ·   gibt -1 zurück wenn nicht lesbar"""
    m = re.search(r"(\d{1,2}):(\d{2})", str(zeit_str))
    return int(m.group(1)) if m else -1


# ══════════════════════════════════════════════════════════════════════════════
#   💾  GOOGLE SHEETS  —  performance-optimiert
#
#   Wichtigste Optimierung gegenüber der Vorlage:
#   Die Verbindung wird EINMAL aufgebaut und wiederverwendet (cache_resource).
#   Vorher wurde bei jedem einzelnen Datenzugriff neu authentifiziert —
#   das kostete pro Seitenaufruf mehrere Sekunden.
# ══════════════════════════════════════════════════════════════════════════════

SHEET_SPALTEN = {
    "playtomic_raw":    None,
    "buchungen":        None,
    "checkins":         None,
    "customers":        None,
    "corrections":      ["key", "date", "behoben", "timestamp"],
    "whatsapp_log":     ["key", "name", "datum", "betrag", "to_number", "art", "timestamp"],
    "name_mapping":     ["buchung_name", "checkin_name", "confidence", "timestamp", "confirmed_by"],
    "rejected_matches": ["buchung_name", "checkin_name", "timestamp"],
    "nachmeldungen":    ["name", "email", "geburtstag", "checkin_datum", "status", "timestamp"],
    "auth_tokens":      ["token", "created", "expires"],
    "settings":         ["key", "value"],
}


@st.cache_resource(show_spinner=False)
def _sheet_verbindung():
    """
    Verbindung zum Google Sheet — wird nur EINMAL pro Session aufgebaut.
    Das ist der grösste Performance-Hebel der ganzen App.
    """
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["google_sheets"]["sheet_id"])


def get_sheet():
    try:
        return _sheet_verbindung()
    except KeyError as e:
        st.error(f"❌ Zugangsdaten fehlen in den Secrets: {e}")
        st.caption("Siehe Setup-Anleitung, Kapitel „Secrets eintragen“.")
        return None
    except Exception as e:
        st.error(f"❌ Google Sheets nicht erreichbar: {str(e)[:160]}")
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def loadsheet(name: str, cols=None) -> pd.DataFrame:
    """Ein Tabellenblatt laden. Legt es an, falls es fehlt."""
    leer = pd.DataFrame(columns=cols) if cols else pd.DataFrame()
    sheet = get_sheet()
    if sheet is None:
        return leer
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        try:
            sheet.add_worksheet(title=name, rows=2000, cols=30)
        except Exception:
            pass
        return leer
    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ Google-Limit erreicht — kurz warten, dann neu laden.")
        return leer

    try:
        daten = ws.get_all_records()
        return pd.DataFrame(daten) if daten else leer
    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ Google-Limit erreicht — kurz warten, dann neu laden.")
        return leer


def savesheet(df: pd.DataFrame, name: str, versuche: int = 3) -> bool:
    """Tabellenblatt überschreiben, mit Wiederholung bei Rate-Limit."""
    for versuch in range(versuche):
        sheet = get_sheet()
        if sheet is None:
            return False
        try:
            try:
                ws = sheet.worksheet(name)
            except gspread.exceptions.WorksheetNotFound:
                ws = sheet.add_worksheet(title=name, rows=2000, cols=30)

            ws.clear()

            if not df.empty:
                out = df.copy()
                out.columns = [str(c) for c in out.columns]

                def zelle(x):
                    """Jeden Wert in einen sauberen String verwandeln."""
                    if x is None:
                        return ""
                    if isinstance(x, float):
                        if x != x or x in (float("inf"), float("-inf")):
                            return ""
                        return f"{x:.10g}"
                    try:
                        if pd.isna(x):
                            return ""
                    except (TypeError, ValueError):
                        pass
                    t = str(x).strip()
                    return "" if t.lower() in ("nan", "nat", "none", "<na>",
                                               "null", "inf", "-inf") else t

                zeilen = [out.columns.tolist()]
                for reihe in out.itertuples(index=False, name=None):
                    zeilen.append([zelle(v) for v in reihe])

                ws.update(zeilen, value_input_option="RAW")
            return True

        except Exception as e:
            if "429" in str(e) and versuch < versuche - 1:
                wartezeit = 8 + versuch * 8
                st.warning(f"⚠️ Google-Limit — warte {wartezeit}s…")
                time.sleep(wartezeit)
            else:
                st.error(f"❌ Speichern fehlgeschlagen: {str(e)[:150]}")
                return False
    return False


def _zeilen_hash(df: pd.DataFrame, spalten: list = None) -> pd.Series:
    """
    Eindeutiger Fingerabdruck je Zeile.

    Sicherer als ein Teilschlüssel: Playtomic liefert bei offenen
    Zahlungen "-" als Payment id, wodurch mehrere Zeilen denselben
    Schlüssel bekämen.
    """
    if df.empty:
        return pd.Series(dtype=str)
    nutz = [c for c in (spalten or df.columns) if c in df.columns]
    if not nutz:
        nutz = list(df.columns)

    def norm(v):
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except (TypeError, ValueError):
            pass
        t = str(v).strip()
        # Zahlen vereinheitlichen, damit 13,5 / 13.5 / 13.50 gleich sind
        try:
            f = float(t.replace(",", "."))
            return f"{f:.4f}"
        except ValueError:
            return t.lower()

    roh = df[nutz].map(norm).agg("␟".join, axis=1)
    # Präfix "h", damit Google Sheets den Hash nie als Zahl interpretiert
    return roh.map(lambda s: "h" + hashlib.md5(s.encode()).hexdigest()[:16])


def append_rows(neu: pd.DataFrame, sheet_name: str, key_cols: list) -> int:
    """
    Neue Zeilen anhängen, exakte Dubletten überspringen.

    Vergleicht den vollständigen Zeileninhalt, nicht nur einzelne
    Spalten — dieselbe Datei mehrfach hochzuladen ändert nichts.
    """
    if neu.empty:
        return 0

    alt = loadsheet(sheet_name)
    gemeinsam = [c for c in neu.columns if alt.empty or c in alt.columns]

    neu = neu.copy()
    neu["_hash"] = _zeilen_hash(neu, gemeinsam)
    neu = neu.drop_duplicates(subset=["_hash"])

    if not alt.empty:
        alt = alt.copy()
        if "_hash" in alt.columns:
            vorhanden = set(alt["_hash"].astype(str))
        else:
            alt["_hash"] = _zeilen_hash(alt, gemeinsam)
            vorhanden = set(alt["_hash"])
        neu = neu[~neu["_hash"].isin(vorhanden)]
        if neu.empty:
            return 0
        gesamt = pd.concat([alt, neu], ignore_index=True)
    else:
        gesamt = neu

    savesheet(gesamt, sheet_name)
    return len(neu)


def cache_leeren():
    """Alle Datencaches leeren. Die Verbindung bleibt bestehen."""
    loadsheet.clear()
    for fn_name in ("tages_kennzahlen", "verfuegbare_tage", "monats_kennzahlen",
                    "spieler_statistik", "auslastung_matrix", "rejected_matches_laden",
                    "einstellungen_laden"):
        fn = globals().get(fn_name)
        if fn is not None and hasattr(fn, "clear"):
            try:
                fn.clear()
            except Exception:
                pass
    st.session_state.name_mapping_cache = None


# ══════════════════════════════════════════════════════════════════════════════
#   ⚙️  EINSTELLUNGEN  (persistent im Sheet)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def einstellungen_laden() -> dict:
    df = loadsheet("settings", SHEET_SPALTEN["settings"])
    if df.empty or "key" not in df.columns:
        return {}
    out = {}
    for _, row in df.iterrows():
        wert = row.get("value", "")
        try:
            out[str(row["key"])] = json.loads(str(wert))
        except (json.JSONDecodeError, TypeError):
            out[str(row["key"])] = wert
    return out


def einstellung_setzen(key: str, wert):
    df = loadsheet("settings", SHEET_SPALTEN["settings"])
    neu = pd.DataFrame([{"key": key, "value": json.dumps(wert)}])
    if not df.empty and "key" in df.columns:
        df = df[df["key"].astype(str) != key]
    savesheet(pd.concat([df, neu], ignore_index=True), "settings")
    einstellungen_laden.clear()
    loadsheet.clear()


def einstellung(key: str, standard=None):
    return einstellungen_laden().get(key, standard)


def monatsziel(monat: str = None) -> float:
    """Monatsziel in €. Pro Monat überschreibbar, sonst Standardwert."""
    if monat:
        spezial = einstellung(f"monatsziel_{monat}")
        if spezial is not None:
            try:
                return float(spezial)
            except (TypeError, ValueError):
                pass
    try:
        return float(einstellung("monatsziel", CONFIG["monatsziel_default"]))
    except (TypeError, ValueError):
        return CONFIG["monatsziel_default"]


# ══════════════════════════════════════════════════════════════════════════════
#   🔒  LOGIN
# ══════════════════════════════════════════════════════════════════════════════

def token_speichern(token: str) -> bool:
    try:
        df = loadsheet("auth_tokens", SHEET_SPALTEN["auth_tokens"])
        jetzt = datetime.now()
        if not df.empty and "expires" in df.columns:
            df = df.copy()
            df["_exp"] = pd.to_datetime(df["expires"], errors="coerce")
            df = df[df["_exp"] > jetzt].drop(columns=["_exp"])
        neu = pd.DataFrame([{
            "token": token,
            "created": jetzt.isoformat(),
            "expires": (jetzt + timedelta(days=30)).isoformat(),
        }])
        savesheet(pd.concat([df, neu], ignore_index=True), "auth_tokens")
        loadsheet.clear()
        return True
    except Exception:
        return False


def token_gueltig(token: str) -> bool:
    if not token:
        return False
    try:
        df = loadsheet("auth_tokens", SHEET_SPALTEN["auth_tokens"])
        if df.empty or "token" not in df.columns:
            return False
        treffer = df[df["token"].astype(str) == str(token)]
        if treffer.empty:
            return False
        ablauf = pd.to_datetime(treffer.iloc[0]["expires"], errors="coerce")
        return pd.notna(ablauf) and ablauf > datetime.now()
    except Exception:
        return False


def login() -> bool:
    url_token = st.query_params.get("auth", None)
    if url_token and token_gueltig(url_token):
        st.session_state["auth_ok"] = True
        return True

    if st.session_state.get("auth_ok", False):
        return True

    def pruefen():
        eingabe = st.session_state.get("pw_input", "")
        soll = st.secrets.get("passwords", {}).get("admin_password", "")
        if eingabe and soll and eingabe == soll:
            t = secrets.token_urlsafe(32)
            if token_speichern(t):
                st.query_params["auth"] = t
            st.session_state["auth_ok"] = True
            st.session_state["auth_fehler"] = False
            st.session_state.pop("pw_input", None)
        elif eingabe:
            st.session_state["auth_fehler"] = True

    st.markdown(f"""
    <div class="pc-login">
      <div class="mark">{LOGO_SVG}</div>
      <h1>PADEL CIRCLE</h1>
      <div class="sub">Command Center</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.text_input("Passwort", type="password", on_change=pruefen,
                      key="pw_input", placeholder="••••••••",
                      label_visibility="collapsed")
        if st.session_state.get("auth_fehler"):
            st.error("Falsches Passwort.")
        st.caption("Nach dem Login steht ein Token in der URL — "
                   "als Lesezeichen speichern und du bleibst 30 Tage angemeldet.")

    st.markdown('<div class="pc-claim">ONCE IN &nbsp;·&nbsp; NEVER OUT</div>',
                unsafe_allow_html=True)
    return False


# ══════════════════════════════════════════════════════════════════════════════
#   📄  CSV-PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _text_lesen(datei) -> str:
    inhalt = datei.read()
    datei.seek(0)
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return inhalt.decode(enc)
        except (UnicodeDecodeError, AttributeError):
            continue
    return ""


def parse_playtomic(datei) -> pd.DataFrame:
    """Playtomic-Export. Findet die Kopfzeile automatisch."""
    text = _text_lesen(datei)
    if not text:
        st.error("❌ Playtomic-CSV: Encoding nicht erkannt.")
        return pd.DataFrame()

    zeilen = text.strip().split("\n")
    pflicht = ["User name", "Product SKU", "Service date", "Total"]

    kopf = next((i for i, z in enumerate(zeilen)
                 if all(sp in z for sp in pflicht)), None)

    if kopf is None:
        st.error("❌ Kopfzeile nicht gefunden.")
        st.caption("Gesucht: " + ", ".join(pflicht))
        with st.expander("Erste Zeilen der Datei"):
            for i, z in enumerate(zeilen[:15]):
                st.text(f"{i}: {z[:110]}")
        return pd.DataFrame()

    try:
        datei.seek(0)
        df = pd.read_csv(datei, sep=";", skiprows=kopf, engine="python",
                         on_bad_lines="skip", encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.replace("\ufeff", "")
    except Exception as e:
        st.error(f"❌ Playtomic-CSV: {str(e)[:150]}")
        return pd.DataFrame()

    fehlt = [c for c in pflicht if c not in df.columns]
    if fehlt:
        st.error(f"❌ Fehlende Spalten: {', '.join(fehlt)}")
        return pd.DataFrame()
    return df



def parse_bookings(datei) -> pd.DataFrame:
    """
    Playtomic Bookings-Export (bookings-download.csv).
    Enthält Teilnehmer, E-Mails, Court und Preis — die Basis der
    Wellpass-Erkennung.
    """
    text = _text_lesen(datei)
    if not text:
        st.error("❌ Bookings-CSV: Encoding nicht erkannt.")
        return pd.DataFrame()

    probe = text[:3000]
    trenner = "," if probe.count(",") > probe.count(";") else ";"

    try:
        datei.seek(0)
        df = pd.read_csv(datei, sep=trenner, engine="python",
                         on_bad_lines="skip", encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.replace("\ufeff", "")
    except Exception as e:
        st.error(f"❌ Bookings-CSV: {str(e)[:150]}")
        return pd.DataFrame()

    pflicht = ["booking_start_date", "price", "resource_name", "participant_name_1"]
    fehlt = [c for c in pflicht if c not in df.columns]
    if fehlt:
        st.error(f"❌ Fehlende Spalten im Bookings-Export: {', '.join(fehlt)}")
        st.caption("Gefunden: " + ", ".join(list(df.columns)[:12]) + " …")
        return pd.DataFrame()
    return df


def listenpreis(start: datetime, minuten: float, single_court: bool) -> float:
    """Regulärer Preis einer Buchung ohne jeden Rabatt."""
    if start is None or not minuten:
        return 0.0
    we = start.weekday() >= 5
    std = start.hour
    if single_court:
        basis = (CONFIG["preis_single_prime"] if (we or std >= 16)
                 else CONFIG["preis_single_tag"])
    else:
        if we or std >= 16:
            basis = CONFIG["preis_double_prime"]
        elif std >= 12:
            basis = CONFIG["preis_double_mittag"]
        else:
            basis = CONFIG["preis_double_frueh"]
    return round(basis * float(minuten) / 60.0, 2)


def court_plaetze(court_name: str) -> int:
    """
    Wie viele Plätze hat der Court?
    Playtomic berechnet den Preis immer auf die volle Platzzahl —
    auch wenn nur zwei Leute eingetragen sind. Die leeren Plätze
    gehen auf den Besitzer der Buchung.
    """
    return 2 if "single" in str(court_name).lower() else 4


def wellpass_anzahl(liste: float, bezahlt: float, plaetze: int) -> int:
    """
    Wie viele Wellpass-Rabatte stecken in dieser Buchung?

    Playtomic zieht pro Wellpass-Spieler den kleineren Wert von
    (Preis pro Platz, Wellpass-Brutto) ab. Aus der Preislücke lässt
    sich die Anzahl zurückrechnen.
    """
    rabatt = round(liste - bezahlt, 2)
    if rabatt < 0.5 or liste <= 0:
        return 0
    pro_platz = liste / max(plaetze, 1)
    abzug = min(pro_platz, CONFIG["wellpass_brutto"])
    if abzug <= 0:
        return 0
    anzahl = rabatt / abzug
    gerundet = int(round(anzahl))
    if abs(anzahl - gerundet) > 0.12:
        return 0
    return max(0, min(gerundet, plaetze))


def _teilnehmer_liste(row) -> list:
    """[(Name, E-Mail), …] einer Buchung."""
    out = []
    for i in (1, 2, 3, 4):
        name = row.get(f"participant_name_{i}")
        if pd.isna(name) or not str(name).strip():
            continue
        mail = row.get(f"participant_email_{i}", "")
        mail = "" if pd.isna(mail) else str(mail).strip()
        # Apple-Weiterleitungsadressen sind für EGYM unbrauchbar
        if "privaterelay.appleid.com" in mail:
            mail = ""
        out.append((str(name).strip(), mail))
    return out


def parse_checkins(datei) -> pd.DataFrame:
    """EGYM-Wellpass Check-in-Export."""
    text = _text_lesen(datei)
    if not text:
        st.error("❌ Check-in-CSV: Encoding nicht erkannt.")
        return pd.DataFrame()

    probe = text[:2000]
    trenner = ";" if probe.count(";") > probe.count(",") else ","
    zeilen = text.strip().split("\n")
    kopf = next((i for i, z in enumerate(zeilen)
                 if "Nachname" in z or ("Name" in z and "Datum" in z)), 0)

    try:
        datei.seek(0)
        df = pd.read_csv(datei, sep=trenner, skiprows=kopf, engine="python",
                         on_bad_lines="skip", encoding="utf-8-sig")
        df.columns = (df.columns.str.strip()
                      .str.replace("\ufeff", "").str.replace('"', ""))
    except Exception as e:
        st.error(f"❌ Check-in-CSV: {str(e)[:150]}")
        return pd.DataFrame()

    um = {}
    for sp in df.columns:
        low = sp.lower()
        if "nachname" in low or low == "name":
            um[sp] = "Vor- & Nachname"
        elif "datum" in low or "date" in low:
            um[sp] = "Datum"
        elif "zeit" in low or "time" in low:
            um[sp] = "Zeit"
    return df.rename(columns=um) if um else df


def parse_kunden(datei) -> pd.DataFrame:
    """
    Kundenliste einlesen. Erkennt Spaltennamen in Deutsch und Englisch
    und setzt getrennte Vor-/Nachnamen automatisch zusammen.
    """
    text = _text_lesen(datei)
    if not text:
        return pd.DataFrame()
    probe = text[:4000]
    trenner = ";" if probe.count(";") > probe.count(",") else ","
    try:
        datei.seek(0)
        df = pd.read_csv(datei, sep=trenner, engine="python",
                         on_bad_lines="skip", encoding="utf-8-sig")
        df.columns = (df.columns.str.strip().str.replace("\ufeff", "")
                      .str.replace('"', "").str.lower())
    except Exception as e:
        st.error(f"❌ Kunden-CSV: {str(e)[:150]}")
        return pd.DataFrame()

    if df.empty:
        return df

    um, vorname_sp, nachname_sp = {}, None, None
    for sp in df.columns:
        s_ = sp.strip()
        if s_ in ("name", "full name", "fullname", "vor- & nachname",
                  "vor & nachname", "kunde", "kundenname", "spieler",
                  "player", "player name", "teilnehmer"):
            um[sp] = "name"
        elif s_ in ("vorname", "first name", "firstname", "given name"):
            vorname_sp = sp
        elif s_ in ("nachname", "last name", "lastname", "surname",
                    "family name"):
            nachname_sp = sp
        elif any(k in s_ for k in ("phone", "telefon", "mobil", "handy",
                                   "tel.", "rufnummer", "nummer", "contact")):
            um[sp] = "phone_number"
        elif "mail" in s_:
            um[sp] = "email"
        elif any(k in s_ for k in ("geburt", "birth", "geb.", "geb-", "dob")):
            um[sp] = "geburtstag"

    if um:
        df = df.rename(columns=um)

    # Getrennte Namensspalten zusammenführen
    if "name" not in df.columns and vorname_sp and nachname_sp:
        df["name"] = (df[vorname_sp].fillna("").astype(str).str.strip() + " " +
                      df[nachname_sp].fillna("").astype(str).str.strip()).str.strip()
    elif "name" not in df.columns and (vorname_sp or nachname_sp):
        df["name"] = df[vorname_sp or nachname_sp].fillna("").astype(str).str.strip()

    return df


# ══════════════════════════════════════════════════════════════════════════════
#   🔍  NAME-MATCHING
# ══════════════════════════════════════════════════════════════════════════════

def mapping_laden() -> dict:
    cached = st.session_state.get("name_mapping_cache")
    if cached is not None:
        return cached
    df = loadsheet("name_mapping")
    mapping = {}
    if not df.empty and {"buchung_name", "checkin_name"} <= set(df.columns):
        for _, row in df.iterrows():
            mapping[str(row["buchung_name"])] = {
                "checkin_name": str(row["checkin_name"]),
                "confidence": row.get("confidence", 100),
                "timestamp": row.get("timestamp", ""),
                "confirmed_by": row.get("confirmed_by", "auto"),
            }
    st.session_state.name_mapping_cache = mapping
    return mapping


def mapping_speichern(mapping: dict):
    zeilen = [{
        "buchung_name": b,
        "checkin_name": d["checkin_name"] if isinstance(d, dict) else d,
        "confidence": d.get("confidence", 100) if isinstance(d, dict) else 100,
        "timestamp": (d.get("timestamp") if isinstance(d, dict) else None)
                     or datetime.now().isoformat(),
        "confirmed_by": d.get("confirmed_by", "manuell") if isinstance(d, dict) else "manuell",
    } for b, d in mapping.items()]
    savesheet(pd.DataFrame(zeilen), "name_mapping")
    st.session_state.name_mapping_cache = mapping.copy()
    loadsheet.clear()


def mapping_hinzufuegen(buchung_name: str, checkin_name: str, confidence=100):
    m = mapping_laden()
    m[buchung_name] = {
        "checkin_name": checkin_name,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat(),
        "confirmed_by": "manuell",
    }
    mapping_speichern(m)


def mapping_entfernen(buchung_name: str):
    m = mapping_laden()
    m.pop(buchung_name, None)
    mapping_speichern(m)


@st.cache_data(ttl=120, show_spinner=False)
def rejected_matches_laden() -> set:
    df = loadsheet("rejected_matches")
    if not df.empty and {"buchung_name", "checkin_name"} <= set(df.columns):
        return {(str(a), str(b)) for a, b in
                df[["buchung_name", "checkin_name"]].values}
    return set()


def rejected_speichern(buchung_name: str, checkin_name: str):
    df = loadsheet("rejected_matches", SHEET_SPALTEN["rejected_matches"])
    neu = pd.DataFrame([{"buchung_name": buchung_name,
                         "checkin_name": checkin_name,
                         "timestamp": datetime.now().isoformat()}])
    savesheet(pd.concat([df, neu], ignore_index=True), "rejected_matches")
    rejected_matches_laden.clear()
    loadsheet.clear()


def rejected_entfernen(buchung_name: str, checkin_name: str):
    df = loadsheet("rejected_matches", SHEET_SPALTEN["rejected_matches"])
    if not df.empty:
        df = df[~((df["buchung_name"].astype(str) == buchung_name) &
                  (df["checkin_name"].astype(str) == checkin_name))]
        savesheet(df, "rejected_matches")
        rejected_matches_laden.clear()
        loadsheet.clear()


def _initialen(name: str) -> str:
    return "".join(p[0].lower() for p in name.split() if p)


def _initialen_passen(a: str, b: str) -> bool:
    ia, ib = _initialen(a), _initialen(b)
    if not ia or not ib:
        return False
    return ia == ib or ia in ib or ib in ia


def _lautschrift(name: str) -> str:
    """Vokale weg + ähnliche Laute vereinheitlichen (Meier/Mayer/Maier)."""
    if not name:
        return ""
    out = name[0].lower()
    for ch in name[1:].lower():
        if ch not in "aeiou":
            out += ch
    for alt, neu in (("ph", "f"), ("th", "t"), ("dt", "t"),
                     ("z", "s"), ("c", "k"), ("v", "f"), ("w", "f")):
        out = out.replace(alt, neu)
    return out


def fuzzy_match(suchname: str, kandidaten: list, mapping: dict,
                abgelehnt: set, schon_vergeben: set = None) -> list:
    """Findet den wahrscheinlichsten Check-in-Namen. → [(name, score, quelle), …]"""
    if not kandidaten:
        return []
    schon_vergeben = schon_vergeben or set()
    frei = [k for k in kandidaten if k not in schon_vergeben]
    if not frei:
        return []

    if suchname in mapping:
        gelernt = mapping[suchname]
        gname = gelernt["checkin_name"] if isinstance(gelernt, dict) else gelernt
        if gname in frei:
            return [(gname, 100, "gelernt")]

    treffer = []
    for kand in frei:
        if (suchname, kand) in abgelehnt:
            continue
        token = fuzz.token_set_ratio(suchname, kand)
        partial = fuzz.partial_ratio(suchname, kand)
        laut = fuzz.ratio(_lautschrift(suchname), _lautschrift(kand))
        bonus = 20 if _initialen_passen(suchname, kand) else 0
        score = token * 0.5 + partial * 0.2 + laut * 0.2 + bonus
        if score > 50:
            treffer.append((kand, round(score, 1), "automatisch"))
    return sorted(treffer, key=lambda x: x[1], reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
#   📊  ANALYTICS-ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _rohdaten_aufbereitet() -> pd.DataFrame:
    """Playtomic-Rohdaten einmal aufbereiten — Basis aller Umsatzrechnungen."""
    raw = loadsheet("playtomic_raw")
    if raw.empty or "Service date" not in raw.columns:
        return pd.DataFrame()

    df = raw.copy()
    df["_dt"] = df["Service date"].map(parse_datetime_safe)
    df = df[df["_dt"].notna()].copy()
    if df.empty:
        return df

    df["_datum"] = df["_dt"].map(lambda d: d.date())
    df["_stunde"] = df["_dt"].map(lambda d: d.hour)
    df["_wochentag"] = df["_dt"].map(lambda d: d.weekday())
    df["_betrag"] = df["Total"].map(parse_betrag)
    df["_name_norm"] = (df["User name"].map(normalize_name)
                        if "User name" in df.columns else "")
    df["_team"] = df["_name_norm"].isin(TEAM_NORM)

    df["_wallet"] = (df["Payment method"].astype(str).str.lower()
                     .str.contains("wallet", na=False)
                     if "Payment method" in df.columns else False)

    if "Product SKU" in df.columns:
        sku = df["Product SKU"].astype(str)
        df["_buchung"] = sku.str.contains("User booking|Open match", case=False, na=False)
        df["_baelle"] = sku.str.contains("BALLS", case=False, na=False)
        df["_schlaeger"] = sku.str.contains("RACKET", case=False, na=False)
    else:
        df["_buchung"] = True
        df["_baelle"] = False
        df["_schlaeger"] = False

    return df


def _zeitraum_filter(df: pd.DataFrame, datum_str=None, von=None, bis=None):
    if df.empty:
        return df
    if datum_str:
        ziel = datetime.strptime(datum_str, "%Y-%m-%d").date()
        return df[df["_datum"] == ziel]
    if von and bis:
        return df[(df["_datum"] >= von) & (df["_datum"] <= bis)]
    return df


def verguetete_checkins(von: date = None, bis: date = None) -> int:
    """
    Wie viele Check-ins vergütet EGYM in diesem Zeitraum?

    Pro Person und Tag zählt nur einer — ein zweiter Check-in am
    selben Tag bringt keine zusätzliche Vergütung.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return 0
    df = c.copy()
    df["_d"] = df["analysis_date"].map(parse_date_safe)
    df = df[df["_d"].notna()]
    if von is not None:
        df = df[df["_d"] >= von]
    if bis is not None:
        df = df[df["_d"] <= bis]
    if df.empty:
        return 0
    return int(df.groupby("_d")["Name_norm"].nunique().sum())


def _kennzahlen(df: pd.DataFrame) -> dict:
    """Kernkennzahlen aus einem gefilterten Rohdaten-Ausschnitt."""
    k = {
        "umsatz": 0.0, "online": 0.0, "guthaben": 0.0,
        "baelle": 0.0, "schlaeger": 0.0, "sonstige": 0.0,
        "wellpass_anzahl": 0, "wellpass_wert": 0.0,
        "buchungen": 0, "team_buchungen": 0,
        "gesamt_effektiv": 0.0, "spieler": 0,
    }
    if df.empty:
        return k

    k["umsatz"] = float(df["_betrag"].sum())
    buchungen = df[df["_buchung"]]
    extras = df[~df["_buchung"]]

    k["buchungen"] = int(len(buchungen))
    k["spieler"] = int(buchungen["_name_norm"].nunique())
    k["online"] = float(buchungen.loc[(buchungen["_betrag"] > 0) &
                                      (~buchungen["_wallet"]), "_betrag"].sum())
    k["guthaben"] = float(buchungen.loc[buchungen["_wallet"], "_betrag"].sum())

    # Wellpass-Vergütung kommt aus den EGYM-Check-ins, nicht aus
    # 0-€-Zeilen — sonst weichen Umsatz und Monatsabgleich voneinander ab.
    k["wellpass_anzahl"] = verguetete_checkins(
        df["_datum"].min(), df["_datum"].max())
    k["wellpass_wert"] = round(k["wellpass_anzahl"] * WELLPASS_WERT, 2)
    k["team_buchungen"] = int(len(buchungen[(buchungen["_betrag"] == 0) &
                                            (buchungen["_team"])]))

    if not extras.empty:
        k["baelle"] = float(extras.loc[extras["_baelle"], "_betrag"].sum())
        k["schlaeger"] = float(extras.loc[extras["_schlaeger"], "_betrag"].sum())
        k["sonstige"] = float(extras.loc[~(extras["_baelle"] | extras["_schlaeger"]),
                                         "_betrag"].sum())

    k["gesamt_effektiv"] = round(k["umsatz"] + k["wellpass_wert"], 2)
    return k


@st.cache_data(ttl=900, show_spinner=False)
def tages_kennzahlen(datum_str: str) -> dict:
    return _kennzahlen(_zeitraum_filter(_rohdaten_aufbereitet(), datum_str=datum_str))


@st.cache_data(ttl=900, show_spinner=False)
def monats_kennzahlen(monat: str) -> dict:
    """monat = 'YYYY-MM'"""
    jahr, mon = int(monat[:4]), int(monat[5:7])
    von, bis = date(jahr, mon, 1), date(jahr, mon, monthrange(jahr, mon)[1])
    return _kennzahlen(_zeitraum_filter(_rohdaten_aufbereitet(), von=von, bis=bis))


@st.cache_data(ttl=900, show_spinner=False)
def verfuegbare_tage() -> list:
    df = loadsheet("buchungen")
    if df.empty or "analysis_date" not in df.columns:
        return []
    return sorted(df["analysis_date"].dropna().astype(str).unique(), reverse=True)


@st.cache_data(ttl=900, show_spinner=False)
def auslastung_matrix(monat: str = None) -> pd.DataFrame:
    """
    Heatmap-Daten: Wie viele Buchungen pro Wochentag × Stunde.
    Zeigt sofort, wann die Halle voll ist und wann tote Zeit herrscht.
    """
    df = _rohdaten_aufbereitet()
    if df.empty:
        return pd.DataFrame()

    if monat:
        jahr, mon = int(monat[:4]), int(monat[5:7])
        von, bis = date(jahr, mon, 1), date(jahr, mon, monthrange(jahr, mon)[1])
        df = _zeitraum_filter(df, von=von, bis=bis)

    df = df[df["_buchung"]]
    if df.empty:
        return pd.DataFrame()

    matrix = (df.groupby(["_wochentag", "_stunde"])
              .size().reset_index(name="anzahl"))
    return matrix


@st.cache_data(ttl=900, show_spinner=False)
def spieler_statistik() -> pd.DataFrame:
    """Pro Spieler: Buchungen, Umsatz, Vergessen, erster/letzter Besuch."""
    b = loadsheet("buchungen")
    if b.empty or "Name" not in b.columns:
        return pd.DataFrame()

    df = b.copy()
    df["_betrag"] = df["Betrag"].map(parse_betrag) if "Betrag" in df.columns else 0.0
    df["_datum"] = df["analysis_date"].astype(str)
    df["_fehler"] = df["Fehler"].astype(str) == "Ja" if "Fehler" in df.columns else False
    df["_checkin"] = df["Check-in"].astype(str) == "Ja" if "Check-in" in df.columns else False
    df["_relevant"] = df["Relevant"].astype(str) == "Ja" if "Relevant" in df.columns else False

    stat = df.groupby("Name").agg(
        buchungen=("Name", "count"),
        umsatz=("_betrag", "sum"),
        vergessen=("_fehler", "sum"),
        wellpass_pflichtig=("_relevant", "sum"),
        checkins=("_checkin", "sum"),
        erster_besuch=("_datum", "min"),
        letzter_besuch=("_datum", "max"),
    ).reset_index()

    stat["team"] = stat["Name"].map(lambda n: normalize_name(n) in TEAM_NORM)
    stat["tage_her"] = stat["letzter_besuch"].map(
        lambda d: (date.today() - datetime.strptime(str(d), "%Y-%m-%d").date()).days
        if re.match(r"\d{4}-\d{2}-\d{2}", str(d)) else 999
    )
    stat["treue_quote"] = stat.apply(
        lambda r: prozent(r["checkins"], r["wellpass_pflichtig"])
        if r["wellpass_pflichtig"] else 100.0, axis=1
    )
    return stat.sort_values("buchungen", ascending=False)


def tag_details(datum_str: str) -> pd.DataFrame:
    df = loadsheet("buchungen")
    if df.empty or "analysis_date" not in df.columns:
        return pd.DataFrame()
    return df[df["analysis_date"].astype(str) == str(datum_str)].copy()


def behobene_keys() -> set:
    corr = loadsheet("corrections", SHEET_SPALTEN["corrections"])
    if corr.empty or "key" not in corr.columns:
        return set()
    return set(corr.loc[corr["behoben"].map(is_true), "key"].astype(str))


def offene_fehler(datum_str: str) -> pd.DataFrame:
    """Spieler die spielen waren, aber keinen Wellpass-Check-in haben."""
    tag = tag_details(datum_str)
    if tag.empty or "Fehler" not in tag.columns:
        return pd.DataFrame()

    fehler = tag[tag["Fehler"].astype(str) == "Ja"].copy()
    if fehler.empty:
        return fehler

    erledigt = behobene_keys()
    if erledigt:
        fehler["_key"] = (fehler["Name_norm"].astype(str) + "_"
                          + fehler["Datum"].astype(str))
        fehler = fehler[~fehler["_key"].isin(erledigt)]
    return fehler


def alle_offenen_fehler(tage: list) -> pd.DataFrame:
    """Offene Fehler über mehrere Tage in einer Tabelle."""
    teile = [offene_fehler(t) for t in tage]
    teile = [t for t in teile if not t.empty]
    if not teile:
        return pd.DataFrame()
    return pd.concat(teile, ignore_index=True)


def als_behoben_markieren(name_norm: str, datum: str):
    corr = loadsheet("corrections", SHEET_SPALTEN["corrections"])
    key = f"{name_norm}_{datum}"
    if not corr.empty and "key" in corr.columns:
        corr = corr[corr["key"].astype(str) != key]
    neu = pd.DataFrame([{"key": key, "date": datum, "behoben": True,
                         "timestamp": datetime.now().isoformat()}])
    savesheet(pd.concat([corr, neu], ignore_index=True), "corrections")
    loadsheet.clear()


def checkin_bewertung(checkins_tag: pd.DataFrame) -> dict:
    """
    Wertet die Check-ins eines Tages aus.

    EGYM vergütet pro Person und Tag nur einmal. Checkt jemand
    zweimal ein, ist der zweite Check-in für dich wertlos.

    → {"verguetet": n, "doppelt": n, "namen": {name_norm: anzahl}}
    """
    if checkins_tag.empty or "Name_norm" not in checkins_tag.columns:
        return {"verguetet": 0, "doppelt": 0, "namen": {}}
    zaehl = checkins_tag["Name_norm"].astype(str).value_counts().to_dict()
    verguetet = len(zaehl)
    doppelt = int(sum(v - 1 for v in zaehl.values()))
    return {"verguetet": verguetet, "doppelt": doppelt, "namen": zaehl}


def offene_checkins(datum_str: str) -> pd.DataFrame:
    """
    Check-ins, die keiner Buchung zugeordnet werden konnten.

    Das sind die Kandidaten für eine Namenszuordnung: derselbe
    Mensch, aber bei EGYM anders geschrieben als in Playtomic.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns:
        return pd.DataFrame()
    tag = c[c["analysis_date"].astype(str) == str(datum_str)]
    if tag.empty or "Gespielt" not in tag.columns:
        return pd.DataFrame()
    offen = tag[tag["Gespielt"].astype(str) == "Nein"].copy()
    if offen.empty:
        return offen
    # Doppelte Namen nur einmal anbieten
    return offen.drop_duplicates(subset=["Name_norm"])


def zuordnung_vorschlag(name: str, datum_str: str) -> list:
    """
    Passende offene Check-ins zu einem gemeldeten Vergesser finden.
    → [(anzeigename, name_norm, score), …] absteigend sortiert
    """
    offen = offene_checkins(datum_str)
    if offen.empty:
        return []
    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()
    kandidaten = offen["Name_norm"].astype(str).tolist()
    anzeige = dict(zip(offen["Name_norm"].astype(str),
                       offen["Name"].astype(str)))
    treffer = fuzzy_match(normalize_name(name), kandidaten, mapping, abgelehnt)
    return [(anzeige.get(k, k), k, score) for k, score, _ in treffer]


def checkins_ohne_buchung(datum_str: str) -> pd.DataFrame:
    """
    Wer hat eingecheckt, ohne dass eine Buchung vorliegt?
    Deutet auf Datenlücke hin — oder auf jemanden der nur eingecheckt hat.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns:
        return pd.DataFrame()
    tag = c[c["analysis_date"].astype(str) == str(datum_str)]
    if tag.empty or "Gespielt" not in tag.columns:
        return pd.DataFrame()
    return tag[tag["Gespielt"].astype(str) == "Nein"].copy()


def sauber_serie(tage: list) -> int:
    """Wie viele Tage in Folge (ab heute rückwärts) ohne offenen Fehler?"""
    serie = 0
    for t in tage:
        if offene_fehler(t).empty:
            serie += 1
        else:
            break
    return serie


def prognose_monat(monat: str) -> dict:
    """Hochrechnung Monatsende auf Basis des bisherigen Schnitts."""
    jahr, mon = int(monat[:4]), int(monat[5:7])
    tage_im_monat = monthrange(jahr, mon)[1]

    k = monats_kennzahlen(monat)
    tage = [t for t in verfuegbare_tage() if t.startswith(monat)]

    heute = date.today()
    if (jahr, mon) == (heute.year, heute.month):
        vergangen = heute.day
    else:
        vergangen = tage_im_monat

    tage_mit_daten = len(tage) or 1
    schnitt = k["gesamt_effektiv"] / tage_mit_daten

    return {
        "ist": k["gesamt_effektiv"],
        "schnitt_pro_tag": round(schnitt, 2),
        "prognose": round(schnitt * tage_im_monat, 2),
        "tage_erfasst": tage_mit_daten,
        "tage_gesamt": tage_im_monat,
        "vergangen": vergangen,
        "ziel": monatsziel(monat),
    }


def winback_liste(mindest_buchungen: int = 3, tage_weg: int = 21) -> pd.DataFrame:
    """
    Spieler die regelmässig da waren und jetzt länger nicht mehr.
    Die beste Liste für eine kurze „Wir vermissen dich"-Nachricht.
    """
    stat = spieler_statistik()
    if stat.empty:
        return pd.DataFrame()
    weg = stat[(~stat["team"]) &
               (stat["buchungen"] >= mindest_buchungen) &
               (stat["tage_her"] >= tage_weg) &
               (stat["tage_her"] < 900)]
    return weg.sort_values(["buchungen", "tage_her"], ascending=[False, True])


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#   🎨  DESIGN-SYSTEM  —  Look der Website padelcircle.de
# ══════════════════════════════════════════════════════════════════════════════

def css_laden():
    st.markdown(f"""<style>
 @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
 :root {{
  --ink0:{C['ink0']}; --ink1:{C['ink1']}; --ink2:{C['ink2']}; --ink3:{C['ink3']};
  --volt:{C['volt']}; --blue:{C['blue']};
  --text:{C['text']}; --dim:{C['dim']}; --faint:{C['faint']};
  --line:{C['line']}; --line-str:{C['line_str']};
  --r:{C['r']}; --r-lg:{C['r_lg']}; --r-sm:{C['r_sm']};
 }}
 @keyframes pcUp   {{ from{{opacity:0;transform:translateY(12px)}} to{{opacity:1;transform:none}} }}
 @keyframes pcPop  {{ 0%{{opacity:0;transform:scale(.94)}} 60%{{transform:scale(1.02)}} 100%{{opacity:1;transform:scale(1)}} }}
 @keyframes pcPulse{{ 0%,100%{{box-shadow:0 0 0 0 {C['volt_glow']}}} 50%{{box-shadow:0 0 0 9px rgba(223,255,0,0)}} }}
 @keyframes pcSweep{{ 0%{{background-position:-200% 0}} 100%{{background-position:200% 0}} }}
 @keyframes pcRing {{ from{{stroke-dashoffset:314}} }}
 @keyframes pcFloat{{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-5px)}} }}
 /* ═══ GRUNDLAGE ═══ */
 html, body, .stApp, [data-testid="stAppViewContainer"],
 [data-testid="stHeader"], .main, .block-container {{
  background: var(--ink0) !important;
  color: var(--text) !important;
  font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif !important;
 }}
 .block-container {{ padding-top:2.2rem; padding-bottom:3rem; max-width:1240px; }}
 #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display:none !important; }}
 /* Schriftart nur auf Text-Elemente, niemals pauschal auf span/div —
    sonst werden Icon-Ligaturen zerstört. */
 h1,h2,h3,h4,h5,h6, p, li, td, th, label,
 .stMarkdown, [data-testid="stMarkdownContainer"],
 .pc-head, .pc-kpi, .pc-card, .pc-box, .pc-tile, .pc-row,
 .pc-login, .pc-claim, .pc-chip, .pc-streak, .pc-ring-wrap {{
  font-family:'Montserrat',sans-serif;
  letter-spacing:-.005em;
 }}
 h1,h2,h3,h4,h5,h6, p, li, td, th {{ color: var(--text); }}
 .stMarkdown p, .stMarkdown li, .stMarkdown span {{ color: var(--text); }}
 /* ═══ ICON-SCHRIFTEN ═══
    Streamlit rendert Icons als <span> mit Ligatur-Schrift. Wird deren
    font-family überschrieben, erscheint der Ligatur-Name als Text
    ("uploadUpload"). Diese Regeln schützen davor. */
 [data-testid="stIconMaterial"], [data-testid="stExpanderToggleIcon"],
 [data-testid="stFileUploaderIcon"], [data-testid="stBaseButton-header"] span,
 .material-icons, .material-icons-outlined, .material-icons-round,
 .material-symbols-outlined, .material-symbols-rounded,
 [class*="material-symbols"], [class*="material-icons"],
 span[class*="st-emotion-cache"][data-testid*="Icon"],
 [data-testid="stIconMaterial"]::before {{
  font-family:'Material Symbols Rounded','Material Symbols Outlined',
              'Material Icons' !important;
  letter-spacing:normal !important;
  font-weight:normal !important;
  text-transform:none !important;
  line-height:1 !important;
 }}
 /* Doppelte Beschriftung im Datei-Upload unterbinden */
 [data-testid="stFileUploader"] [data-testid="stIconMaterial"] {{
  font-size:1.4rem !important;
 }}
 .stMarkdown p, .stMarkdown li {{ color: var(--text); line-height:1.6; }}
 [data-testid="stCaptionContainer"], .stCaption, small {{ color: var(--dim) !important; }}
 hr {{ border-color: var(--line) !important; }}
 a {{ color: var(--volt) !important; }}
 /* ═══ LOGIN ═══ */
 .pc-login {{ text-align:center; margin:3rem 0 1.4rem; animation:pcUp .55s ease both; }}
 .pc-login .mark {{
  width:132px; height:auto; color:var(--volt);
  animation:pcFloat 4s ease-in-out infinite;
 }}
 .pc-login h1 {{
  margin:1.3rem 0 .2rem; font-size:2.1rem; font-weight:800;
  letter-spacing:.16em; color:var(--text);
 }}
 .pc-login .sub {{
  color:var(--dim); font-size:.8rem; letter-spacing:.22em;
  text-transform:uppercase; font-weight:500;
 }}
 .pc-claim {{
  text-align:center; margin:2.6rem 0 1rem; font-size:10px;
  letter-spacing:.42em; color:var(--faint); font-weight:600;
 }}
 /* ═══ HEADER ═══ */
 .pc-head {{
  background:linear-gradient(135deg,var(--ink1) 0%,var(--ink2) 100%);
  border:1px solid var(--line); border-radius:var(--r-lg);
  padding:1.5rem 1.8rem; margin-bottom:1.4rem;
  position:relative; overflow:hidden; animation:pcUp .45s ease both;
 }}
 .pc-head::after {{
  content:''; position:absolute; left:0; right:0; bottom:0; height:2px;
  background:linear-gradient(90deg,var(--volt),rgba(223,255,0,.1),var(--volt));
  background-size:200% 100%; animation:pcSweep 6s linear infinite;
 }}
 .pc-head .row {{ display:flex; align-items:center; gap:14px; }}
 .pc-head .mark {{ width:46px; height:auto; color:var(--volt); flex-shrink:0; }}
 .pc-head h1 {{ margin:0; font-size:1.5rem; font-weight:700; letter-spacing:-.01em; }}
 .pc-head .sub {{
  color:var(--volt); font-size:.68rem; letter-spacing:.2em;
  margin-top:.3rem; text-transform:uppercase; font-weight:600;
 }}
 /* ═══ KENNZAHLEN ═══ */
 .pc-kpi {{
  background:var(--ink1); border:1px solid var(--line);
  border-radius:var(--r); padding:1rem 1.15rem; height:100%;
  transition:border-color .18s ease, transform .18s ease;
  animation:pcPop .45s ease both;
 }}
 .pc-kpi:hover {{ border-color:var(--line-str); transform:translateY(-2px); }}
 .pc-kpi .l {{
  color:var(--dim); font-size:.66rem; text-transform:uppercase;
  letter-spacing:.13em; font-weight:600;
 }}
 .pc-kpi .v {{
  color:var(--text); font-size:1.6rem; font-weight:700;
  margin-top:.35rem; line-height:1.1; letter-spacing:-.02em;
 }}
 .pc-kpi .h {{ color:var(--faint); font-size:.73rem; margin-top:.3rem; }}
 .pc-kpi .d {{ font-size:.73rem; margin-top:.3rem; font-weight:700; }}
 .pc-kpi .d.up   {{ color:{C['ok']}; }}
 .pc-kpi .d.down {{ color:{C['err']}; }}
 /* ═══ KARTEN ═══ */
 .pc-card {{
  background:var(--ink1); border:1px solid var(--line);
  border-radius:var(--r); padding:1rem 1.2rem; margin-bottom:.7rem;
  animation:pcUp .4s ease both;
 }}
 /* ═══ HINWEISE ═══ */
 .pc-box {{
  border-radius:var(--r); padding:.9rem 1.15rem; margin:.6rem 0;
  font-size:.87rem; line-height:1.62; border:1px solid;
  animation:pcUp .4s ease both;
 }}
 .pc-box.info {{ background:rgba(46,91,201,.10); border-color:rgba(46,91,201,.4); color:#CBD9F5; }}
 .pc-box.ok   {{ background:rgba(74,222,128,.09); border-color:rgba(74,222,128,.35); color:#B4F5CD; }}
 .pc-box.warn {{ background:rgba(251,191,36,.09); border-color:rgba(251,191,36,.35); color:#FCE7A8; }}
 .pc-box.err  {{ background:rgba(255,90,90,.09);  border-color:rgba(255,90,90,.35);  color:#FFC9C9; }}
 .pc-box b {{ color:var(--volt); }}
 /* ═══ MODUL-KACHELN ═══ */
 .pc-tile {{
  background:linear-gradient(150deg,var(--ink1) 0%,var(--ink2) 100%);
  border:1px solid var(--line); border-radius:var(--r-lg);
  padding:1.15rem 1.25rem 1.3rem; min-height:142px; position:relative;
  transition:border-color .2s ease, transform .2s ease, box-shadow .2s ease;
  animation:pcPop .5s ease both;
 }}
 .pc-tile:hover {{
  border-color:var(--volt); transform:translateY(-4px);
  box-shadow:0 14px 34px rgba(0,0,0,.5);
 }}
 .pc-tile.soon {{ border-style:dashed; opacity:.42; }}
 .pc-tile.soon:hover {{ transform:none; box-shadow:none; border-color:var(--line); }}
 .pc-tile .ic {{ font-size:1.5rem; }}
 .pc-tile .ti {{ color:var(--text); font-size:1rem; font-weight:700; margin-top:.65rem; }}
 .pc-tile .de {{ color:var(--dim); font-size:.78rem; margin-top:.28rem; line-height:1.5; }}
 .pc-tile .bg {{
  position:absolute; top:1rem; right:1.1rem; background:var(--volt);
  color:#0A0A0A; font-size:.62rem; font-weight:800; padding:.2rem .6rem;
  border-radius:999px; letter-spacing:.06em; text-transform:uppercase;
 }}
 .pc-tile .bg.alert {{ animation:pcPulse 2.2s ease-in-out infinite; }}
 .pc-tile .bg.muted {{ background:rgba(255,255,255,.1); color:var(--dim); }}
 /* ═══ RING ═══ */
 .pc-ring-wrap {{
  display:flex; align-items:center; gap:1.3rem; background:var(--ink1);
  border:1px solid var(--line); border-radius:var(--r);
  padding:1.15rem 1.35rem; animation:pcUp .45s ease both;
 }}
 .pc-ring circle.bar {{ animation:pcRing 1.2s cubic-bezier(.2,.8,.3,1) both; }}
 /* ═══ SERIE ═══ */
 .pc-streak {{
  background:linear-gradient(105deg,var(--blue) 0%,#0A2A6B 100%);
  border:1px solid rgba(46,91,201,.5); border-radius:var(--r);
  padding:1.05rem 1.35rem; display:flex; align-items:center;
  justify-content:space-between; animation:pcUp .45s ease both;
 }}
 .pc-streak .t {{ font-size:.66rem; color:rgba(255,255,255,.65);
         letter-spacing:.18em; text-transform:uppercase; font-weight:600; }}
 .pc-streak .n {{ font-size:2.2rem; font-weight:800; color:var(--volt); line-height:1; }}
 /* ═══ ZEILEN ═══ */
 .pc-row {{
  background:var(--ink1); border:1px solid var(--line); border-radius:var(--r-sm);
  padding:.72rem 1rem; margin-bottom:.4rem; display:flex;
  align-items:center; justify-content:space-between;
  transition:border-color .16s ease;
 }}
 .pc-row:hover {{ border-color:var(--line-str); }}
 .pc-row .nm {{ font-weight:600; color:var(--text); }}
 .pc-row .mt {{ color:var(--dim); font-size:.8rem; }}
 .pc-medal {{ font-size:1.05rem; margin-right:.4rem; }}
 .pc-fall {{ display:flex; justify-content:space-between; align-items:baseline; }}
 .pc-fall .nm {{ font-weight:600; color:var(--text); font-size:1rem; }}
 .pc-fall .mt {{ color:var(--dim); font-size:.84rem; }}
 .pc-fall .ts {{ color:var(--dim); font-size:.76rem; }}
 .pc-vorschlag {{
  background:rgba(223,255,0,.07); border:1px solid rgba(223,255,0,.3);
  border-radius:var(--r-sm); padding:.65rem .95rem; margin:.35rem 0 .5rem;
  font-size:.86rem; color:var(--text);
 }}
 .pc-vorschlag b {{ color:var(--volt); }}
 .pc-chip {{
  display:inline-block; padding:.16rem .6rem; border-radius:999px;
  font-size:.67rem; font-weight:700; letter-spacing:.03em;
 }}
 .pc-chip.lime {{ background:var(--volt); color:#0A0A0A; }}
 .pc-chip.soft {{ background:rgba(255,255,255,.08); color:var(--dim); }}
 .pc-chip.warn {{ background:rgba(251,191,36,.2); color:{C['warn']}; }}
 .pc-chip.err  {{ background:rgba(255,90,90,.2); color:{C['err']}; }}
 /* ═══ BUTTONS ═══ */
 div.stButton > button, div.stDownloadButton > button {{
  border-radius:999px !important; font-weight:600 !important;
  font-size:.85rem !important; padding:.5rem 1.15rem !important;
  background:transparent !important; color:var(--text) !important;
  border:1px solid var(--line-str) !important;
  transition:all .16s ease !important;
 }}
 div.stButton > button:hover, div.stDownloadButton > button:hover {{
  border-color:var(--volt) !important; color:var(--volt) !important;
  background:rgba(223,255,0,.06) !important;
 }}
 div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {{
  background:var(--volt) !important; color:#0A0A0A !important;
  border-color:var(--volt) !important; font-weight:700 !important;
 }}
 div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover {{
  background:#EFFF4D !important; color:#0A0A0A !important;
 }}
 div.stButton > button:disabled {{
  opacity:.32 !important; color:var(--faint) !important;
  border-color:var(--line) !important; background:transparent !important;
 }}
 div.stButton > button:active {{ transform:scale(.98); }}
 /* ═══ EINGABEFELDER ═══ */
 .stTextInput input, .stNumberInput input, .stTextArea textarea,
 .stDateInput input, .stTimeInput input {{
  background:var(--ink3) !important; color:var(--text) !important;
  border:1px solid var(--line-str) !important; border-radius:var(--r-sm) !important;
  font-family:'Montserrat',sans-serif !important;
 }}
 .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
  border-color:var(--volt) !important; box-shadow:0 0 0 2px rgba(223,255,0,.14) !important;
 }}
 .stTextInput input::placeholder, .stTextArea textarea::placeholder {{ color:var(--faint) !important; }}
 [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p {{
  color:var(--dim) !important; font-size:.78rem !important;
  font-weight:600 !important; letter-spacing:.02em;
 }}
 [data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {{
  background:var(--ink3) !important; color:var(--text) !important;
  border-color:var(--line-str) !important;
 }}
 [data-testid="stNumberInputStepUp"]:hover, [data-testid="stNumberInputStepDown"]:hover {{
  background:var(--volt) !important; color:#0A0A0A !important;
 }}
 /* Auswahlfelder */
 .stSelectbox div[data-baseweb="select"] > div,
 .stMultiSelect div[data-baseweb="select"] > div {{
  background:var(--ink3) !important; border-color:var(--line-str) !important;
  border-radius:var(--r-sm) !important; color:var(--text) !important;
 }}
 div[data-baseweb="popover"] li, div[data-baseweb="menu"] li {{
  background:var(--ink2) !important; color:var(--text) !important;
 }}
 div[data-baseweb="popover"] li:hover, div[data-baseweb="menu"] li:hover {{
  background:var(--ink3) !important; color:var(--volt) !important;
 }}
 div[data-baseweb="popover"] > div {{ background:var(--ink2) !important; }}
 /* Radio + Checkbox */
 .stRadio label, .stCheckbox label {{ color:var(--text) !important; }}
 .stRadio [role="radiogroup"] label span {{ color:var(--text) !important; }}
 /* Schieberegler */
 .stSlider [data-baseweb="slider"] div[role="slider"] {{ background:var(--volt) !important; }}
 .stSlider [data-testid="stTickBar"] {{ color:var(--faint) !important; }}
 .stSlider [data-baseweb="slider"] > div > div {{ background:var(--volt) !important; }}
 /* Datei-Upload */
 [data-testid="stFileUploader"] section {{
  background:var(--ink1) !important; border:1.5px dashed var(--line-str) !important;
  border-radius:var(--r) !important;
 }}
 [data-testid="stFileUploader"] section:hover {{ border-color:var(--volt) !important; }}
 [data-testid="stFileUploader"] section small,
 [data-testid="stFileUploader"] section span {{ color:var(--dim) !important; }}
 [data-testid="stFileUploader"] button {{
  background:transparent !important; color:var(--text) !important;
  border:1px solid var(--line-str) !important; border-radius:999px !important;
 }}
 [data-testid="stFileUploaderFile"] {{ background:var(--ink2) !important; }}
 /* ═══ TABS ═══ */
 .stTabs [data-baseweb="tab-list"] {{
  gap:.3rem; border-bottom:1px solid var(--line);
  background:transparent;
 }}
 .stTabs [data-baseweb="tab"] {{
  border-radius:var(--r-sm) var(--r-sm) 0 0; padding:.5rem 1.1rem;
  color:var(--dim) !important; font-weight:600; font-size:.85rem;
  background:transparent;
 }}
 .stTabs [data-baseweb="tab"]:hover {{ color:var(--text) !important; }}
 .stTabs [aria-selected="true"] {{
  background:var(--ink2) !important; color:var(--volt) !important;
 }}
 .stTabs [data-baseweb="tab-highlight"] {{ background:var(--volt) !important; }}
 .stTabs [data-baseweb="tab-border"] {{ background:var(--line) !important; }}
 /* ═══ AUSKLAPPER ═══ */
 [data-testid="stExpander"] {{
  background:var(--ink1) !important; border:1px solid var(--line) !important;
  border-radius:var(--r) !important;
 }}
 [data-testid="stExpander"] summary {{ color:var(--text) !important; font-weight:600; }}
 [data-testid="stExpander"] summary:hover {{ color:var(--volt) !important; }}
 [data-testid="stExpander"] svg {{ fill:var(--dim) !important; }}
 /* ═══ TABELLEN ═══ */
 [data-testid="stDataFrame"], [data-testid="stTable"] {{
  background:var(--ink1) !important; border:1px solid var(--line) !important;
  border-radius:var(--r) !important;
 }}
 [data-testid="stDataFrame"] * {{ color:var(--text) !important; }}
 /* ═══ CODE ═══ */
 .stCode, pre, code {{
  background:var(--ink2) !important; color:var(--text) !important;
  border:1px solid var(--line) !important; border-radius:var(--r-sm) !important;
 }}
 .stCode pre {{ border:none !important; }}
 /* ═══ SEITENLEISTE ═══ */
 section[data-testid="stSidebar"] {{
  background:var(--ink1) !important; border-right:1px solid var(--line);
 }}
 section[data-testid="stSidebar"] * {{ color:var(--text); }}
 section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color:var(--faint) !important; }}
 section[data-testid="stSidebar"] div.stButton > button {{
  text-align:left !important; justify-content:flex-start !important;
  border-radius:var(--r-sm) !important; border-color:transparent !important;
  font-weight:500 !important;
 }}
 section[data-testid="stSidebar"] div.stButton > button:hover {{
  background:var(--ink3) !important; border-color:var(--line-str) !important;
 }}
 /* ═══ MELDUNGEN ═══ */
 [data-testid="stAlert"] {{ border-radius:var(--r) !important; }}
 .stSuccess {{ background:rgba(74,222,128,.11) !important; color:#B4F5CD !important; }}
 .stError   {{ background:rgba(255,90,90,.11) !important;  color:#FFC9C9 !important; }}
 .stWarning {{ background:rgba(251,191,36,.11) !important; color:#FCE7A8 !important; }}
 .stInfo    {{ background:rgba(46,91,201,.11) !important;  color:#CBD9F5 !important; }}
 /* ═══ FORTSCHRITT & SPINNER ═══ */
 .stProgress > div > div > div > div {{ background:var(--volt) !important; }}
 .stSpinner > div {{ border-top-color:var(--volt) !important; }}
 /* ═══ DIAGRAMME ═══ */
 .js-plotly-plot .plotly {{ background:transparent !important; }}
</style>
""", unsafe_allow_html=True)


def head(titel: str, unter: str = ""):
    st.markdown(f"""
    <div class="pc-head">
      <div class="row">
        <div class="mark">{LOGO_SVG}</div>
        <div>
          <h1>{titel}</h1>
          <div class="sub">{unter or CONFIG['claim']}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


def kpi(label: str, wert: str, hinweis: str = "", delta: float = None,
        delta_text: str = ""):
    d_html = ""
    if delta is not None:
        richtung = "up" if delta >= 0 else "down"
        pfeil = "▲" if delta >= 0 else "▼"
        d_html = f'<div class="d {richtung}">{pfeil} {abs(delta):.0f}% {delta_text}</div>'
    st.markdown(f"""
    <div class="pc-kpi">
      <div class="l">{label}</div>
      <div class="v">{wert}</div>
      {f'<div class="h">{hinweis}</div>' if hinweis else ''}
      {d_html}
    </div>""", unsafe_allow_html=True)


def box(text: str, art: str = "info"):
    st.markdown(f'<div class="pc-box {art}">{text}</div>', unsafe_allow_html=True)


def fortschritts_ring(prozent_wert: float, mitte_text: str,
                      titel: str, unter: str = ""):
    p = max(0.0, min(float(prozent_wert), 100.0))
    umfang = 314.0
    offset = umfang - (p / 100.0 * umfang)
    farbe = C["volt"] if p >= 100 else (C["blue_soft"] if p >= 60 else C["warn"])
    st.markdown(f"""
    <div class="pc-ring-wrap">
      <svg class="pc-ring" width="110" height="110" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="50" fill="none"
                stroke="{C['line_str']}" stroke-width="9"/>
        <circle class="bar" cx="60" cy="60" r="50" fill="none"
                stroke="{farbe}" stroke-width="9" stroke-linecap="round"
                stroke-dasharray="{umfang}" stroke-dashoffset="{offset}"
                transform="rotate(-90 60 60)"/>
        <text x="60" y="67" text-anchor="middle" font-size="22"
              font-weight="700" fill="{C['text']}"
              font-family="Montserrat,sans-serif">{mitte_text}</text>
      </svg>
      <div>
        <div style="font-weight:700;color:{C['text']};font-size:1.02rem;">{titel}</div>
        <div style="color:{C['dim']};font-size:.83rem;margin-top:.3rem;
                    line-height:1.55;">{unter}</div>
      </div>
    </div>""", unsafe_allow_html=True)


def streak_banner(tage: int):
    if tage <= 0:
        return
    wort = "Tag" if tage == 1 else "Tage"
    st.markdown(f"""
    <div class="pc-streak">
      <div>
        <div class="t">Saubere Serie</div>
        <div style="font-size:.92rem;margin-top:.3rem;color:#fff;">
          {tage} {wort} in Folge ohne vergessenen Check-in
        </div>
      </div>
      <div class="n">{tage}</div>
    </div>""", unsafe_allow_html=True)


def chip(text: str, art: str = "soft") -> str:
    return f'<span class="pc-chip {art}">{text}</span>'


def claim_line():
    st.markdown('<div class="pc-claim">ONCE IN &nbsp;·&nbsp; NEVER OUT</div>',
                unsafe_allow_html=True)


def offene_config() -> list:
    offen = []
    if not CONFIG["egym_gym_id"]:
        offen.append("EGYM Gym-ID")
    if not CONFIG["wellpass_qr_link"]:
        offen.append("Wellpass QR-Link")
    return offen


def plotly_layout(fig, hoehe=340, titel_y="€"):
    fig.update_layout(
        height=hoehe,
        margin=dict(l=8, r=8, t=30, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.16, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(color=C["dim"], size=11)),
        yaxis_title=titel_y,
        font=dict(color=C["dim"], size=11, family="Montserrat"),
        hoverlabel=dict(bgcolor=C["ink3"], font_color=C["text"],
                        bordercolor=C["volt"]),
    )
    fig.update_xaxes(showgrid=False, color=C["dim"], linecolor=C["line"])
    fig.update_yaxes(gridcolor=C["line"], zerolinecolor=C["line"], color=C["dim"])
    return fig

#   📦  MODUL · DATEN-ZENTRALE
# ══════════════════════════════════════════════════════════════════════════════

def _kunden_index(df: pd.DataFrame) -> dict:
    """
    Kundentabelle in ein Wörterbuch nach name_norm verwandeln.

    Doppelte Einträge werden zusammengeführt statt einen Fehler
    auszulösen — bei mehreren Zeilen zur selben Person gewinnt
    jeweils der ausgefüllte Wert.
    """
    if df.empty or "name_norm" not in df.columns:
        return {}
    out = {}
    for _, zeile in df.iterrows():
        schluessel = str(zeile.get("name_norm", "") or "").strip()
        if not schluessel or schluessel.lower() in ("nan", "none"):
            continue
        eintrag = out.setdefault(schluessel, {})
        for spalte in df.columns:
            if spalte == "name_norm":
                continue
            wert = str(zeile.get(spalte, "") or "").strip()
            if wert and wert.lower() not in ("nan", "none", "nat", "<na>"):
                eintrag[spalte] = wert
            elif spalte not in eintrag:
                eintrag[spalte] = ""
    return out


def _zahlungs_index(pdf: pd.DataFrame) -> dict:
    """
    {(name_norm, startzeit): gezahlter Betrag}
    Nur Court-Buchungen, keine Extras.
    """
    if pdf.empty or "Service date" not in pdf.columns:
        return {}
    df = pdf.copy()
    if "Product SKU" in df.columns:
        df = df[df["Product SKU"].astype(str)
                .str.contains("booking|Open match", case=False, na=False)]
    if df.empty:
        return {}
    df["_dt"] = df["Service date"].map(parse_datetime_safe)
    df["_nn"] = df["User name"].map(normalize_name)
    df["_bt"] = df["Total"].map(parse_betrag)
    df = df[df["_dt"].notna()]
    # Summieren, damit Rückerstattungen und Nachzahlungen korrekt verrechnet werden
    grp = df.groupby(["_nn", "_dt"])["_bt"].sum()
    return {k: float(v) for k, v in grp.items()}


def _wellpass_traeger(teilnehmer, start, pro_platz, n_wellpass, zahlungen) -> set:
    """
    Wer von den Teilnehmern hatte den Rabatt?

    Wer weniger als den Platzpreis gezahlt hat, war es. Bleibt genau
    eine Person ohne Zahlungszeile übrig und fehlt genau ein Rabatt,
    wird sie per Ausschluss zugeordnet. Sonst bleibt es offen und
    alle gelten als möglich.
    """
    # Team zahlt immer 0 € und ist nie Wellpass-Träger
    namen = [normalize_name(n) for n, _ in teilnehmer
             if normalize_name(n) not in TEAM_NORM]
    if n_wellpass <= 0 or not namen:
        return set()
    if not zahlungen or n_wellpass >= len(namen):
        return set(namen)

    sicher, voll, unbekannt = set(), set(), set()
    for nn in namen:
        gezahlt = zahlungen.get((nn, start))
        if gezahlt is None:
            unbekannt.add(nn)
        elif pro_platz - gezahlt > 1.0:
            sicher.add(nn)
        else:
            voll.add(nn)

    if len(sicher) == n_wellpass:
        return sicher
    # Ausschlussverfahren: genau eine offene Person, genau ein offener Rabatt
    if len(unbekannt) == 1 and len(sicher) == n_wellpass - 1:
        return sicher | unbekannt
    return set(namen)


def _verarbeiten(b_datei, c_datei, p_datei=None) -> bool:
    """
    Bookings und Wellpass-Check-ins abgleichen.
    Der Payments-Export ist optional und liefert nur die Umsatzzahlen.
    """
    bdf = parse_bookings(b_datei)
    if bdf.empty:
        return False
    cdf = parse_checkins(c_datei)
    if cdf.empty:
        st.error("❌ Check-in-Datei konnte nicht gelesen werden.")
        return False

    st.caption(f"Buchungen {len(bdf)} · Check-ins {len(cdf)}")

    # ── Zahlungen (optional: Umsatz + präzise Wellpass-Zuordnung) ──────
    neu_raw = 0
    zahlungen = {}
    if p_datei is not None:
        pdf = parse_playtomic(p_datei)
        if not pdf.empty:
            key_raw = [c for c in ("Payment id", "User name", "Service date")
                       if c in pdf.columns] or ["User name", "Service date"]
            neu_raw = append_rows(pdf, "playtomic_raw", key_raw)
            zahlungen = _zahlungs_index(pdf)

    # ── Buchungen aufbereiten ───────────────────────────────────────────
    b = bdf.copy()
    if "is_canceled" in b.columns:
        b = b[~b["is_canceled"].astype(str).str.lower().isin(["true", "1", "ja"])]
    if b.empty:
        st.error("❌ Nach Abzug der Stornierungen bleiben keine Buchungen übrig.")
        return False

    b["_start"] = b["booking_start_date"].map(parse_datetime_safe)
    b = b[b["_start"].notna()].copy()
    b["_datum"] = b["_start"].map(lambda d: d.date())
    b["_zeit"] = b["_start"].map(lambda d: d.strftime("%H:%M"))
    b["_preis"] = (b["price"].astype(str).str.replace(" EUR", "", regex=False)
                   .str.replace(",", ".").map(parse_betrag))
    b["_min"] = pd.to_numeric(b.get("duration (minutes)"), errors="coerce").fillna(60)
    b["_single"] = b["resource_name"].astype(str).str.contains("Single", case=False, na=False)
    b["_court"] = b["resource_name"].astype(str)

    # ── Check-ins aufbereiten ───────────────────────────────────────────
    c = cdf.copy()
    um = {"Vor- & Nachname": "Name", "Datum": "Checkin_Datum_raw"}
    if "Zeit" in c.columns:
        um["Zeit"] = "Checkin_Zeit"
    c = c.rename(columns=um)
    if "Name" not in c.columns:
        st.error("❌ In der Check-in-Datei fehlt eine Namensspalte.")
        return False
    c["Name"] = c["Name"].astype(str)
    c["Name_norm"] = c["Name"].map(normalize_name)
    c["Checkin_Datum"] = c["Checkin_Datum_raw"].map(parse_date_safe)
    if "Checkin_Zeit" not in c.columns:
        c["Checkin_Zeit"] = ""
    c["Checkin_Zeit"] = c["Checkin_Zeit"].fillna("").astype(str)
    c = c[c["Checkin_Datum"].notna()].copy()

    alle_tage = sorted(set(b["_datum"]) | set(c["Checkin_Datum"]))
    if not alle_tage:
        st.error("❌ Keine gültigen Tage gefunden.")
        return False

    balken = st.progress(0.0)
    status = st.empty()

    mapping = mapping_laden()
    b_tag = dict(tuple(b.groupby("_datum")))
    c_tag = dict(tuple(c.groupby("Checkin_Datum")))

    buchungen_out, checkins_out, kunden_out = [], [], []

    for i, tag in enumerate(alle_tage):
        balken.progress((i + 1) / len(alle_tage))
        status.caption(f"{tag.strftime('%d.%m.%Y')} · {i+1}/{len(alle_tage)}")

        bt = b_tag.get(tag, pd.DataFrame())
        ct = c_tag.get(tag, pd.DataFrame())
        checkin_namen = set(ct["Name_norm"]) if not ct.empty else set()
        zeit_je_name = (dict(zip(ct["Name_norm"], ct["Checkin_Zeit"]))
                        if not ct.empty else {})
        schon_zugeordnet = set()

        for _, row in bt.iterrows():
            teilnehmer = _teilnehmer_liste(row)
            if not teilnehmer:
                continue

            namen_norm = [normalize_name(n) for n, _ in teilnehmer]

            # Schul- und Gruppenbuchungen ausklammern
            if any(k in namen_norm[0] for k in ("schule", "gruppe", "kurs",
                                                "training", "turnier")):
                continue

            # Reine Team-Buchungen ausklammern — die laufen immer auf 0 €
            # und haben nichts mit Wellpass zu tun
            if all(n in TEAM_NORM for n in namen_norm):
                continue

            liste = listenpreis(row["_start"], row["_min"], bool(row["_single"]))
            plaetze = court_plaetze(row["_court"])
            pro_platz = round(liste / max(plaetze, 1), 2)

            # Sitzt jemand vom Team mit drin, zahlt der 0 € — dessen Platz
            # darf nicht als Wellpass-Rabatt gezählt werden.
            team_im_spiel = sum(1 for n in namen_norm if n in TEAM_NORM)
            liste_effektiv = liste - team_im_spiel * pro_platz
            n_wellpass = wellpass_anzahl(liste_effektiv, row["_preis"],
                                         max(plaetze - team_im_spiel, 1))

            # Wer von den Teilnehmern hat eingecheckt?
            eingecheckt = []
            for name, _mail in teilnehmer:
                nn = normalize_name(name)
                if nn in checkin_namen:
                    eingecheckt.append(nn)
                    schon_zugeordnet.add(nn)
                elif nn in mapping:
                    g = mapping[nn]
                    gname = g["checkin_name"] if isinstance(g, dict) else g
                    if gname in checkin_namen:
                        eingecheckt.append(gname)
                        schon_zugeordnet.add(gname)

            fehlend = max(0, n_wellpass - len(eingecheckt))
            traeger = _wellpass_traeger(teilnehmer, row["_start"], pro_platz,
                                        n_wellpass, zahlungen)

            for name, mail in teilnehmer:
                nn = normalize_name(name)
                hat_checkin = nn in eingecheckt or (
                    nn in mapping and
                    (mapping[nn]["checkin_name"] if isinstance(mapping[nn], dict)
                     else mapping[nn]) in eingecheckt)
                team = nn in TEAM_NORM

                # Fehler: hatte nachweislich den Rabatt, keinen Check-in,
                # gehört nicht zum Team.
                fehler = (fehlend > 0 and nn in traeger
                          and not hat_checkin and not team)

                buchungen_out.append({
                    "Datum": str(tag),
                    "Name": name,
                    "Name_norm": nn,
                    "Email": mail,
                    "Court": row["_court"],
                    "Service_Zeit": row["_zeit"],
                    "Dauer": int(row["_min"]),
                    "Listenpreis": liste,
                    "Bezahlt": row["_preis"],
                    "Betrag": pro_platz,
                    "Plaetze": plaetze,
                    "Wellpass_Rabatte": n_wellpass,
                    "Teilnehmer": len(teilnehmer),
                    "Checkin_Zeit": zeit_je_name.get(nn, ""),
                    "Relevant": "Ja" if n_wellpass > 0 else "Nein",
                    "Check-in": "Ja" if hat_checkin else "Nein",
                    "Team": "Ja" if team else "Nein",
                    "Fehler": "Ja" if fehler else "Nein",
                    "analysis_date": tag.strftime("%Y-%m-%d"),
                })

                if mail:
                    kunden_out.append({"name": name, "name_norm": nn,
                                       "email": mail, "phone_number": ""})

        if not ct.empty:
            for _, row in ct.iterrows():
                checkins_out.append({
                    "Datum": str(tag),
                    "Name": row["Name"],
                    "Name_norm": row["Name_norm"],
                    "Checkin_Zeit": row["Checkin_Zeit"],
                    "Gespielt": "Ja" if row["Name_norm"] in schon_zugeordnet else "Nein",
                    "analysis_date": tag.strftime("%Y-%m-%d"),
                })

    balken.progress(1.0)
    status.empty()

    neu_b = append_rows(pd.DataFrame(buchungen_out), "buchungen",
                        ["analysis_date", "Name_norm", "Service_Zeit", "Court"])
    neu_c = append_rows(pd.DataFrame(checkins_out), "checkins",
                        ["analysis_date", "Name_norm", "Checkin_Zeit"])

    # E-Mails in die Kundenliste übernehmen (für WhatsApp und EGYM-Nachmeldung)
    neu_k = 0
    if kunden_out:
        kdf = pd.DataFrame(kunden_out).drop_duplicates(subset=["name_norm"])
        alt = loadsheet("customers")
        if not alt.empty and "name_norm" in alt.columns:
            # Bestehende Telefonnummern nicht überschreiben
            zusammen = _kunden_index(alt)
            for _, r in kdf.iterrows():
                nn = r["name_norm"]
                if nn in zusammen:
                    if not str(zusammen[nn].get("email", "")).strip():
                        zusammen[nn]["email"] = r["email"]
                        neu_k += 1
                else:
                    zusammen[nn] = {"name": r["name"], "email": r["email"],
                                    "phone_number": ""}
                    neu_k += 1
            neu_df = pd.DataFrame([{"name_norm": k, **v} for k, v in zusammen.items()])
            savesheet(neu_df, "customers")
        else:
            savesheet(kdf, "customers")
            neu_k = len(kdf)

    cache_leeren()

    st.success(f"✅ {neu_b} Buchungszeilen · {neu_c} Check-ins · "
               f"{neu_k} Kunden ergänzt"
               + (f" · {neu_raw} Zahlungszeilen" if neu_raw else ""))
    if neu_b or neu_c:
        st.balloons()
    else:
        box("Alle Daten waren bereits im System.", "info")
    return True


def modul_daten():
    head("Daten-Zentrale", "Playtomic · Wellpass · Kunden")

    t1, t2, t3 = st.tabs(["📊 Buchungen + Check-ins", "👥 Kundenliste", "🗂 Bestand"])

    # ── Haupt-Upload ────────────────────────────────────────────────────
    with t1:
        box("Die App vergleicht den Listenpreis jeder Buchung mit dem tatsächlich "
            "gezahlten Betrag. Die Lücke verrät, wie viele Wellpass-Rabatte drin "
            "steckten. Danach prüft sie, wer davon wirklich eingecheckt hat.", "info")

        c1, c2 = st.columns(2)
        with c1:
            b_datei = st.file_uploader("Buchungen · bookings-download.csv",
                                       type=["csv"], key="up_b")
            if b_datei:
                st.caption(f"✓ {b_datei.name}")
        with c2:
            c_datei = st.file_uploader("Wellpass Check-ins (.csv)", type=["csv"],
                                       key="up_c")
            if c_datei:
                st.caption(f"✓ {c_datei.name}")

        p_datei = st.file_uploader("Zahlungen (optional, nur für den Umsatz)",
                                   type=["csv"], key="up_p")
        if p_datei:
            st.caption(f"✓ {p_datei.name}")

        st.markdown("")
        if st.button("🔄 Daten verarbeiten", type="primary",
                     use_container_width=True,
                     disabled=not (b_datei and c_datei)):
            with st.spinner(lade_text("verarbeite")):
                if _verarbeiten(b_datei, c_datei, p_datei):
                    time.sleep(1.1)
                    st.rerun()

        if not (b_datei and c_datei):
            st.caption("Buchungen und Check-ins werden für den Abgleich gebraucht. "
                       "Die Zahlungsdatei ist optional.")

        with st.expander("Wo finde ich die Exporte?"):
            st.markdown(f"""
**Buchungen (wichtigste Datei)**
1. Playtomic Manager → *Bookings* / *Buchungen*
2. Zeitraum wählen → **Download**
3. Datei heisst meist `bookings-download.csv`

**Zahlungen (optional)**
1. Playtomic Manager → *Payments* / *Zahlungen*
2. Zeitraum wählen → CSV exportieren

**EGYM Wellpass**
1. Partner-Portal öffnen
2. *Check-ins* → Zeitraum wählen
3. CSV exportieren

Direktlink zu deinem Club: {CONFIG['playtomic']}
""")

    # ── Kundenliste ─────────────────────────────────────────────────────
    with t2:
        box("Ohne Telefonnummern kann die App keine WhatsApp-Reminder senden. "
            "E-Mail und Geburtstag braucht sie zusätzlich für EGYM-Nachmeldungen.",
            "info")

        k_datei = st.file_uploader("Kundenliste (.csv)", type=["csv"], key="up_k")

        if k_datei and st.button("📤 Speichern", type="primary",
                                 use_container_width=True):
            df = parse_kunden(k_datei)
            if df.empty:
                st.error("❌ Datei konnte nicht gelesen werden.")
            elif "name" not in df.columns:
                st.error("❌ Spalte mit Namen fehlt.")
                st.caption("Gefunden: " + ", ".join(df.columns))
            else:
                df["name_norm"] = df["name"].map(normalize_name)
                if "phone_number" in df.columns:
                    df["phone_number"] = df["phone_number"].map(telefon_normalisieren)
                else:
                    spalten = ", ".join(str(c) for c in df.columns)
                    box("In dieser Datei wurde keine Telefonspalte gefunden. "
                        "Die Spalte sollte Telefon, Handy, Mobil oder Phone "
                        f"heissen. Gefundene Spalten: <b>{spalten}</b>", "warn")

                # Bestehende Daten ergänzen statt überschreiben
                alt_df = loadsheet("customers")
                if not alt_df.empty and "name_norm" in alt_df.columns:
                    zusammen = _kunden_index(alt_df)
                    for _, r in df.iterrows():
                        nn = r["name_norm"]
                        eintrag = zusammen.get(nn, {})
                        for feld in ("name", "email", "phone_number", "geburtstag"):
                            wert = str(r.get(feld, "") or "").strip()
                            if wert and wert.lower() not in ("nan", "none"):
                                eintrag[feld] = wert
                            elif feld not in eintrag:
                                eintrag[feld] = ""
                        zusammen[nn] = eintrag
                    df = pd.DataFrame([{"name_norm": k, **v}
                                       for k, v in zusammen.items()])

                if savesheet(df, "customers"):
                    cache_leeren()
                    mit_tel = (int((df["phone_number"].astype(str).str.len() > 5).sum())
                               if "phone_number" in df.columns else 0)
                    st.success(f"✅ {len(df)} Kunden gespeichert · "
                               f"{mit_tel} mit Telefonnummer")
                    time.sleep(1.2)
                    st.rerun()

        kunden = loadsheet("customers")
        if not kunden.empty:
            c1, c2, c3 = st.columns(3)
            with c1:
                kpi("Kunden", str(len(kunden)))
            with c2:
                mit_tel = int((kunden["phone_number"].astype(str).str.len() > 5).sum()) \
                          if "phone_number" in kunden.columns else 0
                kpi("mit Telefon", str(mit_tel),
                    f"{prozent(mit_tel, len(kunden)):.0f} % erreichbar")
            with c3:
                mit_mail = int((kunden["email"].astype(str).str.contains("@")).sum()) \
                           if "email" in kunden.columns else 0
                kpi("mit E-Mail", str(mit_mail), "für Nachmeldungen")

        with st.expander("Welche Spalten braucht die Datei?"):
            st.markdown("""
| Erkannt wird | Beispiel-Spaltennamen |
|---|---|
| Name | `name`, `Kunde`, `Spieler`, `Vor- & Nachname` |
| Telefon | `phone`, `Telefon`, `Mobil`, `Handy` |
| E-Mail | alles mit `mail` |
| Geburtstag | `geburtstag`, `Geburtsdatum`, `birth` |

Nummern werden automatisch umgewandelt: `0170…` → `+49170…`
""")

    # ── Bestand ─────────────────────────────────────────────────────────
    with t3:
        raw = loadsheet("playtomic_raw")
        buch = loadsheet("buchungen")
        chk = loadsheet("checkins")
        kunden = loadsheet("customers")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi("Rohdaten", f"{len(raw):,}".replace(",", "."), "Playtomic-Zeilen")
        with c2:
            kpi("Buchungen", f"{len(buch):,}".replace(",", "."), "abgeglichen")
        with c3:
            kpi("Check-ins", f"{len(chk):,}".replace(",", "."), "Wellpass")
        with c4:
            kpi("Kunden", str(len(kunden)))

        tage = verfuegbare_tage()
        st.markdown("")
        if tage:
            box(f"Daten für <b>{len(tage)} Tage</b> — von {datum_kurz(tage[-1])} "
                f"bis {datum_kurz(tage[0])}.", "ok")
        else:
            box("Noch keine verarbeiteten Daten.", "warn")

        # ── Umsatz-Diagnose ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### Umsatz-Prüfung")
        st.caption("Kommt dir eine Zahl zu hoch vor? Hier siehst du, woraus "
                   "sie sich zusammensetzt.")

        roh_p = _rohdaten_aufbereitet()
        if roh_p.empty:
            box("Keine Zahlungsdaten vorhanden.", "info")
        else:
            je_tag = (roh_p.groupby("_datum")
                      .agg(zeilen=("_betrag", "size"), summe=("_betrag", "sum"))
                      .reset_index().sort_values("_datum", ascending=False))
            d1, d2, d3 = st.columns(3)
            with d1:
                kpi("Zahlungszeilen", f"{len(roh_p):,}".replace(",", "."))
            with d2:
                kpi("Erfasste Tage", str(len(je_tag)))
            with d3:
                kpi("Ø pro Tag", euro(je_tag["summe"].mean()))

            auffaellig = je_tag[je_tag["summe"] > je_tag["summe"].median() * 2.5]
            if not auffaellig.empty:
                box(f"⚠️ <b>{len(auffaellig)} Tage</b> liegen mehr als doppelt "
                    "so hoch wie der Mittelwert. Das deutet darauf hin, dass "
                    "für diese Tage mehrere sich überschneidende Exporte "
                    "hochgeladen wurden.", "warn")

            with st.expander("Umsatz pro Tag ansehen"):
                zeig = je_tag.copy()
                zeig["_datum"] = zeig["_datum"].astype(str)
                zeig["summe"] = zeig["summe"].map(euro)
                zeig.columns = ["Datum", "Zeilen", "Umsatz"]
                st.dataframe(zeig, use_container_width=True, hide_index=True,
                             height=300)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Cache**")
            st.caption("Daten werden 30 Min zwischengespeichert, um Google zu schonen.")
            if st.button("🔄 Neu von Google laden", use_container_width=True):
                cache_leeren()
                st.success("Cache geleert.")
                time.sleep(.7)
                st.rerun()
        with c2:
            st.markdown("**Export**")
            st.caption("Alle abgeglichenen Buchungen als CSV sichern.")
            if not buch.empty:
                st.download_button(
                    "⬇️ Buchungen exportieren",
                    data=buch.to_csv(index=False, sep=";").encode("utf-8-sig"),
                    file_name=f"padelcircle_buchungen_{date.today()}.csv",
                    mime="text/csv", use_container_width=True)

        st.markdown("---")
        with st.expander("🧹 Daten zurücksetzen"):
            box("Wenn die Zahlen durcheinander sind, kannst du einzelne "
                "Datenbereiche leeren und sauber neu hochladen. Deine "
                "gelernten Namenszuordnungen und erledigten Fälle bleiben "
                "dabei erhalten.", "warn")
            was = st.selectbox("Was soll geleert werden?", [
                "Zahlungen (Umsatzbasis)",
                "Buchungen und Check-ins",
                "Alles außer Zuordnungen",
            ], key="reset_was")
            bestaetigt = st.checkbox("Ja, wirklich leeren", key="reset_ok")
            if st.button("Jetzt leeren", disabled=not bestaetigt,
                         use_container_width=True):
                ziele = {
                    "Zahlungen (Umsatzbasis)": ["playtomic_raw"],
                    "Buchungen und Check-ins": ["buchungen", "checkins"],
                    "Alles außer Zuordnungen": ["playtomic_raw", "buchungen",
                                                "checkins"],
                }[was]
                for z in ziele:
                    savesheet(pd.DataFrame(), z)
                cache_leeren()
                st.success(f"Geleert: {', '.join(ziele)}")
                time.sleep(1.2)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#   📊  MODUL · DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def _dash_tag():
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten. Starte in der Daten-Zentrale.", "warn")
        return

    st.session_state.setdefault("tag_idx", 0)
    st.session_state.tag_idx = max(0, min(st.session_state.tag_idx, len(tage) - 1))

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Früher", use_container_width=True,
                     disabled=st.session_state.tag_idx >= len(tage) - 1):
            st.session_state.tag_idx += 1
            st.rerun()
    with c3:
        if st.button("Später →", use_container_width=True,
                     disabled=st.session_state.tag_idx <= 0):
            st.session_state.tag_idx -= 1
            st.rerun()

    datum = tage[st.session_state.tag_idx]
    with c2:
        st.markdown(f"<div style='text-align:center;padding-top:.4rem;"
                    f"font-weight:600;color:{C['text']};'>{datum_lang(datum)}</div>",
                    unsafe_allow_html=True)

    st.markdown("")
    k = tages_kennzahlen(datum)

    # Vergleich mit dem Vortag in den Daten
    idx = st.session_state.tag_idx
    vor = tages_kennzahlen(tage[idx + 1]) if idx + 1 < len(tage) else None
    delta_umsatz = None
    if vor and vor["gesamt_effektiv"]:
        delta_umsatz = ((k["gesamt_effektiv"] - vor["gesamt_effektiv"])
                        / vor["gesamt_effektiv"] * 100)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Gesamt effektiv", euro(k["gesamt_effektiv"]), "inkl. Wellpass",
            delta=delta_umsatz, delta_text="ggü. Vortag")
    with c2:
        kpi("Playtomic", euro(k["umsatz"]), f"{k['buchungen']} Buchungen")
    with c3:
        kpi("Wellpass", str(k["wellpass_anzahl"]),
            f"{euro(k['wellpass_wert'])} von EGYM")
    with c4:
        kpi("Spieler", str(k["spieler"]), "eindeutige Personen")

    if k["guthaben"] or k["schlaeger"] or k["baelle"]:
        st.markdown("")
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi("Guthaben", euro(k["guthaben"]))
        with c2:
            kpi("Leihschläger", euro(k["schlaeger"]))
        with c3:
            kpi("Bälle", euro(k["baelle"]))

    # ── Offene Fehler ───────────────────────────────────────────────────
    st.markdown("---")
    fehler = offene_fehler(datum)

    if fehler.empty:
        serie = sauber_serie(tage)
        if serie >= 2:
            streak_banner(serie)
        else:
            box("✅ Alle Wellpass-Check-ins sind da.", "ok")
    else:
        box(f"⚠️ <b>{len(fehler)} Spieler</b> ohne Check-in. "
            f"Potenzieller Verlust: {euro(len(fehler) * WELLPASS_WERT)}", "warn")

        for _, r in fehler.iterrows():
            c1, c2, c3 = st.columns([3, 2, 1.3])
            with c1:
                st.markdown(f"**{r['Name']}**")
                zeit = str(r.get("Service_Zeit", "")).strip()
                st.caption(f"{zeit + ' Uhr · ' if zeit else ''}"
                           f"{euro(r.get('Betrag', 0))}")
            with c2:
                nr = telefon_fuer(str(r["Name"]))
                st.caption(f"📱 {nr}" if nr else "keine Nummer hinterlegt")
            with c3:
                if st.button("Erledigt", key=f"dt_ok_{r['Name_norm']}_{r['Datum']}",
                             use_container_width=True):
                    als_behoben_markieren(str(r["Name_norm"]), str(r["Datum"]))
                    st.rerun()

    # ── Check-ins ohne Buchung ──────────────────────────────────────────
    ohne = checkins_ohne_buchung(datum)
    if not ohne.empty:
        st.markdown("")
        box(f"👀 <b>{len(ohne)} Check-ins ohne passende Buchung.</b> "
            "Entweder fehlt die Buchung im Playtomic-Export, oder jemand hat "
            "eingecheckt ohne zu spielen.", "info")
        with st.expander("Wer war das?"):
            st.dataframe(ohne[["Name", "Checkin_Zeit"]],
                         use_container_width=True, hide_index=True)

    # ── Stunden-Verteilung des Tages ────────────────────────────────────
    tag_daten = tag_details(datum)
    if not tag_daten.empty and "Service_Zeit" in tag_daten.columns:
        stunden = (tag_daten["Service_Zeit"].map(stunde_aus_zeit)
                   .loc[lambda s: s >= 0])
        if not stunden.empty:
            st.markdown("")
            st.markdown("**Wann war was los?**")
            zaehl = stunden.value_counts().sort_index()
            alle_std = list(range(CONFIG["oeffnung_von"], CONFIG["oeffnung_bis"]))
            werte = [int(zaehl.get(s, 0)) for s in alle_std]

            fig = go.Figure(go.Bar(
                x=[f"{s}:00" for s in alle_std], y=werte,
                marker_color=[C["volt"] if v == max(werte) and v > 0
                              else C["blue_soft"] for v in werte],
                hovertemplate="%{x}<br>%{y} Buchungen<extra></extra>",
            ))
            st.plotly_chart(plotly_layout(fig, 250, "Buchungen"),
                            use_container_width=True)

    with st.expander("Alle Buchungen des Tages"):
        if tag_daten.empty:
            st.caption("Keine Buchungen.")
        else:
            spalten = [c for c in ["Name", "Service_Zeit", "Betrag", "Check-in",
                                   "Relevant", "Team"] if c in tag_daten.columns]
            zeig = tag_daten[spalten].copy()
            zeig.columns = [{"Service_Zeit": "Zeit", "Relevant": "Wellpass-pflichtig"}
                            .get(c, c) for c in spalten]
            st.dataframe(zeig, use_container_width=True, hide_index=True)


def _dash_monat():
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    monate = sorted({t[:7] for t in tage}, reverse=True)
    monat = st.selectbox(
        "Monat", monate,
        format_func=lambda m: f"{MONATE_DE[int(m[5:7])-1]} {m[:4]}")

    k = monats_kennzahlen(monat)
    pg = prognose_monat(monat)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Gesamt effektiv", euro(k["gesamt_effektiv"]), "inkl. Wellpass")
    with c2:
        kpi("Playtomic", euro(k["umsatz"]))
    with c3:
        kpi("Wellpass", euro(k["wellpass_wert"]),
            f"{k['wellpass_anzahl']} Check-ins")
    with c4:
        kpi("Ø pro Tag", euro(pg["schnitt_pro_tag"]),
            f"{pg['tage_erfasst']} Tage erfasst")

    # ── Zielfortschritt ─────────────────────────────────────────────────
    ziel = pg["ziel"]
    if ziel > 0:
        st.markdown("")
        erreicht = prozent(k["gesamt_effektiv"], ziel)
        rest = max(0.0, ziel - k["gesamt_effektiv"])
        prog_text = (f"Hochrechnung Monatsende: <b>{euro(pg['prognose'])}</b><br>"
                     f"Ziel: {euro(ziel)} · "
                     + (f"noch {euro(rest)}" if rest > 0 else "Ziel erreicht 🎉"))
        fortschritts_ring(erreicht, f"{erreicht:.0f}%",
                          f"{MONATE_DE[int(monat[5:7])-1]} {monat[:4]}", prog_text)

    # ── Umsatz pro Tag ──────────────────────────────────────────────────
    monats_tage = sorted([t for t in tage if t.startswith(monat)])
    if not monats_tage:
        return

    reihen = [{"tag": t[8:10],
               "Playtomic": tages_kennzahlen(t)["umsatz"],
               "Wellpass": tages_kennzahlen(t)["wellpass_wert"]}
              for t in monats_tage]
    df = pd.DataFrame(reihen)

    st.markdown("")
    st.markdown("**Umsatz pro Tag**")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["tag"], y=df["Playtomic"], name="Playtomic",
                         marker_color=C["blue_soft"]))
    fig.add_trace(go.Bar(x=df["tag"], y=df["Wellpass"], name="Wellpass",
                         marker_color=C["volt"]))
    fig.update_layout(barmode="stack")
    st.plotly_chart(plotly_layout(fig, 320), use_container_width=True)

    # ── Wellpass-Disziplin ──────────────────────────────────────────────
    b = loadsheet("buchungen")
    if not b.empty and "analysis_date" in b.columns:
        mb = b[b["analysis_date"].astype(str).str.startswith(monat)]
        if not mb.empty and "Relevant" in mb.columns:
            pflicht = mb[mb["Relevant"].astype(str) == "Ja"]
            verg = pflicht[pflicht["Fehler"].astype(str) == "Ja"]
            if len(pflicht):
                quote = prozent(len(verg), len(pflicht))
                st.markdown("")
                c1, c2, c3 = st.columns(3)
                with c1:
                    kpi("Wellpass-pflichtig", str(len(pflicht)))
                with c2:
                    kpi("vergessen", str(len(verg)),
                        f"entgangen: {euro(len(verg) * WELLPASS_WERT)}")
                with c3:
                    kpi("Vergess-Quote", f"{quote:.1f} %",
                        "unter 10 % ist gut")


def _dash_auslastung():
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    monate = sorted({t[:7] for t in tage}, reverse=True)
    wahl = st.selectbox("Zeitraum", ["Alle Daten"] + monate,
                        format_func=lambda m: m if m == "Alle Daten"
                        else f"{MONATE_DE[int(m[5:7])-1]} {m[:4]}")
    monat = None if wahl == "Alle Daten" else wahl

    matrix = auslastung_matrix(monat)
    if matrix.empty:
        box("Zu wenig Daten für die Auslastung.", "info")
        return

    box("Je heller das Feld, desto mehr Buchungen. Dunkle Felder in der "
        "Prime-Time sind ungenutzte Zeit — dort lohnen sich Events, Kurse "
        "oder Aktionen.", "info")

    stunden = list(range(CONFIG["oeffnung_von"], CONFIG["oeffnung_bis"]))
    z = [[0] * len(stunden) for _ in range(7)]
    for _, r in matrix.iterrows():
        wt, std = int(r["_wochentag"]), int(r["_stunde"])
        if 0 <= wt < 7 and std in stunden:
            z[wt][stunden.index(std)] = int(r["anzahl"])

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"{s}:00" for s in stunden],
        y=WOCHENTAGE_KURZ,
        colorscale=[[0, C["ink2"]], [0.45, C["blue"]], [1, C["volt"]]],
        hovertemplate="%{y} %{x}<br>%{z} Buchungen<extra></extra>",
        showscale=False,
    ))
    fig.update_layout(height=310, margin=dict(l=8, r=8, t=20, b=8),
                      plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(color=C["text"], size=12))
    st.plotly_chart(fig, use_container_width=True)

    # ── Beste und schwächste Slots ──────────────────────────────────────
    flach = []
    for wt in range(7):
        for i, std in enumerate(stunden):
            flach.append({"wt": wt, "std": std, "n": z[wt][i]})
    fdf = pd.DataFrame(flach)

    top = fdf.nlargest(5, "n")
    prime = fdf[(fdf["std"] >= 16) & (fdf["n"] == 0)]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Stärkste Slots**")
        for _, r in top.iterrows():
            if r["n"] > 0:
                st.markdown(f"<div class='pc-row'><span class='nm'>"
                            f"{WOCHENTAGE_DE[int(r['wt'])]} {int(r['std'])}:00</span>"
                            f"<span class='mt'>{int(r['n'])} Buchungen</span></div>",
                            unsafe_allow_html=True)
    with c2:
        st.markdown("**Leere Prime-Time-Slots**")
        if prime.empty:
            st.caption("Keine — Prime-Time läuft überall.")
        else:
            st.caption(f"{len(prime)} Slots ab 16 Uhr ohne einzige Buchung.")
            for _, r in prime.head(5).iterrows():
                st.markdown(f"<div class='pc-row'><span class='nm'>"
                            f"{WOCHENTAGE_DE[int(r['wt'])]} {int(r['std'])}:00</span>"
                            f"<span class='mt'>leer</span></div>",
                            unsafe_allow_html=True)


def _dash_abgleich():
    """Monatliche Gegenüberstellung: gegebene Rabatte vs. vergütete Check-ins."""
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    box("Zwei Zahlen müssen zusammenpassen: wie viele Rabatte du gegeben hast "
        "und wie viele Check-ins EGYM dir vergütet. Beide Abweichungen zeigt "
        "die App getrennt — sie heben sich nicht gegenseitig auf.", "info")

    monate = sorted({t[:7] for t in tage}, reverse=True)
    monat = st.selectbox("Monat", monate,
                         format_func=lambda m: f"{MONATE_DE[int(m[5:7])-1]} {m[:4]}",
                         key="abgl_monat")

    b = loadsheet("buchungen")
    c = loadsheet("checkins")
    if b.empty:
        box("Keine Buchungsdaten.", "warn")
        return

    mb = b[b["analysis_date"].astype(str).str.startswith(monat)].copy()
    mc = (c[c["analysis_date"].astype(str).str.startswith(monat)].copy()
          if not c.empty and "analysis_date" in c.columns else pd.DataFrame())

    if mb.empty:
        box("Für diesen Monat liegen keine Buchungen vor.", "warn")
        return

    # ── Rabatte pro Buchung zählen ──────────────────────────────────────
    schluessel = [x for x in ("analysis_date", "Court", "Service_Zeit")
                  if x in mb.columns]
    if "Wellpass_Rabatte" in mb.columns and schluessel:
        eindeutig = mb.drop_duplicates(subset=schluessel)
        rabatte = int(pd.to_numeric(eindeutig["Wellpass_Rabatte"],
                                    errors="coerce").fillna(0).sum())
    else:
        rabatte = 0
        box("Diese Daten stammen aus einer Vorgängerversion. Lade die "
            "betroffenen Tage in der Daten-Zentrale neu hoch.", "info")

    # ── Check-ins auswerten: nur einer pro Person und Tag zählt ─────────
    verguetet = doppelt = 0
    if not mc.empty and {"Name_norm", "analysis_date"} <= set(mc.columns):
        je_tag = mc.groupby("analysis_date")["Name_norm"]
        verguetet = int(je_tag.nunique().sum())
        doppelt = len(mc) - verguetet

    fehlend = max(0, rabatte - verguetet)
    ohne_buchung = 0
    if not mc.empty and "Gespielt" in mc.columns:
        ohne = mc[mc["Gespielt"].astype(str) == "Nein"]
        if not ohne.empty and {"Name_norm", "analysis_date"} <= set(ohne.columns):
            ohne_buchung = int(ohne.groupby("analysis_date")["Name_norm"]
                               .nunique().sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Rabatte gegeben", str(rabatte), "laut Playtomic-Preisen")
    with c2:
        kpi("Davon vergütet", str(verguetet),
            f"{doppelt} Doppel-Check-ins ohne Wert" if doppelt else "durch EGYM")
    with c3:
        kpi("Nicht vergütet", str(fehlend),
            "Rabatt gegeben, kein Check-in")
    with c4:
        kpi("Verlust", euro(fehlend * WELLPASS_WERT), "entgangene Vergütung")

    st.markdown("")
    if fehlend == 0:
        box("✅ <b>Sauber.</b> Für jeden gegebenen Rabatt liegt ein vergüteter "
            "Check-in vor.", "ok")
    else:
        box(f"⚠️ <b>{fehlend} Rabatte ohne Vergütung</b> — das sind "
            f"{euro(fehlend * WELLPASS_WERT)}, die dir für diesen Monat fehlen.",
            "warn")

    if doppelt:
        box(f"ℹ️ <b>{doppelt} Doppel-Check-ins.</b> EGYM vergütet pro Person und "
            "Tag nur einmal — diese Check-ins bringen dir nichts. Meist steckt "
            "dahinter jemand, der zweimal am Terminal war.", "info")

    if ohne_buchung:
        box(f"👀 <b>{ohne_buchung} Check-ins ohne Buchung.</b> Entweder eine "
            "Namensvariante — dann im Modul <i>Name-Abgleich</i> oder direkt beim "
            "WhatsApp-Reminder zuordnen. Oder jemand hat mitgespielt, ohne in "
            "Playtomic eingetragen zu sein.", "info")

    # ── Tagesverlauf ────────────────────────────────────────────────────
    monats_tage = sorted([t for t in tage if t.startswith(monat)])
    tag_schluessel = [x for x in ("Court", "Service_Zeit") if x in mb.columns]
    reihen = []
    for t in monats_tage:
        tb = mb[mb["analysis_date"].astype(str) == t]
        eind = tb.drop_duplicates(subset=tag_schluessel) if tag_schluessel else tb
        rab = (int(pd.to_numeric(eind["Wellpass_Rabatte"], errors="coerce")
                   .fillna(0).sum())
               if ("Wellpass_Rabatte" in eind.columns and not eind.empty) else 0)
        tc = mc[mc["analysis_date"].astype(str) == t] if not mc.empty else pd.DataFrame()
        verg = int(tc["Name_norm"].nunique()) if not tc.empty and "Name_norm" in tc.columns else 0
        reihen.append({"tag": t[8:10], "Rabatte": rab, "Vergütet": verg})

    if reihen:
        df = pd.DataFrame(reihen)
        st.markdown("")
        st.markdown("**Tag für Tag**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["tag"], y=df["Rabatte"], name="Rabatte gegeben",
                             marker_color=C["blue_soft"]))
        fig.add_trace(go.Bar(x=df["tag"], y=df["Vergütet"], name="Vergütet",
                             marker_color=C["volt"]))
        fig.update_layout(barmode="group")
        st.plotly_chart(plotly_layout(fig, 300, "Anzahl"), use_container_width=True)

    # ── Zwei Listen ─────────────────────────────────────────────────────
    st.markdown("---")
    l1, l2 = st.tabs(["Nicht vergütet", "Check-ins ohne Buchung"])

    with l1:
        offen_df = mb[mb["Fehler"].astype(str) == "Ja"] if "Fehler" in mb.columns else pd.DataFrame()
        if offen_df.empty:
            box("Keine offenen Einzelfälle.", "ok")
        else:
            spalten = [x for x in ["analysis_date", "Name", "Court", "Service_Zeit",
                                   "Listenpreis", "Bezahlt", "Email"]
                       if x in offen_df.columns]
            zeig = offen_df[spalten].copy()
            zeig.columns = [{"analysis_date": "Datum", "Service_Zeit": "Zeit",
                             "Listenpreis": "Liste", "Bezahlt": "Gezahlt",
                             "Email": "E-Mail"}.get(x, x) for x in spalten]
            st.dataframe(zeig.sort_values("Datum", ascending=False),
                         use_container_width=True, hide_index=True, height=330)
            st.download_button(
                "⬇️ Als CSV", data=zeig.to_csv(index=False, sep=";").encode("utf-8-sig"),
                file_name=f"nicht_verguetet_{monat}.csv", mime="text/csv",
                use_container_width=True)

    with l2:
        if mc.empty or "Gespielt" not in mc.columns:
            box("Keine Check-in-Daten.", "info")
        else:
            ohne = mc[mc["Gespielt"].astype(str) == "Nein"]
            if ohne.empty:
                box("✅ Alle Check-ins konnten einer Buchung zugeordnet werden.", "ok")
            else:
                box("Diese Personen haben eingecheckt, tauchen aber in keiner "
                    "Buchung auf. Ordne sie beim WhatsApp-Reminder zu — dann "
                    "verschwinden sie hier und der zugehörige Fall gilt als "
                    "geklärt.", "info")
                zeig2 = ohne[["analysis_date", "Name", "Checkin_Zeit"]].rename(
                    columns={"analysis_date": "Datum", "Checkin_Zeit": "Uhrzeit"})
                st.dataframe(zeig2.sort_values("Datum", ascending=False),
                             use_container_width=True, hide_index=True, height=330)


def modul_dashboard():
    head("Business Dashboard", "Umsatz · Auslastung · Abgleich")
    t1, t2, t3, t4 = st.tabs(["📅 Tag", "📈 Monat", "🔥 Auslastung", "⚖️ Monatsabgleich"])
    with t1:
        _dash_tag()
    with t2:
        _dash_monat()
    with t3:
        _dash_auslastung()
    with t4:
        _dash_abgleich()


# ══════════════════════════════════════════════════════════════════════════════
#   👥  MODUL · SPIELER & COMMUNITY
# ══════════════════════════════════════════════════════════════════════════════

MEDAILLEN = ["🥇", "🥈", "🥉"]


def _spieler_rangliste():
    stat = spieler_statistik()
    if stat.empty:
        box("Noch keine Spielerdaten.", "warn")
        return

    kunden = stat[~stat["team"]].copy()
    if kunden.empty:
        box("Noch keine Kunden erfasst — bisher nur Team-Buchungen.", "info")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Spieler gesamt", str(len(kunden)))
    with c2:
        viel = int((kunden["buchungen"] >= 5).sum())
        kpi("Vielspieler", str(viel), "5+ Buchungen")
    with c3:
        neu = int((kunden["buchungen"] == 1).sum())
        kpi("Einmal-Gäste", str(neu), "noch nicht wiedergekommen")
    with c4:
        schnitt = kunden["buchungen"].mean()
        kpi("Ø Buchungen", f"{schnitt:.1f}", "pro Spieler")

    st.markdown("")
    c1, c2 = st.columns([1, 1])
    with c1:
        sortier = st.selectbox("Sortieren nach",
                               ["buchungen", "umsatz", "vergessen", "treue_quote"],
                               format_func=lambda s: {
                                   "buchungen": "Buchungen",
                                   "umsatz": "Umsatz",
                                   "vergessen": "Vergessene Check-ins",
                                   "treue_quote": "Check-in-Disziplin",
                               }[s])
    with c2:
        anzahl = st.slider("Anzeigen", 10, 100, 25, step=5)

    liste = kunden.sort_values(sortier, ascending=False).head(anzahl)

    st.markdown("")
    for i, (_, r) in enumerate(liste.iterrows()):
        medaille = MEDAILLEN[i] if i < 3 and sortier == "buchungen" else ""
        quote = r["treue_quote"]
        if r["wellpass_pflichtig"] == 0:
            chip_html = chip("kein Wellpass", "soft")
        elif quote >= 90:
            chip_html = chip(f"{quote:.0f}% Disziplin", "lime")
        elif quote >= 60:
            chip_html = chip(f"{quote:.0f}% Disziplin", "warn")
        else:
            chip_html = chip(f"{quote:.0f}% Disziplin", "err")

        st.markdown(f"""
        <div class="pc-row">
          <div>
            <span class="pc-medal">{medaille}</span>
            <span class="nm">{r['Name']}</span>
            <span class="mt">&nbsp;· {int(r['buchungen'])} Buchungen
              · {euro(r['umsatz'])}</span>
          </div>
          <div>{chip_html}</div>
        </div>""", unsafe_allow_html=True)


def _vielspieler():
    stat = spieler_statistik()
    if stat.empty:
        box("Noch keine Daten.", "warn")
        return

    grenze = st.slider("Ab wie vielen Buchungen gilt jemand als Vielspieler?",
                       3, 30, 5)
    viel = stat[(~stat["team"]) & (stat["buchungen"] >= grenze)].copy()

    if viel.empty:
        box(f"Noch niemand mit {grenze}+ Buchungen. "
            "Das kommt mit der Zeit — gib der Halle ein paar Wochen.", "info")
        return

    umsatz_anteil = prozent(viel["umsatz"].sum(),
                            stat[~stat["team"]]["umsatz"].sum())

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Vielspieler", str(len(viel)), f"ab {grenze} Buchungen")
    with c2:
        kpi("Umsatzanteil", f"{umsatz_anteil:.0f} %", "von allen Kunden")
    with c3:
        kpi("Ø Buchungen", f"{viel['buchungen'].mean():.1f}")

    st.markdown("")
    box("Das sind die Leute die den Circle tragen. Eine kurze persönliche "
        "Nachricht wirkt hier stärker als jede Werbung.", "info")

    kunden_df = loadsheet("customers")
    hat_nummern = not kunden_df.empty and "phone_number" in kunden_df.columns

    for i, (_, r) in enumerate(viel.sort_values("buchungen", ascending=False)
                               .head(30).iterrows()):
        with st.container():
            c1, c2 = st.columns([3, 1.2])
            with c1:
                st.markdown(f"**{r['Name']}** · {int(r['buchungen'])} Buchungen "
                            f"· {euro(r['umsatz'])}")
                st.caption(f"Zuletzt vor {int(r['tage_her'])} Tagen · "
                           f"seit {datum_kurz(r['erster_besuch'])}")
            with c2:
                nummer = telefon_fuer(str(r["Name"])) if hat_nummern else ""
                if nummer:
                    st.caption(f"📱 {nummer}")
                else:
                    st.caption("keine Nummer")

            text = danke_nachricht(str(r["Name"]), int(r["buchungen"]))
            with st.expander("Danke-Nachricht"):
                st.code(text, language=None)
                if nummer and twilio_bereit():
                    if st.button("Senden", key=f"vs_{i}", use_container_width=True):
                        with st.spinner("Sende…"):
                            if whatsapp_senden(f"whatsapp:{nummer}", text):
                                whatsapp_loggen(str(r["Name"]),
                                                normalize_name(str(r["Name"])),
                                                str(date.today()), 0, nummer,
                                                art="danke")
                                st.success("✅ Gesendet.")
                                time.sleep(1)
                                st.rerun()


def _winback():
    box("Spieler die regelmässig da waren und plötzlich nicht mehr. "
        "Meist reicht eine kurze Nachricht, damit sie wiederkommen.", "info")

    c1, c2 = st.columns(2)
    with c1:
        min_buchungen = st.slider("Mindestens Buchungen gehabt", 2, 20, 3)
    with c2:
        tage_weg = st.slider("Seit mindestens … Tagen weg", 7, 120, 21)

    weg = winback_liste(min_buchungen, tage_weg)

    if weg.empty:
        box("✅ Niemand aus dem Raster gefallen. Deine Stammspieler kommen alle "
            "regelmässig.", "ok")
        return

    potenzial = weg["umsatz"].sum() / max(weg["buchungen"].sum(), 1) * len(weg)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Verlorene Spieler", str(len(weg)))
    with c2:
        kpi("Ø Tage weg", f"{weg['tage_her'].mean():.0f}")
    with c3:
        kpi("Rückhol-Potenzial", euro(potenzial), "grobe Schätzung")

    st.markdown("")
    kunden_df = loadsheet("customers")
    hat_nummern = not kunden_df.empty and "phone_number" in kunden_df.columns

    for i, (_, r) in enumerate(weg.head(30).iterrows()):
        c1, c2 = st.columns([3, 1.2])
        with c1:
            st.markdown(f"**{r['Name']}** · war {int(r['buchungen'])}× da")
            st.caption(f"Zuletzt vor {int(r['tage_her'])} Tagen "
                       f"({datum_kurz(r['letzter_besuch'])})")
        with c2:
            nummer = telefon_fuer(str(r["Name"])) if hat_nummern else ""
            st.caption(f"📱 {nummer}" if nummer else "keine Nummer")

        text = winback_nachricht(str(r["Name"]), int(r["tage_her"]))
        with st.expander("Nachricht"):
            st.code(text, language=None)
            if nummer and twilio_bereit():
                if st.button("Senden", key=f"wb_{i}", use_container_width=True):
                    with st.spinner("Sende…"):
                        if whatsapp_senden(f"whatsapp:{nummer}", text):
                            whatsapp_loggen(str(r["Name"]),
                                            normalize_name(str(r["Name"])),
                                            str(date.today()), 0, nummer,
                                            art="winback")
                            st.success("✅ Gesendet.")
                            time.sleep(1)
                            st.rerun()


def modul_spieler():
    head("Spieler & Community", "Rangliste · Vielspieler · Rückholung")
    t1, t2, t3 = st.tabs(["🏆 Rangliste", "⭐ Vielspieler", "🔄 Rückholung"])
    with t1:
        _spieler_rangliste()
    with t2:
        _vielspieler()
    with t3:
        _winback()


# ══════════════════════════════════════════════════════════════════════════════
#   💬  MODUL · WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

def twilio_bereit() -> bool:
    tw = st.secrets.get("twilio", {})
    return all(tw.get(k) for k in ("account_sid", "auth_token", "whatsapp_from"))


def whatsapp_senden(an_nummer: str, text: str) -> bool:
    try:
        from twilio.rest import Client
    except ImportError:
        st.error("❌ Paket `twilio` fehlt — in requirements.txt eintragen.")
        return False

    tw = st.secrets.get("twilio", {})
    sid, token, absender = (tw.get("account_sid"), tw.get("auth_token"),
                            tw.get("whatsapp_from"))
    if not all([sid, token, absender]):
        st.error("❌ Twilio ist noch nicht eingerichtet.")
        return False
    try:
        client = Client(sid, token)
        msg = client.messages.create(from_=absender, body=text, to=an_nummer)
        return bool(msg.sid)
    except Exception as e:
        st.error(f"❌ WhatsApp-Fehler: {str(e)[:200]}")
        return False


def telefon_fuer(name: str) -> str:
    kunden = loadsheet("customers")
    if kunden.empty or "name" not in kunden.columns \
            or "phone_number" not in kunden.columns:
        return ""
    ziel = normalize_name(name)
    k = kunden.copy()
    k["_n"] = k["name"].map(normalize_name)
    treffer = k[k["_n"] == ziel]
    if treffer.empty:
        return ""
    return telefon_normalisieren(treffer.iloc[0]["phone_number"])


def email_fuer(name: str) -> str:
    kunden = loadsheet("customers")
    if kunden.empty or "name" not in kunden.columns or "email" not in kunden.columns:
        return ""
    ziel = normalize_name(name)
    k = kunden.copy()
    k["_n"] = k["name"].map(normalize_name)
    treffer = k[k["_n"] == ziel]
    if treffer.empty:
        return ""
    wert = str(treffer.iloc[0]["email"])
    return wert if "@" in wert else ""


# ── Nachrichtenvorlagen ───────────────────────────────────────────────────────

def reminder_nachricht(name: str, datum: str, zeit: str = "") -> str:
    vorname = name.split()[0] if " " in name else name
    wann = f"am {datum}" + (f" um {zeit} Uhr" if zeit else "")
    qr = f"\n\n👉 Check-in QR: {QR_LINK}" if QR_LINK else ""
    return f"""🔵 Hey {vorname}!

Du warst {wann} bei uns am Court.

Kurze Sache: dein Wellpass-Check-in ist bei uns noch nicht angekommen. 👀

Kannst du ihn kurz nachholen? Dauert 10 Sekunden.{qr}

Falls es nicht mehr klappt, melde dich einfach — wir finden eine Lösung.

⚡ Once in. Never out.
Dein {CONFIG['name']} Team
{CONFIG['email']}"""


def zweiter_reminder(name: str, datum: str) -> str:
    vorname = name.split()[0] if " " in name else name
    return f"""🔵 Hey {vorname},

kurze Erinnerung zu deinem Besuch am {datum} — der Wellpass-Check-in fehlt
bei uns immer noch. 👀

Wenn du ihn nicht mehr nachholen kannst, berechnen wir eine
Bearbeitungsgebühr von {euro(ADMIN_GEBUEHR)}
(PayPal: {CONFIG['email']}).

Sag einfach kurz Bescheid was dir lieber ist.

⚡ Once in. Never out.
Dein {CONFIG['name']} Team"""


def danke_nachricht(name: str, buchungen: int) -> str:
    vorname = name.split()[0] if " " in name else name
    return f"""🔵 Hey {vorname}!

Kurz zwischendurch: du warst jetzt schon {buchungen}× bei uns am Court. 😏

Genau solche Leute machen den Circle aus. Danke dafür.

Falls du mal jemanden mitbringen willst — sag Bescheid,
wir finden einen Slot.

⚡ Once in. Never out.
Dein {CONFIG['name']} Team"""


def winback_nachricht(name: str, tage_her: int) -> str:
    vorname = name.split()[0] if " " in name else name
    return f"""🔵 Hey {vorname}!

Lange nicht gesehen — {tage_her} Tage, um genau zu sein. 👀

Die Courts stehen, das Licht ist an, und im Circle ist immer
jemand da für ein Match.

Buchen wie gewohnt: {CONFIG['playtomic']}

⚡ Once in. Never out.
Dein {CONFIG['name']} Team"""


# ── Protokoll ─────────────────────────────────────────────────────────────────

def wa_key(name_norm: str, datum: str, betrag) -> str:
    return f"{name_norm}_{datum}_{betrag}"


def whatsapp_loggen(name: str, name_norm: str, datum: str, betrag,
                    nummer: str, art: str = "reminder"):
    log = loadsheet("whatsapp_log", SHEET_SPALTEN["whatsapp_log"])
    key = wa_key(name_norm, datum, betrag)
    neu = pd.DataFrame([{
        "key": key, "name": name, "datum": datum, "betrag": betrag,
        "to_number": nummer, "art": art,
        "timestamp": datetime.now().isoformat(),
    }])
    if not log.empty and "key" in log.columns:
        log = log[log["key"].astype(str) != key]
    savesheet(pd.concat([log, neu], ignore_index=True), "whatsapp_log")
    loadsheet.clear()


def schon_gesendet(name_norm: str, datum: str, betrag):
    log = loadsheet("whatsapp_log", SHEET_SPALTEN["whatsapp_log"])
    if log.empty or "key" not in log.columns:
        return None
    treffer = log[log["key"].astype(str) == wa_key(name_norm, datum, betrag)]
    if treffer.empty:
        return None
    try:
        return datetime.fromisoformat(str(treffer.iloc[0]["timestamp"]))
    except (ValueError, TypeError):
        return None


# ── Modul ─────────────────────────────────────────────────────────────────────

def modul_whatsapp():
    head("WhatsApp Reminder", "Wellpass-Vergesser anschreiben")

    if not twilio_bereit():
        box("Twilio ist noch nicht eingerichtet — es wird nichts versendet. "
            "Du kannst die Nachrichten trotzdem sehen und kopieren, "
            "um sie manuell zu schicken.", "warn")
    if not QR_LINK:
        box("Der Wellpass-QR-Link fehlt in der Konfiguration — "
            "die Nachrichten gehen ohne QR raus.", "info")

    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    t1, t2 = st.tabs(["📬 Offene Fälle", "📜 Protokoll"])

    with t1:
        zeitraum = st.radio("Zeitraum",
                            ["Letzter Tag", "7 Tage", "30 Tage", "Alles"],
                            horizontal=True)
        grenze = {"Letzter Tag": 1, "7 Tage": 7,
                  "30 Tage": 30, "Alles": len(tage)}[zeitraum]
        offen = alle_offenen_fehler(tage[:grenze])

        if offen.empty:
            box("✅ Keine offenen Fälle in diesem Zeitraum.", "ok")
            return

        kunden = loadsheet("customers")
        hat_nummern = not kunden.empty and "phone_number" in kunden.columns

        offen = offen.copy()
        offen["_nummer"] = (offen["Name"].map(telefon_fuer)
                            if hat_nummern else "")
        erreichbar = offen[offen["_nummer"].astype(str).str.len() > 5]

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi("Offene Fälle", str(len(offen)))
        with c2:
            kpi("erreichbar", str(len(erreichbar)), "Nummer hinterlegt")
        with c3:
            kpi("Wert", euro(len(offen) * WELLPASS_WERT), "entgangene Vergütung")

        if not hat_nummern:
            box("Keine Kundenliste mit Nummern hinterlegt — lade sie in der "
                "Daten-Zentrale hoch, dann geht der Versand automatisch.", "warn")

        # ── Sammelversand ───────────────────────────────────────────────
        if twilio_bereit() and not erreichbar.empty:
            st.markdown("---")
            with st.expander(f"⚡ Sammelversand an alle {len(erreichbar)} "
                             "erreichbaren Spieler"):
                box("Sendet an jeden genau eine Nachricht. Bereits "
                    "angeschriebene werden übersprungen.", "info")
                if st.button("Jetzt alle anschreiben", type="primary",
                             use_container_width=True):
                    balken = st.progress(0.0)
                    gesendet = uebersprungen = 0
                    for i, (_, r) in enumerate(erreichbar.iterrows()):
                        balken.progress((i + 1) / len(erreichbar))
                        if schon_gesendet(str(r["Name_norm"]), str(r["Datum"]),
                                          r.get("Betrag", 0)):
                            uebersprungen += 1
                            continue
                        txt = reminder_nachricht(
                            str(r["Name"]), datum_kurz(str(r["Datum"])),
                            str(r.get("Service_Zeit", "")))
                        if whatsapp_senden(f"whatsapp:{r['_nummer']}", txt):
                            whatsapp_loggen(str(r["Name"]), str(r["Name_norm"]),
                                            str(r["Datum"]), r.get("Betrag", 0),
                                            str(r["_nummer"]))
                            gesendet += 1
                        time.sleep(0.4)
                    balken.progress(1.0)
                    st.success(f"✅ {gesendet} gesendet · "
                               f"{uebersprungen} übersprungen")
                    if gesendet:
                        st.balloons()
                    time.sleep(1.2)
                    st.rerun()

        # ── Einzelfälle ─────────────────────────────────────────────────
        st.markdown("---")
        st.caption(f"{len(offen)} Fälle · Namensvarianten lassen sich direkt "
                   "hier zuordnen")

        for i, (_, r) in enumerate(offen.iterrows()):
            name = str(r["Name"])
            nn = str(r["Name_norm"])
            datum = str(r["Datum"])
            betrag = r.get("Betrag", 0)
            zeit = str(r.get("Service_Zeit", "")).strip()
            nummer = str(r["_nummer"])
            mail = email_fuer(name)
            court = str(r.get("Court", "")).strip()
            gesendet = schon_gesendet(nn, datum, betrag)

            kopf = (f'<div class="pc-card"><div class="pc-fall">'
                    f'<div><span class="nm">{name}</span>'
                    f'<span class="mt">&nbsp;· {datum_kurz(datum)}'
                    + (f' · {zeit} Uhr' if zeit else '')
                    + (f' · {court}' if court else '')
                    + '</span></div>'
                    + (f'<div class="ts">📤 {gesendet.strftime("%d.%m. %H:%M")}</div>'
                       if gesendet else '<div class="ts"></div>')
                    + '</div></div>')
            st.markdown(kopf, unsafe_allow_html=True)

            k1, k2 = st.columns(2)
            with k1:
                st.caption(f"📱 {nummer}" if len(nummer) > 5
                           else "📱 keine Nummer hinterlegt")
            with k2:
                st.caption(f"✉️ {mail}" if mail else "✉️ keine E-Mail hinterlegt")

            # ── Zuordnungsvorschlag ─────────────────────────────────────
            vorschlaege = zuordnung_vorschlag(name, datum)
            if vorschlaege:
                bester, bester_norm, score = vorschlaege[0]
                sicherheit = ("lime" if score >= 85
                              else "warn" if score >= 70 else "err")
                st.markdown(
                    f'<div class="pc-vorschlag">Bei EGYM hat '
                    f'<b>{bester}</b> eingecheckt — dieselbe Person? '
                    f'{chip(f"{score:.0f}%", sicherheit)}</div>',
                    unsafe_allow_html=True)

                v1, v2, v3 = st.columns([1.2, 1, 2])
                with v1:
                    if st.button("✓ Ist dieselbe", key=f"wa_zu_{i}",
                                 type="primary", use_container_width=True):
                        mapping_hinzufuegen(nn, bester_norm, score)
                        als_behoben_markieren(nn, datum)
                        cache_leeren()
                        st.success(f"Gemerkt: {name} = {bester}")
                        time.sleep(1)
                        st.rerun()
                with v2:
                    if st.button("✗ Nein", key=f"wa_ab_{i}",
                                 use_container_width=True):
                        rejected_speichern(nn, bester_norm)
                        st.rerun()
                with v3:
                    if len(vorschlaege) > 1:
                        st.caption(f"{len(vorschlaege)-1} weitere Vorschläge "
                                   "unter „Anderen Namen zuordnen“")

            # ── Manuelle Zuordnung ──────────────────────────────────────
            alle_offen = offene_checkins(datum)
            if not alle_offen.empty:
                with st.expander("Anderen Namen zuordnen"):
                    st.caption(f"{len(alle_offen)} Check-ins an diesem Tag ohne "
                               "passende Buchung. Wähle den richtigen aus.")
                    auswahl = st.selectbox(
                        "Check-in", ["—"] + alle_offen["Name"].astype(str).tolist(),
                        key=f"wa_sel_{i}", label_visibility="collapsed")
                    if auswahl != "—":
                        ziel_norm = alle_offen.loc[
                            alle_offen["Name"].astype(str) == auswahl,
                            "Name_norm"].astype(str).iloc[0]
                        if st.button(f"„{auswahl}“ ist {name}",
                                     key=f"wa_man_{i}", type="primary",
                                     use_container_width=True):
                            mapping_hinzufuegen(nn, ziel_norm, 100)
                            als_behoben_markieren(nn, datum)
                            cache_leeren()
                            st.success("Gemerkt.")
                            time.sleep(1)
                            st.rerun()

            # ── Aktionen ────────────────────────────────────────────────
            c1, c2, c3 = st.columns(3)
            with c1:
                kann = len(nummer) > 5 and twilio_bereit()
                if st.button("Senden", key=f"wa_s_{i}", type="primary",
                             use_container_width=True, disabled=not kann):
                    txt = reminder_nachricht(name, datum_kurz(datum), zeit)
                    with st.spinner("Sende…"):
                        if whatsapp_senden(f"whatsapp:{nummer}", txt):
                            whatsapp_loggen(name, nn, datum, betrag, nummer)
                            st.success("✅")
                            time.sleep(.9)
                            st.rerun()
            with c2:
                if st.button("Nachfassen", key=f"wa_n_{i}",
                             use_container_width=True,
                             disabled=not (gesendet and len(nummer) > 5
                                           and twilio_bereit())):
                    txt = zweiter_reminder(name, datum_kurz(datum))
                    with st.spinner("Sende…"):
                        if whatsapp_senden(f"whatsapp:{nummer}", txt):
                            whatsapp_loggen(name, nn, datum, betrag, nummer,
                                            art="nachfassen")
                            st.success("✅")
                            time.sleep(.9)
                            st.rerun()
            with c3:
                if st.button("Erledigt", key=f"wa_e_{i}",
                             use_container_width=True):
                    als_behoben_markieren(nn, datum)
                    st.rerun()

            with st.expander("Nachricht ansehen"):
                st.code(reminder_nachricht(name, datum_kurz(datum), zeit),
                        language=None)

    # ── Protokoll ───────────────────────────────────────────────────────
    with t2:
        log = loadsheet("whatsapp_log", SHEET_SPALTEN["whatsapp_log"])
        if log.empty:
            box("Noch nichts versendet.", "info")
            return

        log = log.copy()
        log["_ts"] = pd.to_datetime(log["timestamp"], errors="coerce")
        log = log.sort_values("_ts", ascending=False)

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi("Gesendet gesamt", str(len(log)))
        with c2:
            letzte7 = int((log["_ts"] >= datetime.now() - timedelta(days=7)).sum())
            kpi("Letzte 7 Tage", str(letzte7))
        with c3:
            arten = log["art"].value_counts().to_dict() if "art" in log.columns else {}
            kpi("Reminder", str(arten.get("reminder", 0)))

        st.markdown("")
        zeig = log[["name", "datum", "art", "timestamp"]].head(100).copy() \
            if "art" in log.columns else log[["name", "datum", "timestamp"]].head(100).copy()
        zeig.columns = ["Spieler", "Spieltag", "Art", "Gesendet"][:len(zeig.columns)]
        st.dataframe(zeig, use_container_width=True, hide_index=True, height=420)


# ══════════════════════════════════════════════════════════════════════════════
#   📋  MODUL · WELLPASS-NACHMELDUNG
# ══════════════════════════════════════════════════════════════════════════════

def nachmeldung_moeglich(checkin_datum: date) -> bool:
    """EGYM nimmt den laufenden Monat + die ersten 3 Tage des Folgemonats."""
    if checkin_datum is None:
        return False
    heute = date.today()
    if (checkin_datum.month, checkin_datum.year) == (heute.month, heute.year):
        return True
    if heute.day <= 3:
        vm = 12 if heute.month == 1 else heute.month - 1
        vj = heute.year - 1 if heute.month == 1 else heute.year
        return (checkin_datum.month, checkin_datum.year) == (vm, vj)
    return False


def nachmeldung_csv(eintraege: list) -> str:
    kopf = ("Vorname;Nachname;E-Mail;Geb-Tag;Geb-Monat;Geb-Jahr;"
            "Checkin-Tag;Checkin-Monat;Checkin-Jahr")
    zeilen = [kopf]
    for e in eintraege:
        ci, gb = e.get("checkin_datum"), e.get("geburtstag")
        ci_t, ci_m, ci_j = ((ci.day, ci.month, ci.year)
                            if isinstance(ci, date) else ("", "", ""))
        gb_t, gb_m, gb_j = ((gb.day, gb.month, gb.year)
                            if isinstance(gb, date) else ("", "", ""))
        zeilen.append(";".join(str(x) for x in [
            e.get("vorname", ""), e.get("nachname", ""), e.get("email", ""),
            gb_t, gb_m, gb_j, ci_t, ci_m, ci_j]))
    return "\n".join(zeilen)


def modul_nachmeldung():
    head("Wellpass-Nachmeldung", "Vergessene Check-ins bei EGYM nachreichen")

    box(f"Zwei Wege wenn jemand den Check-in vergisst:<br><br>"
        f"<b>Weg A · Gebühr</b> — du berechnest {euro(ADMIN_GEBUEHR)} an den Spieler.<br>"
        f"<b>Weg B · Nachmeldung</b> — du reichst bei EGYM nach. Der Spieler zahlt "
        f"nichts, du bekommst trotzdem deine {euro(WELLPASS_WERT)}. "
        f"Geht nur im laufenden Monat (+ 3 Kulanztage).<br><br>"
        f"Weg B ist fast immer besser.", "info")

    if not CONFIG["egym_gym_id"]:
        box("Deine <b>EGYM Gym-ID</b> fehlt in der Konfiguration ganz oben "
            "im Skript. Ohne sie kann der Nachmeldungs-Bot das Formular "
            "nicht ausfüllen.", "warn")

    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    # ── Kandidaten ──────────────────────────────────────────────────────
    kandidaten = []
    for tag in tage:
        try:
            td = datetime.strptime(tag, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not nachmeldung_moeglich(td):
            continue
        for _, r in offene_fehler(tag).iterrows():
            kandidaten.append({"name": str(r["Name"]),
                               "name_norm": str(r["Name_norm"]),
                               "datum": td})

    if not kandidaten:
        box("Keine nachmeldbaren Fälle. Entweder ist alles sauber, oder die "
            f"offenen Fälle liegen ausserhalb der EGYM-Frist — die laufen dann "
            f"über die Gebühr ({euro(ADMIN_GEBUEHR)}).", "ok")
        return

    c1, c2 = st.columns(2)
    with c1:
        kpi("Nachmeldbar", str(len(kandidaten)), "innerhalb der EGYM-Frist")
    with c2:
        kpi("Wert", euro(len(kandidaten) * WELLPASS_WERT),
            "wenn EGYM bestätigt")

    st.markdown("---")
    st.markdown("##### Daten ergänzen")
    st.caption("EGYM braucht E-Mail und Geburtsdatum. Wenn beides in deiner "
               "Kundenliste steht, füllt die App es vor.")

    kunden = loadsheet("customers")
    hat_kunden = not kunden.empty and "name" in kunden.columns
    if hat_kunden:
        kunden = kunden.copy()
        kunden["_n"] = kunden["name"].map(normalize_name)

    eintraege = []
    for i, k in enumerate(kandidaten):
        vn_vor, nn_vor = split_name(k["name"])
        mail_vor, gb_vor = "", None

        if hat_kunden:
            tr = kunden[kunden["_n"] == k["name_norm"]]
            if not tr.empty:
                m = str(tr.iloc[0].get("email", ""))
                mail_vor = m if "@" in m else ""
                gb_vor = parse_date_safe(tr.iloc[0].get("geburtstag"))

        vollstaendig = bool(mail_vor and gb_vor)
        with st.expander(f"{'✅' if vollstaendig else '○'}  {k['name']}  ·  "
                         f"{k['datum'].strftime('%d.%m.%Y')}"):
            aktiv = st.checkbox("In Export aufnehmen", value=vollstaendig,
                                key=f"nm_a_{i}")
            c1, c2 = st.columns(2)
            with c1:
                vn = st.text_input("Vorname", value=vn_vor, key=f"nm_v_{i}")
                mail = st.text_input("E-Mail", value=mail_vor, key=f"nm_m_{i}",
                                     placeholder="name@example.com")
            with c2:
                nn = st.text_input("Nachname", value=nn_vor, key=f"nm_n_{i}")
                gb = st.date_input("Geburtsdatum", value=gb_vor, key=f"nm_g_{i}",
                                   min_value=date(1930, 1, 1),
                                   max_value=date.today(), format="DD.MM.YYYY")
            st.caption(f"Check-in-Datum: {k['datum'].strftime('%d.%m.%Y')}")

            if aktiv:
                if not mail or not gb:
                    st.caption("⚠️ E-Mail und Geburtsdatum fehlen — "
                               "EGYM lehnt sonst ab.")
                else:
                    eintraege.append({"vorname": vn, "nachname": nn,
                                      "email": mail, "geburtstag": gb,
                                      "checkin_datum": k["datum"]})

    st.markdown("---")
    if not eintraege:
        box("Noch keine vollständigen Einträge.", "info")
        return

    csv_text = nachmeldung_csv(eintraege)
    c1, c2 = st.columns(2)
    with c1:
        kpi("Bereit", str(len(eintraege)), "vollständige Einträge")
    with c2:
        kpi("Wert", euro(len(eintraege) * WELLPASS_WERT))

    st.markdown("")
    st.download_button("⬇️ CSV für den Nachmeldungs-Bot",
                       data=csv_text.encode("utf-8-sig"),
                       file_name=f"nachmeldung_{date.today()}.csv",
                       mime="text/csv", type="primary",
                       use_container_width=True)

    with st.expander("Vorschau"):
        st.code(csv_text, language=None)

    with st.expander("Bot-Konfiguration (einmalig eintragen)"):
        st.code(f'''HALLE = {{
    "gym_id":      "{CONFIG['egym_gym_id'] or 'DEINE_GYM_ID'}",
    "einrichtung": "{CONFIG['egym_einrichtung']}",
    "adresse":     "{CONFIG['adresse']}",
    "stadt":       "{CONFIG['stadt']}",
    "plz":         "{CONFIG['plz']}",
    "land":        "{CONFIG['land']}",
    "grund":       "Durchgelaufen ohne einzuchecken",
}}''', language="python")
        st.caption("Danach im Terminal: "
                   f"`python3 wellpass_nachmeldung_bot.py nachmeldung_{date.today()}.csv`")


# ══════════════════════════════════════════════════════════════════════════════
#   🔗  MODUL · NAME-MATCHING
# ══════════════════════════════════════════════════════════════════════════════

def modul_matching():
    head("Name-Abgleich", "Playtomic ↔ Wellpass zusammenführen")

    box("Playtomic und EGYM schreiben Namen oft unterschiedlich — "
        "„M. Sidorov“ hier, „Marcel Sidorov“ dort. Dann meldet die App fälschlich "
        "einen fehlenden Check-in. Hier bestätigst du die Zuordnung einmal, "
        "danach erkennt die App sie automatisch.", "info")

    t1, t2 = st.tabs(["🔍 Vorschläge", "📚 Gelernte Zuordnungen"])

    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()

    # ── Vorschläge ──────────────────────────────────────────────────────
    with t1:
        tage = verfuegbare_tage()
        if not tage:
            box("Noch keine Daten.", "warn")
            return

        anzahl_tage = st.slider("Wie viele Tage prüfen?", 1,
                                min(60, len(tage)), min(14, len(tage)))
        ziel_tage = tage[:anzahl_tage]

        checkins = loadsheet("checkins")
        vorschlaege = []

        for tag in ziel_tage:
            fehler = offene_fehler(tag)
            if fehler.empty:
                continue
            tag_checkins = checkins[
                (checkins["analysis_date"].astype(str) == tag) &
                (checkins["Gespielt"].astype(str) == "Nein")
            ] if not checkins.empty and "analysis_date" in checkins.columns \
                else pd.DataFrame()

            if tag_checkins.empty:
                continue
            kandidaten = tag_checkins["Name_norm"].astype(str).tolist()
            namen_anzeige = dict(zip(tag_checkins["Name_norm"].astype(str),
                                     tag_checkins["Name"].astype(str)))

            for _, r in fehler.iterrows():
                treffer = fuzzy_match(str(r["Name_norm"]), kandidaten,
                                      mapping, abgelehnt)
                if treffer:
                    best, score, quelle = treffer[0]
                    if quelle != "gelernt":
                        vorschlaege.append({
                            "buchung": str(r["Name"]),
                            "buchung_norm": str(r["Name_norm"]),
                            "checkin": namen_anzeige.get(best, best),
                            "checkin_norm": best,
                            "score": score, "tag": tag,
                        })

        if not vorschlaege:
            box("✅ Keine offenen Zuordnungs-Vorschläge. Entweder passt alles, "
                "oder es gibt keine unzugeordneten Check-ins.", "ok")
            return

        box(f"<b>{len(vorschlaege)} Vorschläge</b> gefunden. "
            "Bestätigen heisst: die App merkt sich das dauerhaft.", "info")

        for i, v in enumerate(vorschlaege):
            sicherheit = ("lime" if v["score"] >= 85
                          else "warn" if v["score"] >= 70 else "err")
            st.markdown(f"""
            <div class="pc-card">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;">
                <div>
                  <span style="color:{C['dim']};font-size:.78rem;">
                    Playtomic</span><br>
                  <span style="font-weight:600;color:{C['text']};">
                    {v['buchung']}</span>
                </div>
                <div style="font-size:1.3rem;color:{C['volt']};">↔</div>
                <div style="text-align:right;">
                  <span style="color:{C['dim']};font-size:.78rem;">
                    Wellpass</span><br>
                  <span style="font-weight:600;color:{C['text']};">
                    {v['checkin']}</span>
                </div>
                <div>{chip(f"{v['score']:.0f}%", sicherheit)}</div>
              </div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("✓ Ist dieselbe Person", key=f"mm_ok_{i}",
                             type="primary", use_container_width=True):
                    mapping_hinzufuegen(v["buchung_norm"], v["checkin_norm"],
                                        v["score"])
                    cache_leeren()
                    st.success("Gemerkt.")
                    time.sleep(.7)
                    st.rerun()
            with c2:
                if st.button("✗ Nicht dieselbe", key=f"mm_no_{i}",
                             use_container_width=True):
                    rejected_speichern(v["buchung_norm"], v["checkin_norm"])
                    st.rerun()
            with c3:
                st.caption(f"Spieltag {datum_kurz(v['tag'])}")

        box("Nach dem Bestätigen musst du die betroffenen Tage einmal neu "
            "verarbeiten (Daten-Zentrale), damit die Zuordnung rückwirkend greift.",
            "info")

    # ── Gelernte ────────────────────────────────────────────────────────
    with t2:
        if not mapping:
            box("Noch keine Zuordnungen gelernt.", "info")
        else:
            st.caption(f"{len(mapping)} gespeicherte Zuordnungen")
            for i, (buchung, details) in enumerate(mapping.items()):
                ziel = (details["checkin_name"] if isinstance(details, dict)
                        else details)
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"<div class='pc-row'>"
                                f"<span class='nm'>{buchung}</span>"
                                f"<span class='mt'>↔ {ziel}</span></div>",
                                unsafe_allow_html=True)
                with c2:
                    if st.button("Löschen", key=f"mm_del_{i}",
                                 use_container_width=True):
                        mapping_entfernen(buchung)
                        cache_leeren()
                        st.rerun()

        if abgelehnt:
            st.markdown("---")
            st.caption(f"{len(abgelehnt)} abgelehnte Vorschläge")
            with st.expander("Abgelehnte anzeigen"):
                for i, (b, c) in enumerate(sorted(abgelehnt)):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.caption(f"{b} ↮ {c}")
                    with c2:
                        if st.button("Zurücknehmen", key=f"mm_rej_{i}",
                                     use_container_width=True):
                            rejected_entfernen(b, c)
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#   ⚙️  MODUL · EINSTELLUNGEN
# ══════════════════════════════════════════════════════════════════════════════

def modul_einstellungen():
    head("Einstellungen", "Ziele · Konfiguration · System")

    t1, t2, t3 = st.tabs(["🎯 Ziele", "🔍 Suche", "🩺 System"])

    # ── Ziele ───────────────────────────────────────────────────────────
    with t1:
        st.markdown("##### Monatsziel")
        st.caption("Gilt als Standard für alle Monate. Einzelne Monate kannst "
                   "du darunter überschreiben.")

        aktuell = monatsziel()
        neu = st.number_input("Standard-Monatsziel (€)", min_value=0.0,
                              value=float(aktuell), step=500.0, format="%.0f")
        if st.button("Speichern", type="primary"):
            einstellung_setzen("monatsziel", neu)
            st.success("Gespeichert.")
            time.sleep(.7)
            st.rerun()

        st.markdown("---")
        st.markdown("##### Ziel für einen bestimmten Monat")
        tage = verfuegbare_tage()
        monate = sorted({t[:7] for t in tage}, reverse=True) if tage else []
        if monate:
            m = st.selectbox("Monat", monate,
                             format_func=lambda x: f"{MONATE_DE[int(x[5:7])-1]} {x[:4]}")
            m_ziel = st.number_input("Ziel für diesen Monat (€)",
                                     min_value=0.0, value=float(monatsziel(m)),
                                     step=500.0, format="%.0f", key="m_ziel")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Für diesen Monat speichern", use_container_width=True):
                    einstellung_setzen(f"monatsziel_{m}", m_ziel)
                    st.success("Gespeichert.")
                    time.sleep(.7)
                    st.rerun()
            with c2:
                if st.button("Auf Standard zurücksetzen", use_container_width=True):
                    einstellung_setzen(f"monatsziel_{m}", None)
                    st.success("Zurückgesetzt.")
                    time.sleep(.7)
                    st.rerun()

    # ── Suche ───────────────────────────────────────────────────────────
    with t2:
        st.markdown("##### Spieler suchen")
        suche = st.text_input("Name", placeholder="z.B. Mustermann",
                              label_visibility="collapsed")
        if suche and len(suche) >= 2:
            b = loadsheet("buchungen")
            if b.empty or "Name" not in b.columns:
                box("Keine Daten.", "warn")
            else:
                treffer = b[b["Name"].astype(str).str.contains(
                    suche, case=False, na=False)]
                if treffer.empty:
                    box(f"Nichts gefunden für „{suche}“.", "info")
                else:
                    namen = treffer["Name"].unique()
                    box(f"{len(treffer)} Buchungen von {len(namen)} Spielern.", "ok")

                    stat = spieler_statistik()
                    for nm in namen[:10]:
                        srow = stat[stat["Name"] == nm]
                        if srow.empty:
                            continue
                        s = srow.iloc[0]
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            kpi("Spieler", str(nm))
                        with c2:
                            kpi("Buchungen", str(int(s["buchungen"])))
                        with c3:
                            kpi("Umsatz", euro(s["umsatz"]))
                        with c4:
                            kpi("Zuletzt", f"vor {int(s['tage_her'])} T.")

                        with st.expander(f"Alle Buchungen von {nm}"):
                            sp = [c for c in ["analysis_date", "Service_Zeit",
                                              "Betrag", "Check-in", "Fehler"]
                                  if c in treffer.columns]
                            z = treffer[treffer["Name"] == nm][sp].copy()
                            z.columns = [{"analysis_date": "Datum",
                                          "Service_Zeit": "Zeit"}.get(c, c)
                                         for c in sp]
                            st.dataframe(z.sort_values("Datum", ascending=False),
                                         use_container_width=True, hide_index=True)

    # ── System ──────────────────────────────────────────────────────────
    with t3:
        st.markdown("##### Verbindungen")

        pruefungen = [
            ("Google Sheet", get_sheet() is not None,
             "Datenbank erreichbar"),
            ("Twilio / WhatsApp", twilio_bereit(),
             "Versand möglich"),
            ("EGYM Gym-ID", bool(CONFIG["egym_gym_id"]),
             "für Nachmeldungen nötig"),
            ("Wellpass QR-Link", bool(CONFIG["wellpass_qr_link"]),
             "für Reminder-Nachrichten"),
            ("Kundenliste", not loadsheet("customers").empty,
             "Telefonnummern für WhatsApp"),
        ]
        for name, ok_status, hinweis in pruefungen:
            symbol = "✅" if ok_status else "⚠️"
            farbe = C["ok"] if ok_status else C["warn"]
            st.markdown(f"""
            <div class="pc-row">
              <div><span class="nm">{symbol} {name}</span>
                   <span class="mt">&nbsp;· {hinweis}</span></div>
              <div style="color:{farbe};font-weight:600;font-size:.8rem;">
                {'bereit' if ok_status else 'offen'}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### Aktuelle Konfiguration")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("**Wellpass-Vergütung**")
            st.markdown(f"{euro(CONFIG['wellpass_brutto'])} × "
                        f"{CONFIG['wellpass_anteil']*100:.0f} % = "
                        f"**{euro(WELLPASS_WERT)}** pro Check-in")
            st.caption("**Bearbeitungsgebühr**")
            st.markdown(f"**{euro(ADMIN_GEBUEHR)}** bei vergessenem Check-in")
        with c2:
            st.caption("**Court-Preise (60 Min)**")
            st.markdown(f"""
Double 6–12 Uhr · **{euro(CONFIG['preis_double_frueh'])}**
Double 12–16 Uhr · **{euro(CONFIG['preis_double_mittag'])}**
Double ab 16 / WE · **{euro(CONFIG['preis_double_prime'])}**
Single bis 16 Uhr · **{euro(CONFIG['preis_single_tag'])}**
Single ab 16 / WE · **{euro(CONFIG['preis_single_prime'])}**
""")

        st.markdown("---")
        st.markdown("##### Wartung")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Alle Caches leeren", use_container_width=True):
                cache_leeren()
                st.success("Geleert.")
                time.sleep(.7)
                st.rerun()
        with c2:
            st.caption(f"{CONFIG['firma']} · {CONFIG['hrb']}")
            st.caption(f"USt-IdNr. {CONFIG['ust_id']}")


# ══════════════════════════════════════════════════════════════════════════════
#   🏠  COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════

MODULE = [
    {"id": "daten",     "ic": "📦", "ti": "Daten-Zentrale",
     "de": "Playtomic & Wellpass hochladen", "an": True, "fn": lambda: modul_daten()},
    {"id": "dashboard", "ic": "📊", "ti": "Business Dashboard",
     "de": "Umsatz, Auslastung, Prognose", "an": True, "fn": lambda: modul_dashboard()},
    {"id": "whatsapp",  "ic": "💬", "ti": "WhatsApp Reminder",
     "de": "Wellpass-Vergesser anschreiben", "an": True, "fn": lambda: modul_whatsapp()},
    {"id": "spieler",   "ic": "👥", "ti": "Spieler & Community",
     "de": "Rangliste, Vielspieler, Rückholung", "an": True, "fn": lambda: modul_spieler()},
    {"id": "nachmeldung", "ic": "📋", "ti": "Wellpass-Nachmeldung",
     "de": "Check-ins bei EGYM nachreichen", "an": True, "fn": lambda: modul_nachmeldung()},
    {"id": "matching",  "ic": "🔗", "ti": "Name-Abgleich",
     "de": "Playtomic ↔ Wellpass zusammenführen", "an": True, "fn": lambda: modul_matching()},
    {"id": "einstellungen", "ic": "⚙️", "ti": "Einstellungen",
     "de": "Ziele, Suche, Systemcheck", "an": True, "fn": lambda: modul_einstellungen()},
    {"id": "rechnungen", "ic": "🧾", "ti": "Rechnungen",
     "de": "Bearbeitungsgebühr automatisch", "an": False, "fn": None},
    {"id": "events",    "ic": "🗓", "ti": "Events",
     "de": "Mexicano, Coaching, Ladies Day", "an": False, "fn": None},
]


def _kachel_badge(modul, offen_gesamt: int) -> str:
    if not modul["an"]:
        return '<div class="bg muted">bald</div>'
    if modul["id"] == "whatsapp" and offen_gesamt:
        return f'<div class="bg alert">{offen_gesamt} offen</div>'
    if modul["id"] == "daten" and not verfuegbare_tage():
        return '<div class="bg alert">Start hier</div>'
    return '<div class="bg">live</div>'


def command_center():
    head(CONFIG["name"], "Command Center")

    offen_cfg = offene_config()
    if offen_cfg:
        box("Noch auszufüllen in der Konfiguration (oben im Skript): "
            f"<b>{', '.join(offen_cfg)}</b>. Die App läuft auch ohne — "
            "betroffene Funktionen sind eingeschränkt.", "warn")

    tage = verfuegbare_tage()
    offen_gesamt = 0

    if tage:
        k = tages_kennzahlen(tage[0])
        offen_df = alle_offenen_fehler(tage[:7])
        offen_gesamt = len(offen_df)
        serie = sauber_serie(tage)

        monat_akt = tage[0][:7]
        mk = monats_kennzahlen(monat_akt)
        ziel = monatsziel(monat_akt)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi("Letzter Spieltag", datum_kurz(tage[0]),
                WOCHENTAGE_DE[datetime.strptime(tage[0], "%Y-%m-%d").weekday()])
        with c2:
            kpi("Umsatz Tag", euro(k["gesamt_effektiv"]), "inkl. Wellpass")
        with c3:
            kpi("Monat bisher", euro(mk["gesamt_effektiv"]),
                f"{MONATE_DE[int(monat_akt[5:7])-1]}")
        with c4:
            kpi("Offene Fälle", str(offen_gesamt), "letzte 7 Tage")

        st.markdown("")
        c1, c2 = st.columns([1.2, 1])
        with c1:
            if ziel > 0:
                erreicht = prozent(mk["gesamt_effektiv"], ziel)
                rest = max(0.0, ziel - mk["gesamt_effektiv"])
                fortschritts_ring(
                    erreicht, f"{erreicht:.0f}%",
                    f"Monatsziel {MONATE_DE[int(monat_akt[5:7])-1]}",
                    (f"{euro(mk['gesamt_effektiv'])} von {euro(ziel)}<br>"
                     + (f"noch {euro(rest)}" if rest > 0
                        else "Ziel erreicht 🎉")))
        with c2:
            if serie >= 2:
                streak_banner(serie)
            elif offen_gesamt:
                box(f"⚠️ {offen_gesamt} Spieler ohne Check-in — "
                    f"{euro(offen_gesamt * WELLPASS_WERT)} liegen auf der Strasse.",
                    "warn")

        st.markdown("")

    # ── Kacheln ─────────────────────────────────────────────────────────
    for start in range(0, len(MODULE), 3):
        spalten = st.columns(3)
        for sp, modul in zip(spalten, MODULE[start:start + 3]):
            with sp:
                st.markdown(f"""
                <div class="pc-tile {'soon' if not modul['an'] else ''}">
                  {_kachel_badge(modul, offen_gesamt)}
                  <div class="ic">{modul['ic']}</div>
                  <div class="ti">{modul['ti']}</div>
                  <div class="de">{modul['de']}</div>
                </div>""", unsafe_allow_html=True)

                if modul["an"]:
                    if st.button("Öffnen", key=f"tile_{modul['id']}",
                                 use_container_width=True):
                        st.session_state.modul = modul["id"]
                        st.rerun()
                else:
                    st.button("Bald", key=f"soon_{modul['id']}",
                              use_container_width=True, disabled=True)
        st.markdown("")


# ══════════════════════════════════════════════════════════════════════════════
#   ▶️  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(page_title=f"{CONFIG['name']} · Command Center",
                       page_icon="🔵", layout="wide",
                       initial_sidebar_state="collapsed")
    css_laden()

    if not login():
        st.stop()

    st.session_state.setdefault("modul", None)
    st.session_state.setdefault("name_mapping_cache", None)

    # ── Sidebar ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:1rem 0 1.4rem;">
          <div style="width:72px;margin:0 auto;color:{C['volt']};">{LOGO_SVG}</div>
          <div style="margin-top:.7rem;font-size:.62rem;letter-spacing:.2em;
                      color:{C['dim']};font-weight:600;">COMMAND CENTER</div>
        </div>""", unsafe_allow_html=True)

        if st.button("🏠 Übersicht", use_container_width=True):
            st.session_state.modul = None
            st.rerun()

        st.markdown("---")
        for modul in MODULE:
            if not modul["an"]:
                continue
            if st.button(f"{modul['ic']}  {modul['ti']}",
                         key=f"nav_{modul['id']}", use_container_width=True):
                st.session_state.modul = modul["id"]
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Abmelden", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

        st.caption(CONFIG["firma"])
        st.caption(f"{COURTS_GESAMT} Courts · {CONFIG['stadt']}")

    # ── Inhalt ──────────────────────────────────────────────────────────
    aktiv = st.session_state.modul
    if aktiv is None:
        command_center()
    else:
        modul = next((m for m in MODULE if m["id"] == aktiv), None)
        if modul and modul["fn"]:
            if st.button("← Übersicht"):
                st.session_state.modul = None
                st.rerun()
            modul["fn"]()
        else:
            st.session_state.modul = None
            st.rerun()

    claim_line()


if __name__ == "__main__":
    main()
