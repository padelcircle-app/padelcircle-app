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
from gspread.utils import numericise
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
    # Welche Court-Nummern sind Einzelcourts? Playtomic benennt
    # denselben Court mal "Single Court Padel 6", mal nur "Padel 6".
    "single_court_nummern": [6],
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
    "wellpass_brutto":     12.00,    # aktueller Satz
    "wellpass_anteil":      0.95,
    # EGYM hat den Satz gesenkt. Alte Monate müssen weiter mit dem alten
    # Satz gerechnet werden, sonst stimmt rückwirkend keine Zahl mehr.
    # Aufsteigend nach Datum, "ab" gilt einschliesslich.
    "wellpass_saetze": [
        {"ab": "2000-01-01", "brutto": 13.00},
        {"ab": "2026-08-04", "brutto": 12.00},
    ],
    # Was Playtomic pro Wellpass-Spieler vom Platzpreis abzieht.
    # NICHT dasselbe wie wellpass_brutto — das ist die Vergütung von EGYM.
    # Der Abzug hat sich im Betrieb schon geändert (13,00 € → 12,00 €),
    # deshalb einstellbar und mit Selbsterkennung.
    "wellpass_abzug":      12.00,
    # Ab wann Playtomic wie viel abzieht. WICHTIG: massgeblich ist der
    # Tag der BUCHUNG, nicht der Spieltag. Man kann zwei Wochen im
    # Voraus buchen — nach einer Umstellung laufen also noch Wochen
    # später Buchungen mit dem alten Rabatt ein. Deshalb wird der Wert
    # des Spieltags nur bevorzugt, der andere bleibt als Möglichkeit.
    "wellpass_abzug_saetze": [
        {"ab": "2000-01-01", "abzug": 13.00},
        {"ab": "2026-08-04", "abzug": 12.00},
    ],
    "wellpass_abzug_alternativen": [13.00, 12.00, 13.50, 11.00],
    "admin_gebuehr":       15.00,   # Gebühr wenn Check-in vergessen wurde
    # Wie viele Tage nach dem Spiel darf ein Check-in nachgeholt werden?
    "nachhol_fenster_tage": 5,
    # Für gesperrte Spieler gilt ein weiteres Fenster: Wer gesperrt ist,
    # meldet sich oft erst Wochen später — mit fünf Tagen fände man den
    # nachgeholten Check-in nie.
    "sperre_nachhol_fenster_tage": 90,
    # Wie weit zurück werden überzählige Check-ins angezeigt?
    "ueberzaehlig_rueckblick_tage": 40,

    "egym_gym_id":         "1042620",                          # ← AUSFÜLLEN
    "egym_einrichtung":    "Padel Circle Memmingen",    # ← PRÜFEN (exakt wie bei EGYM)
    "wellpass_qr_link":    "https://cdn.jsdelivr.net/gh/padelcircle-app/padelcircle-assets/wellpass.jpg",                          # ← AUSFÜLLEN nach QR-Hosting

    # ── Wellpass-Erkennung ───────────────────────────────────────────────────
    # Wer einen Wellpass-Rabatt bekam, musste einchecken.
    # Double 28–36 € ÷ 4 Spieler = 7–9 € pro Kopf → alles unter 7 € ist Zuzahlung.
    "wellpass_zuzahlung_max":  7.0,
    "single_payer_min":       20.0,   # Zahlt einer ≥ 20 €, zahlt er für die Gruppe
    "standard_dauer_minuten": 90,     # falls der Export keine Dauer liefert

    # ── Ziele ────────────────────────────────────────────────────────────────
    "monatsziel_default":  12000.0,   # € — im Modul Einstellungen änderbar

    # ── Team: zählt nicht als Kunde, bekommt keine Reminder ──────────────────
    "mitarbeiter": [
        "Marcel Sidorov",
        "Mattia Mauta",
        "Mattia Niklas Mauta",
        "Playtomic",
        # ← ERGÄNZEN: Trainer, Aushilfen
    ],

    # ── Familie / Dauergäste ohne Wellpass-Pflicht ───────────────────────────
    "immer_gruen": [
        "Marcel Sidorov",
        "Mattia Mauta",
        "Mattia Niklas Mauta",
        "Bernd Schelenz",
        "Андрей Миллер",      # eigener Benefit — spielt dauerhaft kostenlos
        "Andrey Miller",
        # ← ERGÄNZEN
    ],
}

# ── Platzhalter statt echter Namen ───────────────────────────────────────────
#
# Playtomic füllt nicht besetzte Plätze mit „Player 2", „Player 3" …
# Das sind keine Menschen: sie haben keine Nummer, keine E-Mail, keinen
# Wellpass und können nichts nachholen. Sie dürfen deshalb weder als Fall
# auftauchen noch als Rabattträger gelten.
#
# Die Liste stand vorher nur mit den deutschen Varianten in „mitarbeiter" —
# Playtomic schreibt aber englisch. Deshalb tauchten Player 2 bis 4 als
# Fälle auf, obwohl es sie gar nicht gibt.
PLATZHALTER_MUSTER = re.compile(
    r"^(player|spieler|guest|gast|visitor|besucher|teilnehmer|participant)"
    r"[\s._-]*\d*$", re.IGNORECASE)


def ist_platzhalter(name) -> bool:
    """Ist das ein von Playtomic erzeugter Platzhalter statt einer Person?"""
    text = str(name or "").strip()
    if not text:
        return True
    return bool(PLATZHALTER_MUSTER.match(text))


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

WELLPASS_WERT   = round(CONFIG["wellpass_brutto"] * CONFIG["wellpass_anteil"], 2)


def wellpass_saetze() -> list:
    """Satz-Historie, aufsteigend nach Datum. Über Einstellungen änderbar."""
    roh = einstellung("wellpass_saetze", CONFIG["wellpass_saetze"])
    saetze = []
    if isinstance(roh, (list, tuple)):
        for x in roh:
            if not isinstance(x, dict):
                continue
            try:
                ab, brutto = str(x["ab"]), float(x["brutto"])
            except (KeyError, TypeError, ValueError):
                continue
            if ab and brutto > 0:
                saetze.append({"ab": ab, "brutto": brutto})
    if not saetze:
        saetze = list(CONFIG["wellpass_saetze"])
    return sorted(saetze, key=lambda x: x["ab"])


def wellpass_brutto_am(datum) -> float:
    """Was EGYM an diesem Tag pro Check-in zahlt."""
    tag = str(datum)[:10]
    gueltig = CONFIG["wellpass_brutto"]
    for satz in wellpass_saetze():
        if tag >= satz["ab"]:
            gueltig = satz["brutto"]
        else:
            break
    return float(gueltig)


def wellpass_wert_am(datum) -> float:
    """Was davon bei dir ankommt — 95 %."""
    return round(wellpass_brutto_am(datum) * CONFIG["wellpass_anteil"], 2)


def wellpass_wert_summe(datumsliste) -> float:
    """Summe über mehrere Tage, jeder mit dem Satz seiner Zeit."""
    return round(sum(wellpass_wert_am(d) for d in datumsliste), 2)
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


# ── Warum ein Fall erledigt ist ───────────────────────────────────────────────
#
#   Bewusst einfach: zwei Gründe, die man selbst auswählt — Bezahlt oder
#   Gesperrt. Keine Bilanz-Rechnung dahinter, nur zum Nachvollziehen und
#   Zählen (z.B. wie oft jemand schon gesperrt wurde). "Nachgeholt" setzt
#   nicht der Nutzer, sondern die Nachholungs-Zuordnung automatisch, wenn
#   ein späterer Check-in einen alten Fall erklärt.
#
ERLEDIGT_GRUENDE = {
    "bezahlt": {
        "label": "Bezahlt",
        "kurz":  "Bezahlt",
        "icon":  "💶",
        "hilfe": "Hat die Bearbeitungsgebühr bezahlt (PayPal, Überweisung, bar).",
    },
    "gesperrt": {
        "label": "Gesperrt",
        "kurz":  "Gesperrt",
        "icon":  "🔒",
        "hilfe": "Wellpass-Zugang gesperrt.",
    },
    "nachgeholt": {
        "label": "Check-in nachgeholt",
        "kurz":  "Nachgeholt",
        "icon":  "🔄",
        "hilfe": "EGYM vergütet nachträglich — wird automatisch gesetzt, "
                 "wenn ein späterer Check-in zugeordnet wird.",
    },
}

GRUND_UNBEKANNT = {
    "label": "Ohne Grund erfasst", "kurz": "Ohne Grund", "icon": "❔",
    "hilfe": "Als erledigt markiert, ohne einen Grund auszuwählen.",
}


def grund_info(schluessel) -> dict:
    """Zu einem gespeicherten Grund die Beschreibung holen."""
    return ERLEDIGT_GRUENDE.get(str(schluessel).strip(), GRUND_UNBEKANNT)


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
    s = str(val).strip()
    # Währungsangaben entfernen: "36 EUR", "36€", "EUR 36"
    s = re.sub(r"(?i)\b(eur|euro|usd|chf)\b", "", s)
    s = s.replace("€", "").replace("$", "").replace("\xa0", "")
    s = re.sub(r"[^\d,.\-+]", "", s).strip()
    if not s or s in ("-", "+", ".", ","):
        return 0.0
    if "," in s and "." in s:
        # Das hintere Zeichen ist der Dezimaltrenner
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
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


def prozent_text(teil, ganz) -> str:
    """„7 von 9 · 78 %" — für Kennzahlen mit Bezugsgrösse."""
    if not ganz:
        return "keine Bezugsgrösse"
    return f"{int(teil)} von {int(ganz)} · {prozent(teil, ganz):.0f} %"


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
    "corrections":      ["key", "date", "behoben", "grund", "betrag", "notiz",
                         "timestamp"],
    "whatsapp_log":     ["key", "name", "datum", "betrag", "to_number", "art", "timestamp"],
    "name_mapping":     ["buchung_name", "checkin_name", "confidence", "timestamp", "confirmed_by"],
    "rejected_matches": ["buchung_name", "checkin_name", "timestamp"],
    "nachmeldungen":    ["name", "email", "geburtstag", "checkin_datum", "status", "timestamp"],
    "checkin_zuordnung": ["checkin_key", "fall_key", "checkin_datum",
                          "checkin_name", "fall_datum", "fall_name", "timestamp"],
    "freigaben":        ["name_norm", "name", "ausgeloest_am", "letzte_sperre",
                         "bestaetigt", "timestamp"],
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
def alle_blaetter() -> dict:
    """
    Alle Tabellenblätter in EINEM Google-Aufruf.

    Vorher holte jedes loadsheet() sein Blatt einzeln — und weil gspread
    für worksheet(name) jedes Mal die Mappenstruktur mitlädt, waren das
    zwei Anfragen pro Blatt. Bei zwölf Blättern also rund 24 Anfragen,
    jedes Mal wenn der Cache geleert wurde. Genau daran lief das
    Google-Limit auf.

    Jetzt: eine Anfrage für die Struktur, eine für alle Werte.

    Wichtig: Bei einem Fehler wird eine Ausnahme ausgelöst statt leerer
    Daten. Sonst hätte ein kurzzeitiges Limit eine leere Tabelle für
    30 Minuten in den Cache gebrannt — die App hätte behauptet, es gäbe
    keine Daten.
    """
    sheet = get_sheet()
    if sheet is None:
        return {}

    letzter_fehler = None
    for versuch in range(3):
        try:
            # Alle vorhandenen Blätter holen. Die vier grossen —
            # buchungen, checkins, customers, playtomic_raw — entstehen
            # erst beim Import und stehen deshalb nicht in SHEET_SPALTEN.
            gesucht = [ws.title for ws in sheet.worksheets()]
            if not gesucht:
                return {}

            antwort = sheet.values_batch_get(gesucht)
            bereiche = antwort.get("valueRanges", [])

            blaetter = {}
            for name, bereich in zip(gesucht, bereiche):
                zeilen = bereich.get("values", [])
                blaetter[name] = _zu_dataframe(zeilen)
            return blaetter

        except Exception as e:
            letzter_fehler = e
            if "429" in str(e) or "quota" in str(e).lower():
                time.sleep(3 + versuch * 4)
            else:
                break

    raise RuntimeError(f"Google-Abruf fehlgeschlagen: {letzter_fehler}")


def _zu_dataframe(zeilen: list) -> pd.DataFrame:
    """Rohwerte aus der Tabelle in einen DataFrame — wie get_all_records."""
    if not zeilen:
        return pd.DataFrame()
    kopf = [str(c).strip() for c in zeilen[0]]
    if not kopf:
        return pd.DataFrame()

    breite = len(kopf)
    daten = []
    for zeile in zeilen[1:]:
        # Google lässt leere Zellen am Zeilenende weg — auffüllen
        gefuellt = list(zeile) + [""] * (breite - len(zeile))
        daten.append([numericise(w) for w in gefuellt[:breite]])

    return pd.DataFrame(daten, columns=kopf) if daten \
        else pd.DataFrame(columns=kopf)


def loadsheet(name: str, cols=None) -> pd.DataFrame:
    """Ein Tabellenblatt aus dem gemeinsamen Abruf holen."""
    leer = pd.DataFrame(columns=cols) if cols else pd.DataFrame()
    try:
        blaetter = alle_blaetter()
    except Exception:
        # Nicht gecacht — beim nächsten Durchlauf wird neu versucht.
        # Die Meldung nur einmal pro Seitenaufbau zeigen, sonst steht
        # sie zwanzigmal untereinander.
        if not st.session_state.get("_limit_gemeldet"):
            st.session_state["_limit_gemeldet"] = True
            st.warning("⚠️ Google antwortet gerade nicht — kurz warten "
                       "und die Seite neu laden.")
        return leer

    df = blaetter.get(name)
    if df is None:
        blatt_anlegen(name)
        return leer
    return df.copy() if not df.empty else leer


def blatt_anlegen(name: str):
    """Fehlendes Tabellenblatt anlegen."""
    sheet = get_sheet()
    if sheet is None:
        return
    try:
        sheet.add_worksheet(title=name, rows=2000, cols=30)
        alle_blaetter.clear()
    except Exception:
        pass


def _cache_zuruecksetzen():
    """Der gemeinsame Abruf ist die einzige Quelle — hier zurücksetzen."""
    alle_blaetter.clear()


# loadsheet.clear() wird an vielen Stellen aufgerufen — auf den
# gemeinsamen Abruf umbiegen, damit nichts ins Leere läuft.
loadsheet.clear = lambda *a, **k: alle_blaetter.clear()


def _zellwert(x) -> str:
    """Einen Wert in einen sauberen String für Google Sheets verwandeln."""
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


def _kopfzeile(name: str):
    """Die vorhandene Kopfzeile eines Blattes lesen. None = Blatt fehlt."""
    sheet = get_sheet()
    if sheet is None:
        return None, None
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        return None, None
    except Exception:
        return None, None
    try:
        kopf = [str(c).strip() for c in ws.row_values(1)]
    except Exception:
        return ws, None
    return ws, (kopf or None)


def savesheet_append(neu: pd.DataFrame, name: str, versuche: int = 3) -> bool:
    """
    Nur die neuen Zeilen anhängen.

    Der bisherige Weg war: ganzes Blatt löschen, alles neu schreiben.
    Bei wachsenden Blättern wird das langsam und läuft irgendwann ins
    Google-Limit. Anhängen schreibt nur, was wirklich dazukommt.

    Passt die Kopfzeile nicht zu den neuen Daten — etwa weil eine Spalte
    dazugekommen ist — wird auf das vollständige Schreiben zurückgefallen.
    Das ist der sichere Weg: lieber einmal langsam als ein verschobenes
    Blatt.
    """
    if neu.empty:
        return True

    ws, kopf = _kopfzeile(name)
    if ws is None or not kopf:
        # Blatt fehlt oder ist leer → einmal vollständig schreiben
        alt = loadsheet(name)
        gesamt = pd.concat([alt, neu], ignore_index=True) if not alt.empty else neu
        return savesheet(gesamt, name)

    # Spalten, die im Blatt nicht vorkommen → Schema hat sich geändert
    unbekannt = [c for c in neu.columns if str(c) not in kopf]
    if unbekannt:
        alt = loadsheet(name)
        gesamt = pd.concat([alt, neu], ignore_index=True) if not alt.empty else neu
        return savesheet(gesamt, name)

    ausgerichtet = neu.reindex(columns=kopf)
    zeilen = [[_zellwert(v) for v in reihe]
              for reihe in ausgerichtet.itertuples(index=False, name=None)]

    for versuch in range(versuche):
        try:
            ws.append_rows(zeilen, value_input_option="RAW",
                           insert_data_option="INSERT_ROWS",
                           table_range="A1")
            alle_blaetter.clear()
            return True
        except Exception as e:
            if "429" in str(e) and versuch < versuche - 1:
                wartezeit = 8 + versuch * 8
                st.warning(f"⚠️ Google-Limit — warte {wartezeit}s…")
                time.sleep(wartezeit)
            else:
                st.error(f"❌ Anhängen fehlgeschlagen: {str(e)[:150]}")
                return False
    return False


def sheet_zeile_setzen(name: str, daten: dict,
                       schluessel_spalte: str = "key") -> bool:
    """
    Eine einzelne Zeile schreiben.

    Ist der Schlüssel neu — der Normalfall — wird nur angehängt.
    Nur beim Überschreiben einer vorhandenen Zeile muss das Blatt
    komplett neu geschrieben werden.
    """
    spalten = SHEET_SPALTEN.get(name)
    df = loadsheet(name, spalten)
    schluessel = str(daten.get(schluessel_spalte, ""))

    vorhanden = (not df.empty and schluessel_spalte in df.columns
                 and (df[schluessel_spalte].astype(str) == schluessel).any())

    if vorhanden:
        rest = df[df[schluessel_spalte].astype(str) != schluessel]
        return savesheet(pd.concat([rest, pd.DataFrame([daten])],
                                   ignore_index=True), name)
    return savesheet_append(pd.DataFrame([daten]), name)


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

                zeilen = [out.columns.tolist()]
                for reihe in out.itertuples(index=False, name=None):
                    zeilen.append([_zellwert(v) for v in reihe])

                ws.update(zeilen, value_input_option="RAW")
            alle_blaetter.clear()
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


def append_rows(neu: pd.DataFrame, sheet_name: str,
                key_cols: list = None, id_spalte: str = None,
                aktualisieren: bool = False) -> int:
    """
    Neue Zeilen anhängen, Dubletten überspringen.

    Mit aktualisieren=True werden vorhandene Zeilen durch die neue
    Fassung ersetzt. Das braucht der Import: lädst du einen Tag erneut
    hoch, soll die Auswertung neu geschrieben werden — sonst bliebe ein
    Fall als offen stehen, obwohl du die Namensverknüpfung längst
    bestätigt hast.

    Gibt es eine echte ID-Spalte (bei Playtomic-Zahlungen die
    "Payment id"), zählt sie — dieselbe Zahlung darf nur einmal
    im Umsatz landen, auch wenn sich ihr Status zwischen zwei
    Exporten geändert hat. Sonst entscheidet der Zeilen-Hash.
    """
    if neu.empty:
        return 0

    alt = loadsheet(sheet_name)
    gemeinsam = [c for c in neu.columns
                 if c != "_hash" and (alt.empty or c in alt.columns)]

    neu = neu.copy()
    neu["_hash"] = _zeilen_hash(neu, gemeinsam)

    def kennung(df):
        """Echte ID wenn brauchbar, sonst Fachschlüssel, sonst Zeilen-Hash."""
        if id_spalte and id_spalte in df.columns:
            roh = df[id_spalte].astype(str).str.strip()
            brauchbar = ~roh.isin(["", "-", "nan", "None", "0"])
            return roh.where(brauchbar, df["_hash"])
        # Fachschlüssel (Tag + Spieler + Zeit + Court) erkennt dieselbe
        # Buchung auch dann wieder, wenn sich eine Auswertungsspalte
        # geändert hat. Über den vollen Zeilen-Hash entstünde sonst bei
        # jeder Korrektur eine zweite Zeile für denselben Spieltag.
        if key_cols and all(c in df.columns for c in key_cols):
            return df[key_cols].astype(str).agg("|".join, axis=1)
        return df["_hash"]

    neu["_id"] = kennung(neu)
    neu = neu.drop_duplicates(subset=["_id"])

    if not alt.empty:
        alt = alt.copy()
        hash_fehlt = "_hash" not in alt.columns
        if hash_fehlt:
            alt["_hash"] = _zeilen_hash(alt, gemeinsam)

        alt_kennung = kennung(alt).astype(str)
        neu_kennung = neu["_id"].astype(str)
        vorhanden = set(alt_kennung)

        if aktualisieren:
            # Dieselbe Buchung nochmal hochgeladen — die Auswertung kann
            # sich geändert haben, etwa weil du zwischenzeitlich eine
            # Namensverknüpfung bestätigt hast. Dann muss die alte Zeile
            # ersetzt werden statt übersprungen zu zählen.
            geaendert = neu[neu_kennung.isin(vorhanden)]
            wirklich_neu = neu[~neu_kennung.isin(vorhanden)]

            if not geaendert.empty:
                behalten = alt[~alt_kennung.isin(set(
                    geaendert["_id"].astype(str)))]
                gesamt = pd.concat(
                    [behalten, geaendert.drop(columns=["_id"]),
                     wirklich_neu.drop(columns=["_id"])], ignore_index=True)
                savesheet(gesamt, sheet_name)
                return len(wirklich_neu)
            neu = wirklich_neu
        else:
            neu = neu[~neu_kennung.isin(vorhanden)]

        if neu.empty:
            return 0

        if hash_fehlt:
            # Altbestand kennt die Hash-Spalte noch nicht. Einmal komplett
            # schreiben, damit die Dublettenprüfung danach trägt — ab dem
            # nächsten Import wird nur noch angehängt.
            savesheet(pd.concat([alt, neu.drop(columns=["_id"])],
                                ignore_index=True), sheet_name)
        else:
            # Nur die neuen Zeilen ans Blatt hängen. Vorher wurde das
            # komplette Blatt gelöscht und neu geschrieben — bei tausenden
            # Zeilen der teuerste Vorgang der ganzen App.
            savesheet_append(neu.drop(columns=["_id"]), sheet_name)
    else:
        savesheet(neu.drop(columns=["_id"]), sheet_name)

    return len(neu)


def betraege_verdaechtig(sheet_name: str = "playtomic_raw") -> dict:
    """
    Prüft, ob Beträge im Sheet durch Google verfälscht wurden.

    "13,5" wird von Google Sheets als 135 gelesen — das Komma gilt
    dort als Tausendertrennzeichen. Nachträglich lässt sich das nicht
    sicher zurückrechnen (135 könnte auch echt sein), deshalb nur
    erkennen und neu einlesen lassen.
    """
    df = loadsheet(sheet_name)
    ergebnis = {"betroffen": False, "summe": 0.0, "zeilen": 0, "anteil": 0.0}
    if df.empty or "Total" not in df.columns:
        return ergebnis

    werte = df["Total"].map(parse_betrag)
    ergebnis["summe"] = float(werte.sum())
    ergebnis["zeilen"] = len(df)

    # Court-Anteile liegen typisch zwischen 0 und 80 €. Häufen sich
    # dreistellige Beträge, spricht das für verlorene Dezimaltrenner.
    hoch = int((werte > 100).sum())
    ergebnis["anteil"] = prozent(hoch, len(df))
    ergebnis["betroffen"] = ergebnis["anteil"] > 8.0
    return ergebnis


def dubletten_bereinigen(sheet_name: str, id_spalte: str = None) -> tuple:
    """
    Vorhandene Dubletten aus einem Blatt entfernen.

    Bei Zahlungen entscheidet die Payment id: dieselbe Zahlung
    darf nur einmal zählen. Sonst gilt der vollständige Zeileninhalt.
    → (vorher, nachher)
    """
    df = loadsheet(sheet_name)
    if df.empty:
        return (0, 0)
    vorher = len(df)
    arbeit = df.copy()
    spalten = [c for c in arbeit.columns if c not in ("_hash", "_id")]
    arbeit["_hash"] = _zeilen_hash(arbeit, spalten)

    if id_spalte and id_spalte in arbeit.columns:
        roh = arbeit[id_spalte].astype(str).str.strip()
        brauchbar = ~roh.isin(["", "-", "nan", "None", "0"])
        arbeit["_id"] = roh.where(brauchbar, arbeit["_hash"])
    else:
        arbeit["_id"] = arbeit["_hash"]

    arbeit = arbeit.drop_duplicates(subset=["_id"]).drop(columns=["_id"])
    nachher = len(arbeit)
    if nachher < vorher:
        savesheet(arbeit, sheet_name)
        cache_leeren()
    return (vorher, nachher)


ABGELEITETE_CACHES = ("tages_kennzahlen", "verfuegbare_tage", "monats_kennzahlen",
                      "spieler_statistik", "auslastung_matrix",
                      "rejected_matches_laden", "einstellungen_laden",
                      "kontakt_index", "offene_fehler", "offene_je_tag", "eigener_anspruch",
                      "zuordnung_vorschlag", "nachhol_kandidaten",
                      "offene_checkins", "offene_checkins_zeitraum",
                      "verbrauchte_checkins", "anspruch_bilanz", "nachholung_quelle",
                      "mapping_gedeckt_je_tag", "mapping_belegte_checkins",
                      "checkin_erklaerung", "checkin_zuordnungen",
                      "redundante_korrekturen",
                      "buchungsnamen_am_tag", "abzug_pruefen", "verguetung_wert",
                      "checkins_von_am", "rabattierte_buchungen_am", "checkins_roh_und_verguetet",
                      "playtomic_spieler", "spieltage_von", "mapping_konflikte",
                      "offene_freigaben", "anspruch_verdacht")


def _cache_funktion_leeren(name: str):
    fn = globals().get(name)
    if fn is not None and hasattr(fn, "clear"):
        try:
            fn.clear()
        except Exception:
            pass


def cache_leeren(*blaetter, funktionen=None):
    """
    Datencaches leeren. Die Verbindung bleibt bestehen.

    Die Tabellendaten liegen in einem gemeinsamen Abruf — der wird
    immer komplett verworfen, das kostet nur zwei Google-Anfragen.
    Teuer sind die abgeleiteten Auswertungen: die werden nur geleert,
    wenn sie von der Änderung überhaupt betroffen sind.
    """
    alle_blaetter.clear()

    for fn_name in (ABGELEITETE_CACHES if funktionen is None else funktionen):
        _cache_funktion_leeren(fn_name)

    if funktionen is None:
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


def fenster_nachhol() -> int:
    """
    Wie viele Tage nach dem Spiel darf ein Check-in noch nachgeholt
    werden? Einstellbar, weil Leute sich unterschiedlich schnell melden.
    """
    return int(einstellung("nachhol_fenster_tage",
                           CONFIG["nachhol_fenster_tage"]))


def fenster_rueckblick() -> int:
    """Wie weit zurück werden überzählige Check-ins angezeigt?"""
    return int(einstellung("ueberzaehlig_rueckblick_tage",
                           CONFIG["ueberzaehlig_rueckblick_tage"]))


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


def token_widerrufen(token: str = None):
    """
    Anmeldung beenden. Ohne Token werden alle Geräte abgemeldet.
    """
    df = loadsheet("auth_tokens", SHEET_SPALTEN["auth_tokens"])
    if df.empty or "token" not in df.columns:
        return
    if token:
        df = df[df["token"].astype(str) != str(token)]
    else:
        df = df.iloc[0:0]
    savesheet(df, "auth_tokens")
    loadsheet.clear()


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
        hinterlegt = st.secrets.get("passwords", {}).get("admin_password", "")
        if not hinterlegt:
            st.error("Kein Passwort in den Secrets hinterlegt. "
                     "In Streamlit unter Settings → Secrets eintragen:")
            st.code('[passwords]\nadmin_password = "deinPasswort"', language=None)
            return False

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

# Spalten, deren Werte Geldbeträge sind und deshalb eindeutig
# geschrieben werden müssen, bevor sie ins Sheet wandern.
GELD_SPALTEN = (
    "Total", "Subtotal", "Taxes", "Net amount transferred",
    "B2B fee Total", "B2B fee Subtotal", "B2B fee Taxes",
    "Non-applicable total", "Non-applicable subtotal", "Non-applicable taxes",
    "price",
)


def zahlen_normalisieren(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beträge auf Punkt-Schreibweise bringen.

    Google Sheets deutet "13,5" sonst als 135 — das Komma wird als
    Tausendertrennzeichen gelesen. Aus 29.699 € würden 74.623 €.
    """
    if df.empty:
        return df
    out = df.copy()
    for spalte in out.columns:
        if str(spalte).strip() not in GELD_SPALTEN:
            continue
        out[spalte] = out[spalte].map(
            lambda v: "" if parse_betrag(v) == 0 and str(v).strip() in ("", "-", "nan")
            else f"{parse_betrag(v):.2f}")
    return out


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
    return zahlen_normalisieren(df)



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
    return zahlen_normalisieren(df)


def stundensatz(zeitpunkt: datetime, single_court: bool) -> float:
    """Der Stundensatz, der zu diesem Zeitpunkt gilt."""
    we = zeitpunkt.weekday() >= 5
    std = zeitpunkt.hour
    if single_court:
        return (CONFIG["preis_single_prime"] if (we or std >= 16)
                else CONFIG["preis_single_tag"])
    if we or std >= 16:
        return CONFIG["preis_double_prime"]
    if std >= 12:
        return CONFIG["preis_double_mittag"]
    return CONFIG["preis_double_frueh"]


def listenpreis(start: datetime, minuten: float, single_court: bool) -> float:
    """
    Regulärer Preis einer Buchung ohne jeden Rabatt.

    Abschnittsweise gerechnet, weil Playtomic das auch so macht: Eine
    Buchung von 15:00 bis 16:30 kostet eine Stunde zum Mittagstarif und
    eine halbe zum Abendtarif — nicht anderthalb Stunden zum Mittagstarif.

    Vorher galt für die ganze Dauer der Tarif der Startzeit. Bei jeder
    Buchung über eine Tarifgrenze war der Listenpreis dadurch zu
    niedrig, der errechnete Rabatt zu klein und in der Folge die
    Zuordnung der Wellpass-Spieler falsch.
    """
    if start is None or not minuten:
        return 0.0

    summe = 0.0
    rest = float(minuten)
    zeiger = start
    # Tarife wechseln nur zur vollen Stunde — abschnittsweise bis dahin
    while rest > 0.001:
        schritt = min(rest, 60.0 - zeiger.minute)
        summe += stundensatz(zeiger, single_court) * schritt / 60.0
        zeiger = zeiger + timedelta(minutes=schritt)
        rest -= schritt

    return round(summe, 2)


def ist_single_court(court_name: str) -> bool:
    """
    Ist das der Einzelcourt?

    Playtomic schreibt denselben Court unterschiedlich — mal
    "Single Court Padel 6", mal nur "Padel 6". Deshalb zählt
    neben der Bezeichnung auch die Court-Nummer aus CONFIG.
    """
    name = str(court_name).lower()
    if "single" in name:
        return True
    nummer = re.search(r"(\d+)", name)
    if nummer and int(nummer.group(1)) in CONFIG["single_court_nummern"]:
        return True
    return False


def court_plaetze(court_name: str) -> int:
    """
    Wie viele Plätze hat der Court?

    Playtomic berechnet den Preis immer auf die volle Platzzahl —
    auch wenn nur zwei Leute eingetragen sind. Die leeren Plätze
    gehen auf den Besitzer der Buchung.
    """
    return 2 if ist_single_court(court_name) else 4


# ── Events ───────────────────────────────────────────────────────────────────
#
# Ein Event ist keine teure Buchung, sondern eine andere Art Zeile.
# Playtomic markiert es hart, es muss also nichts geraten werden:
#
#   booking_type   OPEN_PLAY        statt REGULAR_BOOKING / OPEN_MATCH
#   activity_id    gesetzt          Kennung der Veranstaltung
#   activity_name  "…Mexicano"      Anzeigename
#   Product SKU    "Tournament registration"   in den Zahlungen
#
# Drei Dinge sind anders als bei einer Buchung, und jedes davon hat die
# alte Rechnung verdorben:
#   • Das Event steht einmal pro belegtem Court in der Datei — fünf
#     identische Zeilen sind EINE Veranstaltung.
#   • `price` ist der Gesamtumsatz des Events, nicht der Court-Preis.
#   • Der Preis pro Kopf ist frei gesetzt und hat mit dem Stundentarif
#     nichts zu tun. Der Wellpass-Rabatt ebenso wenig.

EVENT_MAX_PLAETZE = 20


def event_kennung(row) -> str:
    """
    Die Event-Kennung einer Buchungszeile — "" bei normaler Buchung.

    Verlangt werden beide Signale: eine gesetzte Aktivitäts-Kennung UND
    ein passender `booking_type`. Eine normale Buchung soll unter keinen
    Umständen als Event durchgehen — lieber ein Event übersehen als die
    Preislogik einer echten Buchung aushebeln.
    """
    kennung = ""
    for spalte in ("activity_id", "tournament_id"):
        wert = row.get(spalte)
        if wert is None:
            continue
        wert = str(wert).strip()
        if wert and wert.lower() not in ("nan", "none", "nat", "<na>"):
            kennung = wert
            break
    if not kennung:
        return ""
    art = str(row.get("booking_type", "") or "").strip().upper()
    if art and art not in ("OPEN_PLAY", "TOURNAMENT"):
        return ""
    return kennung


def event_titel(row) -> str:
    """Anzeigename des Events."""
    for spalte in ("activity_name", "course_name", "tournament_name"):
        wert = row.get(spalte)
        if wert is None:
            continue
        wert = str(wert).strip()
        if wert and wert.lower() not in ("nan", "none"):
            return wert
    return "Event"


def _zeilen_plaetze(row) -> int:
    """Wie viele Teilnehmerspalten diese Zeile haben kann."""
    return EVENT_MAX_PLAETZE if str(row.get("_event", "") or "") else 4


def wellpass_abzug_saetze() -> list:
    """Ab wann Playtomic wie viel abzieht. Aufsteigend nach Datum."""
    roh = einstellung("wellpass_abzug_saetze", CONFIG["wellpass_abzug_saetze"])
    saetze = []
    if isinstance(roh, (list, tuple)):
        for x in roh:
            if not isinstance(x, dict):
                continue
            try:
                ab, wert = str(x["ab"]), float(x["abzug"])
            except (KeyError, TypeError, ValueError):
                continue
            if ab and wert > 0:
                saetze.append({"ab": ab, "abzug": wert})
    if not saetze:
        saetze = list(CONFIG["wellpass_abzug_saetze"])
    return sorted(saetze, key=lambda x: x["ab"])


def wellpass_abzug_am(datum=None) -> float:
    """
    Welcher Abzug galt an diesem Tag — als bevorzugter Wert.

    Nicht als Gesetz: Gebucht wird bis zu zwei Wochen im Voraus, und
    massgeblich ist der Rabatt zum Zeitpunkt der Buchung. Nach einer
    Umstellung laufen deshalb noch Wochen später Buchungen mit dem
    alten Wert ein. Der Wert des Spieltags wird nur zuerst probiert.
    """
    if datum is None:
        datum = date.today()
    tag = str(datum)[:10]
    gueltig = CONFIG["wellpass_abzug"]
    for satz in wellpass_abzug_saetze():
        if tag >= satz["ab"]:
            gueltig = satz["abzug"]
        else:
            break
    return float(gueltig)


def wellpass_abzug() -> float:
    """Der heute gültige Abzug."""
    return wellpass_abzug_am(date.today())


def wellpass_anzahl(liste: float, bezahlt: float, plaetze: int,
                    abzug_wert: float = None, datum=None) -> int:
    """
    Wie viele Wellpass-Rabatte stecken in dieser Buchung?

    Playtomic zieht pro Wellpass-Spieler den kleineren Wert von
    (Preis pro Platz, Abzugsbetrag) ab. Aus der Preislücke lässt sich
    die Anzahl zurückrechnen.

    Der Abzugsbetrag ist nicht in Stein gemeisselt — er lag mal bei
    13,00 € und liegt inzwischen bei 12,00 €. Passt der eingestellte
    Wert nicht, werden die bekannten Alternativen durchprobiert.

    Ohne das war der Schaden erheblich: Bei einem Abzug von 12,00 € und
    einer Annahme von 13,00 € ging nur die Buchung mit EINEM Wellpass-
    Spieler zufällig auf. Zwei, drei oder vier Rabatte in derselben
    Buchung landeten bei 0 — die Buchung verschwand vollständig aus der
    Kontrolle, obwohl dort das meiste Geld hing.
    """
    rabatt = round(liste - bezahlt, 2)
    if rabatt < 0.5 or liste <= 0:
        return 0
    pro_platz = liste / max(plaetze, 1)

    if abzug_wert:
        kandidaten = [float(abzug_wert)]
    else:
        # Der zum Spieltag passende Wert zuerst, die anderen als
        # Rückfallebene — wegen der Vorausbuchungen über den Wechsel.
        kandidaten = [wellpass_abzug_am(datum)]
        for weiterer in CONFIG["wellpass_abzug_alternativen"]:
            if float(weiterer) not in kandidaten:
                kandidaten.append(float(weiterer))

    for kandidat in kandidaten:
        abzug = min(pro_platz, float(kandidat))
        if abzug <= 0:
            continue
        anzahl = rabatt / abzug
        gerundet = int(round(anzahl))
        if gerundet < 1 or gerundet > plaetze:
            continue
        if abs(anzahl - gerundet) <= 0.12:
            return gerundet

    return 0


def _teilnehmer_liste(row, max_plaetze: int = 4) -> list:
    """
    [(Name, E-Mail), …] einer Buchung.

    Eine normale Buchung hat höchstens vier Plätze. Ein Event füllt
    dagegen `participant_name_1` bis `participant_name_20`. Bei fest
    verdrahteten vier Plätzen waren dort 16 von 20 Teilnehmern für die
    gesamte Auswertung unsichtbar — sie tauchten weder als Spieler noch
    als möglicher Wellpass-Fall auf.
    """
    out = []
    for i in range(1, int(max_plaetze) + 1):
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
    cache_leeren()
    st.session_state.name_mapping_cache = mapping.copy()


def mapping_hinzufuegen(buchung_name: str, checkin_name: str, confidence=100):
    m = mapping_laden()
    m[buchung_name] = {
        "checkin_name": checkin_name,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat(),
        "confirmed_by": "manuell",
    }
    mapping_speichern(m)


def mapping_mehrere_hinzufuegen(paare: list):
    """
    Mehrere Verknüpfungen auf einmal — ein Schreibvorgang statt einer
    pro Paar. Bei zwanzig Zuordnungen ist das der Unterschied zwischen
    zwanzig Google-Anfragen und einer.

    paare = [(buchung_name, checkin_name, confidence), …]
    """
    if not paare:
        return
    m = mapping_laden()
    jetzt = datetime.now().isoformat()
    for buchung_name, checkin_name, confidence in paare:
        m[buchung_name] = {
            "checkin_name": checkin_name,
            "confidence": confidence,
            "timestamp": jetzt,
            "confirmed_by": "automatisch",
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
    savesheet_append(pd.DataFrame([{
        "buchung_name": buchung_name, "checkin_name": checkin_name,
        "timestamp": datetime.now().isoformat()}]), "rejected_matches")
    cache_leeren("rejected_matches",
                 funktionen=("rejected_matches_laden", "zuordnung_vorschlag",
                             "nachhol_kandidaten"))


def rejected_entfernen(buchung_name: str, checkin_name: str):
    df = loadsheet("rejected_matches", SHEET_SPALTEN["rejected_matches"])
    if not df.empty:
        df = df[~((df["buchung_name"].astype(str) == buchung_name) &
                  (df["checkin_name"].astype(str) == checkin_name))]
        savesheet(df, "rejected_matches")
        cache_leeren("rejected_matches",
                     funktionen=("rejected_matches_laden", "zuordnung_vorschlag",
                                 "nachhol_kandidaten"))


def name_aus_email(mail: str) -> str:
    """
    Namensbestandteile aus einer E-Mail-Adresse ziehen.

    "michaela_duerr@mein.gmx" → "michaela duerr"
    Damit lassen sich Namensvarianten erkennen, die über den reinen
    Namensvergleich nicht auffallen.
    """
    if not mail or "@" not in str(mail):
        return ""
    lokal = str(mail).split("@")[0].lower()
    if "privaterelay" in str(mail).lower():
        return ""
    # Trennzeichen zu Leerzeichen, Ziffern raus
    lokal = re.sub(r"[._\-+]+", " ", lokal)
    lokal = re.sub(r"\d+", " ", lokal)
    return normalize_name(lokal)


def email_aehnlichkeit(mail: str, name: str) -> float:
    """
    Wie gut passt eine E-Mail-Adresse zu einem Namen? 0–100

    Reagiert auch auf Teiltreffer: enthält die Adresse den Nachnamen,
    ist das ein starkes Indiz.
    """
    aus_mail = name_aus_email(mail)
    if not aus_mail:
        return 0.0
    ziel = normalize_name(name)
    if not ziel:
        return 0.0

    direkt = fuzz.token_set_ratio(aus_mail, ziel)

    # Einzelne Namensteile prüfen — jeder Teil zählt
    teile_ziel = [t for t in ziel.split() if len(t) > 2]
    teile_mail = [t for t in aus_mail.split() if len(t) > 2]
    treffer = sum(1 for t in teile_ziel
                  if any(fuzz.ratio(t, m) >= 85 for m in teile_mail))
    anteil = (treffer / len(teile_ziel) * 100) if teile_ziel else 0

    # Zusammengeschriebene Adressen: "katjaherold" enthält
    # "katja" und "herold" ohne Trennzeichen
    ohne_luecken = ziel.replace(" ", "")
    mail_kompakt = aus_mail.replace(" ", "")
    verschmolzen = fuzz.ratio(ohne_luecken, mail_kompakt)

    # Steckt jeder Namensteil als Zeichenfolge in der Adresse?
    enthalten = sum(1 for t in teile_ziel if t in mail_kompakt)
    enthalten_anteil = (enthalten / len(teile_ziel) * 100) if teile_ziel else 0

    return min(100.0, max(direkt, anteil, verschmolzen, enthalten_anteil))


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


def _vergleichsform(name: str) -> str:
    """
    Namen für den Vergleich glätten.

    Playtomic-Benutzernamen sehen oft aus wie „Jonas.valentino" oder
    „max_mustermann" — ohne Trennung bleibt das ein einziges Wort und
    jeder Vergleich mit der ausgeschriebenen Form scheitert.

    Bewusst nicht in normalize_name: dort würde es die gespeicherten
    Schlüssel verändern und bereits geschlossene Fälle wieder aufreissen.
    """
    s = str(name)
    for zeichen in (".", "_", ",", "/"):
        s = s.replace(zeichen, " ")
    return re.sub(r"\s+", " ", s).strip()


def _namensteile(name: str):
    """Vorname und Nachname trennen. Nachname = letztes Wort."""
    teile = [t for t in _vergleichsform(name).split() if t]
    if not teile:
        return "", ""
    if len(teile) == 1:
        return teile[0], ""
    return teile[0], teile[-1]


def _teil_aehnlich(a: str, b: str) -> float:
    """
    Zwei Namensteile vergleichen — Abkürzungen eingeschlossen.

    EGYM kürzt oft ab („Ka He" statt des vollen Namens). Ist ein Teil der
    Anfang des anderen, gilt das als starker Treffer.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    if len(a) >= 2 and len(b) >= 2 and (a.startswith(b) or b.startswith(a)):
        return 90.0
    return max(fuzz.ratio(a, b),
               fuzz.ratio(_lautschrift(a), _lautschrift(b)))


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

    such_vor, such_nach = _namensteile(suchname)
    such_glatt = _vergleichsform(suchname)

    treffer = []
    for kand in frei:
        if (suchname, kand) in abgelehnt:
            continue

        kand_glatt = _vergleichsform(kand)
        token = fuzz.token_set_ratio(such_glatt, kand_glatt)
        partial = fuzz.partial_ratio(such_glatt, kand_glatt)
        laut = fuzz.ratio(_lautschrift(such_glatt), _lautschrift(kand_glatt))
        basis = token * 0.5 + partial * 0.2 + laut * 0.3

        # Der Nachname entscheidet.
        #
        # Vorher gab es 20 Punkte allein dafür, dass die Anfangsbuchstaben
        # passten. Damit landete „Jannik Bretthauer" gegen „Jennifer Berka"
        # bei 71 % — zwei völlig verschiedene Menschen, beide J. B.
        kand_vor, kand_nach = _namensteile(kand)
        nachname = _teil_aehnlich(such_nach, kand_nach)
        vorname = _teil_aehnlich(such_vor, kand_vor)

        # Der Deckel greift nur, wenn beide Seiten überhaupt einen
        # Nachnamen haben. Bei Benutzernamen ohne zweiten Teil bliebe
        # sonst jeder Vergleich auf der Strecke.
        beide_mit_nachname = bool(such_nach) and bool(kand_nach)
        if beide_mit_nachname and nachname < 60:
            # Ohne ähnlichen Nachnamen reicht es nie für sich allein.
            # Andere Belege — Uhrzeit, E-Mail, nur bei EGYM bekannt —
            # können den Wert danach noch anheben.
            basis = min(basis, 65.0)

        bonus = 0.0
        if nachname >= 85 and vorname >= 85:
            bonus = 10.0
        elif nachname >= 85 or (vorname >= 90 and nachname >= 60):
            bonus = 5.0

        score = min(100.0, basis + bonus)
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


@st.cache_data(ttl=900, show_spinner=False)
def verguetung_wert(von: date = None, bis: date = None) -> float:
    """
    Was EGYM für diesen Zeitraum zahlt — jeder Tag mit dem Satz,
    der damals galt.

    Wichtig, weil der Satz gesenkt wurde: Würde man pauschal mit dem
    neuen Satz rechnen, wären rückwirkend alle alten Monatszahlen
    falsch.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return 0.0
    df = c.copy()
    df["_d"] = df["analysis_date"].map(parse_date_safe)
    df = df[df["_d"].notna()]
    if von is not None:
        df = df[df["_d"] >= von]
    if bis is not None:
        df = df[df["_d"] <= bis]
    if df.empty:
        return 0.0

    je_tag = df.groupby("_d")["Name_norm"].nunique()
    return round(sum(int(anzahl) * wellpass_wert_am(tag)
                     for tag, anzahl in je_tag.items()), 2)


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
    # Jeder Tag mit dem Satz seiner Zeit — EGYM hat gesenkt
    k["wellpass_wert"] = verguetung_wert(df["_datum"].min(), df["_datum"].max())
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
def auslastung_vorschlaege() -> list:
    """
    Konkrete Handlungsvorschläge statt nur einer Heatmap zum Anschauen.

    Drei Muster, jedes mit eigener Handlungsempfehlung:
      • Rückläufige Slots — letzte 4 Wochen deutlich schwächer als die
        4 Wochen davor. Früh erkennbar, bevor ein Slot ganz ausstirbt.
      • Tote Prime-Time-Slots — ab 16 Uhr oder am Wochenende seit
        Beginn der Daten ohne eine einzige Buchung.
      • Dauerhaft volle Nebenzeit-Slots — ausserhalb der Prime Time
        durchgehend unter den stärksten 10 % aller Slots. Kandidat für
        einen höheren Preis, statt Nachfrage zu verschenken.

    → [{"art": …, "text": …, "wochentag": …, "stunde": …}, …]
    """
    df = _rohdaten_aufbereitet()
    if df.empty:
        return []
    df = df[df["_buchung"]]
    if df.empty:
        return []

    heute = date.today()
    vorschlaege = []

    # ── Rückläufige Slots: letzte 4 Wochen vs. die 4 Wochen davor ───────
    letzte_4w = df[df["_datum"] >= heute - timedelta(days=28)]
    davor_4w = df[(df["_datum"] < heute - timedelta(days=28)) &
                  (df["_datum"] >= heute - timedelta(days=56))]
    if not letzte_4w.empty and not davor_4w.empty:
        m_neu = (letzte_4w.groupby(["_wochentag", "_stunde"]).size())
        m_alt = (davor_4w.groupby(["_wochentag", "_stunde"]).size())
        for schluessel, alt_anzahl in m_alt.items():
            if alt_anzahl < 3:
                continue  # zu wenig Basis für einen verlässlichen Vergleich
            neu_anzahl = int(m_neu.get(schluessel, 0))
            rueckgang = prozent(alt_anzahl - neu_anzahl, alt_anzahl)
            if rueckgang >= 40:
                wt, std = schluessel
                vorschlaege.append({
                    "art": "rueckgang",
                    "wochentag": int(wt), "stunde": int(std),
                    "text": (f"{WOCHENTAGE_DE[int(wt)]} {int(std)}:00 Uhr — "
                             f"{rueckgang:.0f}% weniger Buchungen als in den "
                             f"4 Wochen davor ({int(alt_anzahl)} → {neu_anzahl}). "
                             "Läuft der Slot einer festen Gruppe hinterher, die "
                             "gerade ausbleibt?"),
                })

    # ── Tote Prime-Time-Slots ─────────────────────────────────────────────
    gesamt = df.groupby(["_wochentag", "_stunde"]).size()
    wochen_erfasst = max(1, (df["_datum"].max() - df["_datum"].min()).days // 7)
    for wt in range(7):
        for std in range(CONFIG["oeffnung_von"], CONFIG["oeffnung_bis"]):
            prime = std >= 16 or wt >= 5
            if not prime:
                continue
            if gesamt.get((wt, std), 0) > 0:
                continue
            vorschlaege.append({
                "art": "leer",
                "wochentag": wt, "stunde": std,
                "text": (f"{WOCHENTAGE_DE[wt]} {std}:00 Uhr — seit "
                         f"{wochen_erfasst} Wochen keine einzige Buchung, "
                         "obwohl Prime-Time-Preis gilt. Kurs, Event oder "
                         "befristete Aktion könnte den Slot beleben."),
            })

    # ── Dauerhaft volle Nebenzeit-Slots — Preis-Kandidaten ──────────────
    if not gesamt.empty:
        schwelle = gesamt.quantile(0.9)
        for (wt, std), anzahl in gesamt.items():
            prime = std >= 16 or wt >= 5
            if prime or anzahl < schwelle or anzahl < 4:
                continue
            vorschlaege.append({
                "art": "stark",
                "wochentag": int(wt), "stunde": int(std),
                "text": (f"{WOCHENTAGE_DE[int(wt)]} {int(std)}:00 Uhr — "
                         f"{int(anzahl)} Buchungen trotz Nebenzeit-Preis, "
                         "unter den gefragtesten Slots insgesamt. Nachfrage "
                         "da für einen höheren Preis oder mehr Kapazität."),
            })

    reihenfolge = {"rueckgang": 0, "leer": 1, "stark": 2}
    vorschlaege.sort(key=lambda v: reihenfolge.get(v["art"], 9))
    return vorschlaege


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


@st.cache_data(ttl=600, show_spinner=False)
def mapping_gedeckt_je_tag() -> dict:
    """
    Fälle, die durch eine nachträglich bestätigte Verknüpfung geklärt sind.

    Die Fehler-Kennzeichnung entsteht beim Import und wird gespeichert.
    Bestätigst du danach eine Namensverknüpfung, bleibt die alte Zeile
    stehen — der Fall taucht weiter auf, obwohl er längst geklärt ist.
    Genau deshalb kam „Ka He" immer wieder hoch.

    Hier wird die Verknüpfung beim Anzeigen nachträglich angewandt,
    ohne dass du irgendetwas neu hochladen musst.

    → {datum: {buchungs_name_norm, …}}
    """
    mapping = mapping_laden()
    if not mapping:
        return {}

    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return {}

    # Welcher Check-in-Name ist welchem Buchungsnamen zugeordnet?
    rueck = {}
    for buchung_name, ziel in mapping.items():
        gname = str(ziel["checkin_name"] if isinstance(ziel, dict) else ziel)
        rueck.setdefault(gname, []).append(str(buchung_name))

    verbraucht = verbrauchte_checkins()

    gedeckt = {}
    for tag, gruppe in c.groupby(c["analysis_date"].astype(str)):
        namen = set(gruppe["Name_norm"].astype(str))
        for checkin_name, buchungs_namen in rueck.items():
            if checkin_name not in namen:
                continue
            # Ein Check-in, der schon einen älteren Fall geschlossen hat,
            # steht hier nicht mehr zur Verfügung.
            if checkin_schluessel(tag, checkin_name) in verbraucht:
                continue
            gedeckt.setdefault(tag, set()).update(buchungs_namen)

    return gedeckt


@st.cache_data(ttl=600, show_spinner=False)
def mapping_belegte_checkins() -> dict:
    """
    Welche Check-ins sind durch eine bestätigte Verknüpfung bereits
    einer Buchung zugeordnet?

    Gegenstück zu mapping_gedeckt_je_tag. Ohne das entstand ein
    Widerspruch: Der Fall verschwand aus der Liste, weil die Verknüpfung
    ihn deckt — der Check-in stand aber weiter als überzählig daneben,
    weil das Kennzeichen „Gespielt" beim Import gesetzt wurde und nichts
    davon wusste.

    → {datum: {checkin_name_norm, …}}
    """
    mapping = mapping_laden()
    if not mapping:
        return {}

    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return {}

    b = loadsheet("buchungen")
    if b.empty or "Name_norm" not in b.columns:
        return {}

    verbraucht = verbrauchte_checkins()
    belegt = {}

    for tag, gruppe in c.groupby(c["analysis_date"].astype(str)):
        checkin_namen = set(gruppe["Name_norm"].astype(str))
        spieler = set(b[b["analysis_date"].astype(str) == str(tag)]
                      ["Name_norm"].astype(str))

        for buchung_name, ziel in mapping.items():
            if str(buchung_name) not in spieler:
                continue
            gname = str(ziel["checkin_name"] if isinstance(ziel, dict) else ziel)
            if gname not in checkin_namen:
                continue
            if checkin_schluessel(tag, gname) in verbraucht:
                continue
            belegt.setdefault(str(tag), set()).add(gname)

    return belegt


def _ohne_belegte(offen: pd.DataFrame, tag: str) -> pd.DataFrame:
    """Check-ins entfernen, die einer Buchung per Verknüpfung gehören."""
    belegt = mapping_belegte_checkins().get(str(tag), set())
    if not belegt or offen.empty:
        return offen
    return offen[~offen["Name_norm"].astype(str).isin(belegt)]


def _ohne_gedeckte(fehler: pd.DataFrame, tag: str) -> pd.DataFrame:
    """
    Durch Verknüpfung geklärte Fälle herausnehmen.

    Pro Person und Tag nur einen — EGYM vergütet nicht mehr. Wer an
    einem Tag zweimal mit Rabatt gespielt hat, behält seinen zweiten
    offenen Fall.
    """
    gedeckt = mapping_gedeckt_je_tag().get(str(tag), set())
    if not gedeckt or fehler.empty:
        return fehler

    behalten, schon_gedeckt = [], set()
    for idx, name in zip(fehler.index, fehler["Name_norm"].astype(str)):
        if name in gedeckt and name not in schon_gedeckt:
            schon_gedeckt.add(name)
            continue
        behalten.append(idx)
    return fehler.loc[behalten]


@st.cache_data(ttl=900, show_spinner=False)
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

    return _ohne_gedeckte(fehler, datum_str)


@st.cache_data(ttl=900, show_spinner=False)
def offene_je_tag() -> dict:
    """
    Anzahl offener Fälle für ALLE Tage in einem einzigen Durchlauf.

    Für Dropdown-Beschriftungen und Serien-Berechnung. Vorher rief die
    format_func für jeden Tag offene_fehler() auf — bei 26 Tagen also
    26 Filterläufe bei jedem Rendern der Seite.

    → {"2026-07-14": 3, …}
    """
    df = loadsheet("buchungen")
    if df.empty or "Fehler" not in df.columns or "analysis_date" not in df.columns:
        return {}

    fehler = df[df["Fehler"].astype(str) == "Ja"].copy()
    if fehler.empty:
        return {}

    datums_spalte = "Datum" if "Datum" in fehler.columns else "analysis_date"
    erledigt = behobene_keys()
    if erledigt:
        keys = (fehler["Name_norm"].astype(str) + "_"
                + fehler[datums_spalte].astype(str))
        fehler = fehler[~keys.isin(erledigt)]
        if fehler.empty:
            return {}

    zaehler = {}
    for tag, gruppe in fehler.groupby(fehler["analysis_date"].astype(str)):
        anzahl = len(_ohne_gedeckte(gruppe, tag))
        if anzahl:
            zaehler[str(tag)] = int(anzahl)
    return zaehler


def alle_offenen_fehler(tage: list) -> pd.DataFrame:
    """Offene Fehler über mehrere Tage in einer Tabelle."""
    teile = [offene_fehler(t) for t in tage]
    teile = [t for t in teile if not t.empty]
    if not teile:
        return pd.DataFrame()
    return pd.concat(teile, ignore_index=True)


def offene_uebersicht() -> pd.DataFrame:
    """
    Alle offenen Fälle über alle Tage, pro Person zusammengefasst.

    Für den Überblick, wenn mehrere Tage auf einmal nachgearbeitet
    werden — im Tag-für-Tag-Blick sieht man sonst nie, dass dieselbe
    Person schon zum zweiten oder dritten Mal auftaucht.
    """
    tage = verfuegbare_tage()
    if not tage:
        return pd.DataFrame()
    alle = alle_offenen_fehler(tage)
    if alle.empty:
        return pd.DataFrame()

    zeilen = []
    for nn, gruppe in alle.groupby("Name_norm"):
        tage_sortiert = sorted(gruppe["Datum"].astype(str))
        zeilen.append({
            "Name": gruppe["Name"].iloc[-1],
            "Name_norm": nn,
            "Anzahl offen": len(gruppe),
            "Ältester offener Fall": datum_kurz(tage_sortiert[0]),
            "Tage": ", ".join(datum_kurz(t) for t in tage_sortiert),
        })
    df = pd.DataFrame(zeilen)
    return df.sort_values(["Anzahl offen", "Name"], ascending=[False, True])


def gesperrt_historie() -> pd.DataFrame:
    """
    Wie oft wurde wer mit dem Grund „Gesperrt" erledigt.

    Zeigt Wiederholungstäter: taucht jemand hier zwei- oder dreimal auf,
    fehlen entsprechend viele Check-ins.
    """
    df = erledigte_faelle()
    if df.empty:
        return pd.DataFrame()
    g = df[df["grund"] == "gesperrt"]
    if g.empty:
        return pd.DataFrame()

    zeilen = []
    for nn, teil in g.groupby("name_norm"):
        tage_sortiert = sorted(teil["datum"].astype(str))
        zeilen.append({
            "Name": teil["Name"].iloc[-1],
            "Name_norm": nn,
            "Anzahl gesperrt": len(teil),
            "Tage": ", ".join(datum_kurz(t) for t in tage_sortiert),
        })
    df = pd.DataFrame(zeilen)
    return df.sort_values(["Anzahl gesperrt", "Name"], ascending=[False, True])


# ── Sperren auflösen ─────────────────────────────────────────────────────────
#
# Eine Sperre ist kein eigener Zustand, sondern die Summe der Fälle, die
# mit dem Grund „Gesperrt" geschlossen wurden. Wer zweimal gesperrt
# wurde, hat zwei solche Fälle — ihm fehlen zwei Check-ins.
#
# Holt jemand einen Check-in nach, wird der von Hand genau einem dieser
# Fälle zugeordnet. Der Fall wechselt damit auf „Nachgeholt" und zählt
# nicht mehr als Sperre: aus 2× gesperrt wird 1×.
#
# Das passiert bewusst NIE automatisch. Ein Check-in hat Geldwirkung und
# eine Sperre hat Folgen für einen Menschen — beides darf keine
# Namensähnlichkeit im Hintergrund entscheiden. Die App schlägt nur vor,
# zugeordnet wird per Klick.
#
# Erreicht jemand dabei null offene Sperren, ist die Sperre selbst noch
# nicht aufgehoben: Der Wellpass-Zugang hängt bei EGYM, nicht in dieser
# App. Deshalb entsteht in dem Moment eine Freigabe-Aufgabe, die so
# lange sichtbar bleibt, bis sie ausdrücklich bestätigt wird.


def gesperrt_faelle(name_norm: str) -> pd.DataFrame:
    """
    Die noch offenen Sperren einer Person — je Zeile ein Spieltag,
    der mit „Gesperrt" geschlossen wurde. Neueste zuerst.
    """
    df = erledigte_faelle()
    if df.empty:
        return pd.DataFrame()
    treffer = df[(df["grund"] == "gesperrt")
                 & (df["name_norm"].astype(str) == str(name_norm))]
    if treffer.empty:
        return pd.DataFrame()
    return treffer.sort_values("datum", ascending=False)


def sperre_nachholung_zuordnen(name_norm: str, name: str, fall_datum: str,
                               checkin_datum: str, checkin_name: str) -> bool:
    """
    Einen nachgeholten Check-in einer bestehenden Sperre zuordnen.

    Der Fall wechselt von „Gesperrt" auf „Nachgeholt", die Zahl der
    offenen Sperren sinkt um eins. Fällt sie damit auf null, entsteht
    eine Freigabe-Aufgabe — die App kann den Wellpass-Zugang nicht
    selbst wieder öffnen, also muss sie daran erinnern.

    → True, wenn zugeordnet wurde
    """
    vorher = len(gesperrt_faelle(name_norm))
    if not nachholung_speichern(checkin_datum, checkin_name,
                                fall_datum, name_norm):
        return False

    # nachholung_speichern hat "corrections" bereits geleert — die Zahl
    # der offenen Sperren ist damit frisch.
    nachher = len(gesperrt_faelle(name_norm))
    if vorher > 0 and nachher == 0:
        freigabe_anlegen(name_norm, name, fall_datum)
    return True


def freigabe_anlegen(name_norm: str, name: str, letzte_sperre: str):
    """Eine offene Freigabe-Aufgabe vormerken."""
    sheet_zeile_setzen("freigaben", {
        "name_norm": str(name_norm),
        "name": str(name),
        "ausgeloest_am": date.today().isoformat(),
        "letzte_sperre": str(letzte_sperre),
        "bestaetigt": "",
        "timestamp": datetime.now().isoformat(),
    }, schluessel_spalte="name_norm")
    cache_leeren("freigaben", funktionen=("offene_freigaben",))


@st.cache_data(ttl=300, show_spinner=False)
def offene_freigaben() -> pd.DataFrame:
    """
    Wer ist rechnerisch wieder frei, wurde aber noch nicht freigegeben?

    Doppelt abgesichert: Es zählt nur, wer keine offene Sperre mehr hat.
    Wurde jemand nach dem Nachholen erneut gesperrt, verschwindet die
    Aufgabe von selbst — sonst würde die App zur Freigabe eines gerade
    frisch gesperrten Spielers auffordern.
    """
    df = loadsheet("freigaben", SHEET_SPALTEN["freigaben"])
    if df.empty or "name_norm" not in df.columns:
        return pd.DataFrame()
    offen = df[~df.get("bestaetigt", pd.Series([""] * len(df))).map(is_true)]
    if offen.empty:
        return pd.DataFrame()

    historie = gesperrt_historie()
    noch_gesperrt = (set(historie["Name_norm"].astype(str))
                     if not historie.empty else set())
    offen = offen[~offen["name_norm"].astype(str).isin(noch_gesperrt)]
    return offen.sort_values("timestamp", ascending=False)


def freigabe_bestaetigen(name_norm: str):
    """Die Freigabe ist erledigt — der Zugang wurde wieder geöffnet."""
    df = loadsheet("freigaben", SHEET_SPALTEN["freigaben"])
    if df.empty or "name_norm" not in df.columns:
        return
    treffer = df[df["name_norm"].astype(str) == str(name_norm)]
    if treffer.empty:
        return
    zeile = treffer.iloc[-1].to_dict()
    zeile["bestaetigt"] = "Ja"
    zeile["timestamp"] = datetime.now().isoformat()
    sheet_zeile_setzen("freigaben", zeile, schluessel_spalte="name_norm")
    cache_leeren("freigaben", funktionen=("offene_freigaben",))


def freigabe_verwerfen(name_norm: str):
    """
    Eine Freigabe-Aufgabe entfernen.

    Wird gebraucht, wenn jemand erneut gesperrt wird, bevor die alte
    Freigabe bestätigt war — die Aufgabe ist dann gegenstandslos.
    """
    df = loadsheet("freigaben", SHEET_SPALTEN["freigaben"])
    if df.empty or "name_norm" not in df.columns:
        return
    rest = df[df["name_norm"].astype(str) != str(name_norm)]
    if len(rest) != len(df):
        savesheet(rest, "freigaben")
        cache_leeren("freigaben", funktionen=("offene_freigaben",))


def als_behoben_markieren(name_norm: str, datum: str,
                          grund: str = "", notiz: str = "", betrag=None):
    """
    Einen Fall schliessen — mit Grund und, wo es zählt, mit Betrag.

    Der Betrag ist frei: mal kommt die volle Bearbeitungsgebühr rein,
    mal nur der normale Spieleranteil. Bleibt er leer, gilt der
    Standardwert des Grundes.
    """
    # Wird ein Fall mit einem anderen Grund geschlossen, war eine zuvor
    # gesetzte Nachholung falsch — der Check-in gehört dann wieder frei.
    geloest = False
    if grund and str(grund) != "nachgeholt":
        geloest = zuordnung_zu_fall_loesen(name_norm, datum)

    # Wer erneut gesperrt wird, ist nicht mehr freizugeben — eine noch
    # offene Freigabe-Aufgabe von vorher wäre jetzt falsch.
    if str(grund) == "gesperrt":
        freigabe_verwerfen(name_norm)

    sheet_zeile_setzen("corrections", {
        "key": f"{name_norm}_{datum}", "date": datum, "behoben": True,
        "grund": str(grund or ""),
        "betrag": "" if betrag is None else f"{float(betrag):.2f}",
        "notiz": str(notiz or "").strip(),
        "timestamp": datetime.now().isoformat()})

    cache_leeren("corrections", funktionen=(
        "offene_fehler", "offene_je_tag", "verbrauchte_checkins",
        "offene_checkins", "offene_checkins_zeitraum", "nachhol_kandidaten",
        "nachholung_quelle", "anspruch_bilanz")
        if geloest else ("offene_fehler", "offene_je_tag", "anspruch_bilanz"))


def _erledigt_knopf(name_norm: str, datum: str, key: str):
    """
    Kompakter Erledigt-Knopf: Bezahlt oder Gesperrt.

    Ein Klick öffnet ein kleines Popover statt sofort zu schliessen —
    damit der Grund nie verloren geht (vorher gab es keine Auswahl,
    jeder Fall landete als „Ohne Grund erfasst").
    """
    with st.popover("Erledigt", use_container_width=True):
        st.caption("Wie wurde der Fall geklärt?")
        if st.button("💶 Bezahlt", key=f"{key}_bezahlt",
                     use_container_width=True):
            als_behoben_markieren(name_norm, datum, grund="bezahlt")
            st.toast("Als bezahlt markiert.")
            st.rerun()
        if st.button("🔒 Gesperrt", key=f"{key}_gesperrt",
                     use_container_width=True):
            als_behoben_markieren(name_norm, datum, grund="gesperrt")
            st.toast("Als gesperrt markiert.")
            st.rerun()


def zuordnung_zu_fall_loesen(name_norm: str, datum: str) -> bool:
    """
    Die Check-in-Zuordnung eines Falls entfernen und den Check-in
    wieder freigeben.

    Ohne das blieb ein einmal zugeordneter Check-in für immer verbraucht:
    Man konnte den Fall zwar wieder öffnen, der Check-in tauchte aber
    nirgends mehr auf und liess sich niemand anderem mehr zuordnen.

    War die Zuordnung am selben Tag, wurde damals auch eine dauerhafte
    Namensverknüpfung angelegt („Ist dieselbe"). Die muss mit weg —
    sonst gilt der fremde Name weiter als derselbe Mensch. Genau so
    galt ein fremder Check-in-Name noch als derselbe Mensch, nachdem der
    Fall längst korrigiert war.
    """
    df = loadsheet("checkin_zuordnung", SHEET_SPALTEN["checkin_zuordnung"])
    if df.empty or "fall_key" not in df.columns:
        return False
    fk = checkin_schluessel(datum, name_norm)
    treffer = df[df["fall_key"].astype(str) == fk]
    if treffer.empty:
        return False

    savesheet(df[df["fall_key"].astype(str) != fk], "checkin_zuordnung")

    z = treffer.iloc[0]
    if str(z.get("checkin_datum")) == str(datum):
        ziel = mapping_laden().get(str(name_norm))
        gemerkt = str(ziel["checkin_name"] if isinstance(ziel, dict)
                      else ziel or "")
        if gemerkt and gemerkt == str(z.get("checkin_name")):
            mapping_entfernen(str(name_norm))
    return True


def behebung_zuruecknehmen(name_norm: str, datum: str):
    """
    Einen versehentlich als erledigt markierten Fall wieder öffnen —
    und den dafür verwendeten Check-in wieder freigeben.
    """
    corr = loadsheet("corrections", SHEET_SPALTEN["corrections"])
    if not corr.empty and "key" in corr.columns:
        key = f"{name_norm}_{datum}"
        savesheet(corr[corr["key"].astype(str) != key], "corrections")

    geloest = zuordnung_zu_fall_loesen(name_norm, datum)

    cache_leeren("corrections", funktionen=(
        "offene_fehler", "offene_je_tag", "verbrauchte_checkins",
        "offene_checkins", "offene_checkins_zeitraum", "nachhol_kandidaten",
        "nachholung_quelle", "mapping_gedeckt_je_tag")
        if geloest else ("offene_fehler", "offene_je_tag"))


def erledigte_faelle() -> pd.DataFrame:
    """Alle als erledigt markierten Fälle mit Namen und Datum."""
    corr = loadsheet("corrections", SHEET_SPALTEN["corrections"])
    if corr.empty or "key" not in corr.columns:
        return pd.DataFrame()
    df = corr[corr["behoben"].map(is_true)].copy()
    if df.empty:
        return df

    # Schlüssel wieder in Name und Datum zerlegen
    def zerlegen(key):
        teile = str(key).rsplit("_", 1)
        return (teile[0], teile[1]) if len(teile) == 2 else (str(key), "")
    df[["name_norm", "datum"]] = pd.DataFrame(
        [zerlegen(k) for k in df["key"]], index=df.index)

    # Grund — nur zum Anzeigen/Zählen, keine Bilanz dahinter
    if "grund" not in df.columns:
        df["grund"] = ""
    if "notiz" not in df.columns:
        df["notiz"] = ""
    df["grund"] = df["grund"].fillna("").astype(str).str.strip()
    df["notiz"] = df["notiz"].fillna("").astype(str)
    df["grund_label"] = df["grund"].map(lambda g: grund_info(g)["label"])
    df["grund_kurz"] = df["grund"].map(lambda g: grund_info(g)["kurz"])

    # Anzeigenamen aus den Buchungen holen
    b = loadsheet("buchungen")
    if not b.empty and {"Name_norm", "Name"} <= set(b.columns):
        namen = (b.drop_duplicates(subset=["Name_norm"])
                 .set_index("Name_norm")["Name"].to_dict())
        df["Name"] = df["name_norm"].map(lambda n: namen.get(n, n))
    else:
        df["Name"] = df["name_norm"]

    df["_ts"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    return df.sort_values("_ts", ascending=False)


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


@st.cache_data(ttl=600, show_spinner=False)
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

    # Bereits als Nachholung verbrauchte Check-ins ausblenden
    verbraucht = verbrauchte_checkins()
    if verbraucht:
        offen["_key"] = offen.apply(
            lambda r: f"{r['analysis_date']}|{r['Name_norm']}", axis=1)
        offen = offen[~offen["_key"].isin(verbraucht.keys())]

    # Durch eine bestätigte Verknüpfung bereits einer Buchung zugeordnet
    offen = _ohne_belegte(offen, datum_str)

    return offen.drop_duplicates(subset=["Name_norm"])


@st.cache_data(ttl=600, show_spinner=False)
def zuordnung_vorschlag(name: str, datum_str: str, mail: str = None,
                       zeit: str = None) -> list:
    """
    Passende offene Check-ins zu einem gemeldeten Vergesser finden.

    Drei Signale fliessen ein:
      1. Namensähnlichkeit
      2. E-Mail-Adresse — "michaela_duerr@…" verrät den Nachnamen
      3. Zeitnähe zwischen Check-in und Spielbeginn

    → [(anzeigename, name_norm, score, checkin_zeit, grund), …]
    """
    offen = offene_checkins(datum_str)
    if offen.empty:
        return []

    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()
    kandidaten = offen["Name_norm"].astype(str).tolist()
    anzeige = dict(zip(offen["Name_norm"].astype(str), offen["Name"].astype(str)))
    zeiten = dict(zip(offen["Name_norm"].astype(str),
                      offen.get("Checkin_Zeit", pd.Series("", index=offen.index))
                      .astype(str)))

    if mail is None:
        mail = email_fuer(name)

    spielstunde = stunde_aus_zeit(zeit) if zeit else -1

    ergebnis = {}
    for kand, score, quelle in fuzzy_match(normalize_name(name), kandidaten,
                                           mapping, abgelehnt):
        ergebnis[kand] = [score, "Name"]

    # E-Mail-Signal: passt die Adresse zum Check-in-Namen?
    if mail:
        for kand in kandidaten:
            if (normalize_name(name), kand) in abgelehnt:
                continue
            mail_score = email_aehnlichkeit(mail, anzeige.get(kand, kand))
            if mail_score >= 70:
                vorher = ergebnis.get(kand, [0, ""])[0]
                if mail_score > vorher:
                    ergebnis[kand] = [mail_score, "E-Mail"]
                elif vorher:
                    # Beide Signale sprechen dafür → Sicherheit erhöhen
                    ergebnis[kand] = [min(100.0, vorher + 12), "Name + E-Mail"]

    # Zeitnähe als kleiner Zuschlag
    if spielstunde >= 0:
        for kand, wert in ergebnis.items():
            ci = stunde_aus_zeit(zeiten.get(kand, ""))
            if ci >= 0 and abs(ci - spielstunde) <= 1:
                wert[0] = min(100.0, wert[0] + 5)
                if "Zeit" not in wert[1]:
                    wert[1] += " + Zeit"

    # Kennt Playtomic den Check-in-Namen?
    #
    # Nein → es ist fast sicher nur die EGYM-Schreibweise derselben Person.
    # Ja  → derjenige hat einen eigenen Playtomic-Account und ist damit
    #       ein eigenständiger Mensch. Dann ist die Zuordnung verdächtig.
    bekannt = playtomic_spieler()
    for kand, wert in ergebnis.items():
        eigene_tage = bekannt.get(kand, 0)
        if not eigene_tage:
            wert[0] = min(100.0, wert[0] + 10)
            wert[1] += " + nur bei EGYM"
        else:
            wert[0] = max(0.0, wert[0] - 30)
            wert[1] += (f" · ACHTUNG: dieser Name hat {eigene_tage} eigene "
                        f"Buchung{'en' if eigene_tage > 1 else ''} in "
                        "Playtomic, ist also wohl jemand anderes")

    sortiert = sorted(ergebnis.items(), key=lambda x: x[1][0], reverse=True)
    return [(anzeige.get(k, k), k, round(v[0], 1), zeiten.get(k, ""), v[1])
            for k, v in sortiert if v[0] >= 50]


def _rabattierte_namen_am(datum: str) -> list:
    """Alle Namen, die an diesem Tag mit Rabatt gespielt haben."""
    df = loadsheet("buchungen")
    if df.empty or "analysis_date" not in df.columns:
        return []
    tag = df[df["analysis_date"].astype(str) == str(datum)]
    if tag.empty or "Relevant" not in tag.columns:
        return []
    tag = tag[tag["Relevant"].astype(str) == "Ja"]
    return [str(x) for x in tag["Name_norm"]] if not tag.empty else []


def _teilmengen_name(a: str, b: str) -> bool:
    """
    Ist ein Name die Kurzform des anderen?

    Playtomic führt manche Spieler nur mit dem Vornamen — „Bryan",
    während die Check-in-Liste „Bryan Victor Biber" kennt. Für den
    Nachnamen-Vergleich ist so ein Name unbrauchbar: Ein einzelnes Wort
    hat keinen Nachnamen, die Prüfung läuft ins Leere.
    """
    ta = {t for t in _vergleichsform(a).split() if len(t) >= 3}
    tb = {t for t in _vergleichsform(b).split() if len(t) >= 3}
    if not ta or not tb or ta == tb:
        return False
    return ta < tb or tb < ta


@st.cache_data(ttl=600, show_spinner=False)
def eigener_anspruch(name_norm: str, datum: str) -> int:
    """
    Hatte diese Person an diesem Tag selbst eine rabattierte Buchung?

    Wichtig für Nachholungen: EGYM vergütet pro Person und Tag nur
    einmal. Wer am Tag des Check-ins auch selbst mit Rabatt gespielt
    hat, braucht diesen Check-in für sich — er kann keinen älteren
    Fall mehr schliessen.

    Der Check-in-Name muss dabei nicht der Buchungsname sein. Playtomic
    kennt „Bryan", die Check-in-Liste „Bryan Victor Biber". Wer nur
    exakt nachschlägt, findet die eigene Buchung nicht, hält den
    Check-in für frei und lässt ihn einen älteren Fall schliessen —
    obwohl er an seinem eigenen Tag gebraucht wird. Genau so ging ein
    Check-in vom Event-Tag an einen zwei Wochen älteren Fall.

    Deshalb zählen drei Wege:
      • der Name selbst,
      • jeder Buchungsname, der über den Namensabgleich auf diesen
        Check-in-Namen zeigt,
      • Namen desselben Tages, deren Nachname eindeutig passt — nach
        denselben Regeln, nach denen die App sonst eine Nachholung
        zuordnet.

    Der dritte Weg ist Absicht: Ein Name, der gut genug ist, um einen
    Fall zu schliessen, ist auch gut genug, um einen Check-in zu
    schützen. Alles andere wäre eine Asymmetrie zu Lasten der Kasse.

    → Anzahl der eigenen rabattierten Buchungen an diesem Tag
    """
    ziel = str(name_norm)
    namen = _rabattierte_namen_am(datum)
    if not namen:
        return 0

    erlaubt = {ziel}
    for buchung_name, zuordnung in mapping_laden().items():
        gname = str(zuordnung["checkin_name"] if isinstance(zuordnung, dict)
                    else zuordnung)
        if gname == ziel:
            erlaubt.add(str(buchung_name))

    treffer = sum(1 for n in namen if n in erlaubt)
    if treffer:
        return treffer

    abgelehnt = rejected_matches_laden()
    such_vor, such_nach = _namensteile(ziel)
    for kand in set(namen):
        if (kand, ziel) in abgelehnt or (ziel, kand) in abgelehnt:
            continue
        kand_vor, kand_nach = _namensteile(kand)
        if (such_nach and kand_nach
                and _teil_aehnlich(such_nach, kand_nach) >= 85
                and _teil_aehnlich(such_vor, kand_vor) >= 55):
            return sum(1 for n in namen if n == kand)
    return 0


@st.cache_data(ttl=600, show_spinner=False)
def anspruch_verdacht(name_norm: str, datum: str) -> list:
    """
    Namen, die an diesem Tag mit Rabatt gespielt haben und die Kurzform
    dieses Check-in-Namens sein könnten.

    Bewusst kein harter Riegel wie `eigener_anspruch`: „Daniel" könnte
    Daniel Litz sein oder Daniel Kohlmus. Ein Blockieren wäre geraten
    und würde eine berechtigte Nachholung verschlucken. Angezeigt wird
    es trotzdem — entscheiden soll ein Mensch, nicht die Ähnlichkeit.
    """
    ziel = str(name_norm)
    if eigener_anspruch(ziel, datum):
        return []
    abgelehnt = rejected_matches_laden()
    verdacht = []
    for kand in set(_rabattierte_namen_am(datum)):
        if (kand, ziel) in abgelehnt or (ziel, kand) in abgelehnt:
            continue
        if _teilmengen_name(ziel, kand):
            verdacht.append(kand)
    return sorted(verdacht)


def nachhol_warnung(name_norm: str, checkin_datum: str) -> str:
    """Warntext, falls der Check-in an seinem eigenen Tag gebraucht wird."""
    if eigener_anspruch(name_norm, checkin_datum):
        return ("⚠️ An diesem Tag hat er <b>selbst mit Rabatt gespielt</b>. "
                "EGYM vergütet pro Person und Tag nur einmal — dieser "
                "Check-in gehört zu diesem Tag und kann den älteren Fall "
                "nicht schliessen.")
    verdacht = anspruch_verdacht(name_norm, checkin_datum)
    if verdacht:
        namen = ", ".join(f"<b>{v}</b>" for v in verdacht[:3])
        return ("⚠️ An diesem Tag hat {namen} mit Rabatt gespielt — "
                "möglicherweise dieselbe Person unter dem kürzeren "
                "Playtomic-Namen. Dann gehört der Check-in zu jenem Tag "
                "und darf diesen Fall nicht schliessen. Vorher im "
                "Name-Abgleich klären.").replace("{namen}", namen)
    return ""


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


def alle_checkins_ohne_buchung() -> pd.DataFrame:
    """
    Alle überzähligen Check-ins, roh und ungruppiert — über alle Tage.

    „Überzählig" heisst: keine Buchung gefunden UND noch frei. Ein
    Check-in, der bereits einen älteren Fall geschlossen hat oder über
    eine bestätigte Namensverknüpfung längst einer Buchung gehört, ist
    verbraucht und gehört nicht mehr in diese Liste. Ohne diese beiden
    Abzüge zählte die Übersicht jede erledigte Zuordnung weiter mit —
    die Zahl stieg mit jeder Bearbeitung, statt zu sinken.
    """
    c = loadsheet("checkins")
    if c.empty or "Gespielt" not in c.columns or "analysis_date" not in c.columns:
        return pd.DataFrame()
    df = c[c["Gespielt"].astype(str) == "Nein"].copy()
    if df.empty:
        return df

    verbraucht = verbrauchte_checkins()
    if verbraucht:
        schluessel = [checkin_schluessel(str(t), str(n)) for t, n
                      in zip(df["analysis_date"], df["Name_norm"])]
        df = df[[k not in verbraucht for k in schluessel]]
    if df.empty:
        return df

    belegt = mapping_belegte_checkins()
    if belegt:
        df = df[[str(n) not in belegt.get(str(t), set()) for t, n
                 in zip(df["analysis_date"], df["Name_norm"])]]
    return df


def zu_viele_checkins_uebersicht() -> pd.DataFrame:
    """
    Alle Check-ins ohne passende Buchung, über alle Tage — pro Person
    zusammengefasst. Wer hier öfter auftaucht, checkt regelmässig ein,
    ohne dass eine Buchung dazu gefunden wird.
    """
    ueber = alle_checkins_ohne_buchung()
    if ueber.empty:
        return pd.DataFrame()

    zeilen = []
    for nn, teil in ueber.groupby("Name_norm"):
        tage_sortiert = sorted(teil["analysis_date"].astype(str))
        zeilen.append({
            "Name": teil["Name"].iloc[-1] if "Name" in teil.columns else nn,
            "Name_norm": nn,
            "Zu viele Check-ins": len(teil),
            "Tage": ", ".join(datum_kurz(t) for t in tage_sortiert),
        })
    df = pd.DataFrame(zeilen)
    return df.sort_values(["Zu viele Check-ins", "Name"], ascending=[False, True])


def sauber_serie(tage: list) -> int:
    """Wie viele Tage in Folge (ab heute rückwärts) ohne offenen Fehler?"""
    zaehler = offene_je_tag()
    serie = 0
    for t in tage:
        if zaehler.get(str(t), 0) == 0:
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


@st.cache_data(ttl=900, show_spinner=False)
def spieler_rhythmus() -> pd.DataFrame:
    """
    Pro Spieler der eigene Spielrhythmus — üblicher Abstand zwischen
    zwei Besuchen, verglichen mit der aktuellen Pause.

    Die normale Rückholung nimmt für alle denselben Tage-Schwellwert.
    Das übersieht Vielspieler: wer sonst alle 3 Tage kommt und jetzt
    10 Tage weg ist, ist längst auffällig — ein fester 21-Tage-Schwellwert
    sieht das erst viel später. Das Risiko-Verhältnis (aktuelle Pause ÷
    üblicher Abstand) macht das früh sichtbar, unabhängig vom
    persönlichen Rhythmus.

    → Name, Besuche, üblicher Abstand, aktuelle Pause, Risiko-Verhältnis
    """
    b = loadsheet("buchungen")
    if b.empty or "Name" not in b.columns or "analysis_date" not in b.columns:
        return pd.DataFrame()

    df = b.copy()
    if "Name_norm" in df.columns:
        df = df[~df["Name_norm"].astype(str).isin(TEAM_NORM)]
    df["_datum"] = df["analysis_date"].map(parse_date_safe)
    df = df[df["_datum"].notna()]
    if df.empty:
        return pd.DataFrame()

    heute = date.today()
    zeilen = []
    for name, gruppe in df.groupby("Name"):
        tage = sorted(gruppe["_datum"].unique())
        if len(tage) < 3:
            continue  # zu wenig Besuche für einen verlässlichen Rhythmus
        abstaende = [(tage[i + 1] - tage[i]).days for i in range(len(tage) - 1)]
        avg_abstand = sum(abstaende) / len(abstaende)
        if avg_abstand <= 0:
            continue
        pause = (heute - tage[-1]).days
        zeilen.append({
            "Name": name,
            "Besuche": len(tage),
            "Ø Abstand": round(avg_abstand, 1),
            "Aktuelle Pause": pause,
            "Risiko": round(pause / avg_abstand, 2),
            "Letzter Besuch": str(tage[-1]),
        })
    if not zeilen:
        return pd.DataFrame()
    return pd.DataFrame(zeilen).sort_values("Risiko", ascending=False)


def spieler_segmente() -> pd.DataFrame:
    """
    Grobe Einteilung aller Kunden in Segmente — für den Überblick, nicht
    für Wissenschaft. Basis sind Buchungsanzahl und Tage seit dem
    letzten Besuch aus spieler_statistik().

      • Neu          — höchstens 2 Buchungen, seit ≤30 Tagen zum ersten Mal da
      • Stammspieler — 5+ Buchungen, war in den letzten 21 Tagen da
      • Rückläufig   — 5+ Buchungen, aber länger als 21 Tage nicht mehr da
      • Verloren     — länger als 60 Tage nicht mehr da
      • Gelegenheit  — der Rest
    """
    stat = spieler_statistik()
    if stat.empty:
        return pd.DataFrame()
    kunden = stat[~stat["team"]].copy()
    if kunden.empty:
        return kunden

    def _segment(r):
        if r["tage_her"] > 60:
            return "Verloren"
        if r["buchungen"] <= 2 and r["tage_her"] <= 30:
            return "Neu"
        if r["buchungen"] >= 5:
            return "Stammspieler" if r["tage_her"] <= 21 else "Rückläufig"
        return "Gelegenheit"

    kunden["Segment"] = kunden.apply(_segment, axis=1)
    kunden["Wellpass-Anteil"] = kunden.apply(
        lambda r: prozent(r["wellpass_pflichtig"], r["buchungen"])
        if r["buchungen"] else 0.0, axis=1)
    return kunden


# ══════════════════════════════════════════════════════════════════════════════
#   🗓  EVENT- UND WIEDERKEHR-ANALYSEN
#
#   Die Frage hinter allem hier: Bringt ein Event etwas, das über den
#   Umsatz des Tages hinausgeht? Zwanzig Leute an einem Sonntag sind
#   schnell gezählt. Interessant ist, wer von ihnen vorher schon kam,
#   wer danach wiederkam — und ob das mehr ist als bei allen anderen im
#   selben Zeitraum. Ohne diesen Vergleich sagt eine Wiederkehrquote
#   nichts: Wenn ohnehin 60 % innerhalb einer Woche wiederkommen, sind
#   60 % nach dem Event kein Erfolg.
# ══════════════════════════════════════════════════════════════════════════════


@st.cache_data(ttl=900, show_spinner=False)
def spieltage_je_spieler() -> dict:
    """{name_norm: [datum, …]} — alle Spieltage je Spieler, aufsteigend."""
    b = loadsheet("buchungen")
    if b.empty or "Name_norm" not in b.columns or "analysis_date" not in b.columns:
        return {}
    df = b[~b["Name_norm"].astype(str).isin(TEAM_NORM)].copy()
    if df.empty:
        return {}
    df["_d"] = df["analysis_date"].map(parse_date_safe)
    df = df[df["_d"].notna()]
    out = {}
    for nn, gruppe in df.groupby("Name_norm"):
        out[str(nn)] = sorted({d for d in gruppe["_d"]})
    return out


def _datenstand() -> tuple:
    """Erster und letzter Tag, für den überhaupt Daten vorliegen."""
    tage = verfuegbare_tage()
    if not tage:
        return None, None
    geparst = sorted(d for d in (parse_date_safe(t) for t in tage) if d)
    return (geparst[0], geparst[-1]) if geparst else (None, None)


@st.cache_data(ttl=900, show_spinner=False)
def event_liste() -> pd.DataFrame:
    """
    Alle erkannten Events mit ihren Kennzahlen — eine Zeile je Event.

    Court-Stunden statt nur Teilnehmerzahl: Ein Event blockiert die
    halbe Halle. Erst im Verhältnis zur Tageskapazität wird sichtbar,
    was es die Anlage gekostet hat.
    """
    b = loadsheet("buchungen")
    if b.empty or "Event" not in b.columns:
        return pd.DataFrame()
    ev = b[b["Event"].astype(str) == "Ja"].copy()
    if ev.empty:
        return pd.DataFrame()

    zeilen = []
    for (tag, kennung), g in ev.groupby(["analysis_date", "Event_Id"], sort=False):
        dauer = pd.to_numeric(g["Dauer"], errors="coerce").max()
        courts = pd.to_numeric(g["Event_Courts"], errors="coerce").max()
        dauer = 0 if pd.isna(dauer) else float(dauer)
        courts = 0 if pd.isna(courts) else float(courts)
        umsatz = pd.to_numeric(g["Bezahlt"], errors="coerce").fillna(0).sum()
        zeilen.append({
            "Datum": str(tag),
            "Event_Id": str(kennung),
            "Name": str(g["Event_Name"].iloc[0] or "Event"),
            "Zeit": str(g["Service_Zeit"].iloc[0]),
            "Teilnehmer": int(g["Name_norm"].nunique()),
            "Wellpass": int((g["Relevant"].astype(str) == "Ja").sum()),
            "Offene Fälle": int((g["Fehler"].astype(str) == "Ja").sum()),
            "Courts": int(courts),
            "Court-Stunden": round(courts * dauer / 60.0, 1),
            "Umsatz": round(float(umsatz), 2),
            "Unklar": str(g["Event_Unklar"].iloc[0]) if "Event_Unklar" in g.columns else "Nein",
        })
    df = pd.DataFrame(zeilen)
    return df.sort_values("Datum", ascending=False)


def _quote(menge: set, tage_je_spieler: dict, von: date, bis: date) -> tuple:
    """Wie viele aus der Menge haben zwischen von und bis gespielt?"""
    if not menge or von > bis:
        return 0, len(menge)
    treffer = 0
    for nn in menge:
        if any(von <= d <= bis for d in tage_je_spieler.get(nn, [])):
            treffer += 1
    return treffer, len(menge)


@st.cache_data(ttl=900, show_spinner=False)
def event_wirkung(datum: str, event_id: str, fenster: tuple = (7, 14, 30)) -> dict:
    """
    Was das Event bewirkt hat — vorher, nachher, und im Vergleich.

    Drei Zahlen je Zeitfenster:
      • Teilnehmer, die vorher schon da waren  → wie viele waren Stammgäste
      • Teilnehmer, die danach wiederkamen     → die eigentliche Wirkung
      • dieselbe Quote für alle anderen Spieler → die Kontrollgruppe

    Die Kontrollgruppe ist der Kern. Sie besteht aus allen Spielern, die
    im Monat vor dem Event aktiv waren, aber nicht teilgenommen haben.
    Kommen von denen genauso viele wieder, hat das Event nichts bewegt —
    die Leute wären ohnehin gekommen.

    Fenster, für die noch keine Daten vorliegen, werden als unvollständig
    gekennzeichnet statt als Null ausgewiesen. Ein Event von vorgestern
    kann keine 30-Tage-Wirkung haben, und eine 0 wäre schlicht falsch.
    """
    tag = parse_date_safe(datum)
    if tag is None:
        return {}
    b = loadsheet("buchungen")
    if b.empty or "Event_Id" not in b.columns:
        return {}
    ev = b[(b["analysis_date"].astype(str) == str(datum))
           & (b["Event_Id"].astype(str) == str(event_id))]
    if ev.empty:
        return {}

    teilnehmer = {str(n) for n in ev["Name_norm"] if str(n) not in TEAM_NORM}
    alle_tage = spieltage_je_spieler()
    _erster, letzter = _datenstand()

    # Kontrollgruppe: im Monat vor dem Event aktiv, aber nicht dabei
    kontrolle = set()
    for nn, tage in alle_tage.items():
        if nn in teilnehmer:
            continue
        if any(tag - timedelta(days=30) <= d < tag for d in tage):
            kontrolle.add(nn)

    ergebnis = {"teilnehmer": len(teilnehmer), "kontrollgruppe": len(kontrolle),
                "datenstand": letzter, "fenster": {}}

    # Wer war vor dem Event überhaupt schon einmal da?
    #
    # Vorsicht mit dem Wort „neu": Hier steht nur, dass im geladenen
    # Zeitraum kein früherer Besuch liegt. Reichen die Daten bis kurz vor
    # das Event, sieht die halbe Stammkundschaft wie Neukundschaft aus.
    # Deshalb wird der Beginn des Datenzeitraums mitgegeben — die
    # Anzeige muss die Zahl entsprechend einordnen.
    neu = {nn for nn in teilnehmer
           if not any(d < tag for d in alle_tage.get(nn, []))}
    ergebnis["ohne_vorbesuch"] = len(neu)
    ergebnis["ohne_vorbesuch_wieder"] = sum(
        1 for nn in neu if any(d > tag for d in alle_tage.get(nn, [])))
    ergebnis["daten_ab"] = _erster
    ergebnis["vorlauf_tage"] = (tag - _erster).days if _erster else 0

    for n in fenster:
        vor_treffer, _ = _quote(teilnehmer, alle_tage,
                                tag - timedelta(days=n), tag - timedelta(days=1))
        vollstaendig = letzter is not None and letzter >= tag + timedelta(days=n)
        bis_real = min(tag + timedelta(days=n), letzter) if letzter else tag
        nach_treffer, _ = _quote(teilnehmer, alle_tage,
                                 tag + timedelta(days=1), bis_real)
        kon_treffer, _ = _quote(kontrolle, alle_tage,
                                tag + timedelta(days=1), bis_real)
        ergebnis["fenster"][n] = {
            "vorher": vor_treffer,
            "vorher_quote": prozent(vor_treffer, len(teilnehmer)),
            "nachher": nach_treffer,
            "nachher_quote": prozent(nach_treffer, len(teilnehmer)),
            "kontrolle": kon_treffer,
            "kontrolle_quote": prozent(kon_treffer, len(kontrolle)),
            "vollstaendig": bool(vollstaendig),
            "gemessen_bis": bis_real,
        }
    return ergebnis


@st.cache_data(ttl=900, show_spinner=False)
def wiederkehr_kurve(mindest_kohorte: int = 3) -> pd.DataFrame:
    """
    Von allen Spielern mit einem ersten Besuch in einer Woche: wie viele
    kamen in den folgenden Wochen wieder?

    Die klassische Kohortenfrage. Sie beantwortet, ob Neukunden hängen
    bleiben — und ob sich das über die Monate verändert. Eine einzelne
    Wiederkehrquote sagt wenig; die Reihe zeigt, ob es besser wird.

    Nur Kohorten, deren Fenster vollständig in den Daten liegt.
    """
    tage_je = spieltage_je_spieler()
    if not tage_je:
        return pd.DataFrame()
    erster, letzter = _datenstand()
    if erster is None:
        return pd.DataFrame()

    # Die ersten Wochen der Daten sind unbrauchbar: Dort sieht jeder wie
    # ein Neukunde aus, weil sein früherer Besuch schlicht nicht geladen
    # ist. Ohne diesen Abstand meldete die erste Woche 260 „neue"
    # Spieler — praktisch die gesamte Stammkundschaft.
    vorlauf = erster + timedelta(days=14)

    kohorten = {}
    for nn, tage in tage_je.items():
        if not tage:
            continue
        start = tage[0]
        if start < vorlauf:
            continue
        woche = start - timedelta(days=start.weekday())
        kohorten.setdefault(woche, []).append((nn, start))

    zeilen = []
    for woche in sorted(kohorten):
        leute = kohorten[woche]
        if len(leute) < mindest_kohorte:
            continue
        zeile = {"Kohorte": str(woche), "Neu": len(leute)}
        for w in (1, 2, 4):
            if letzter < woche + timedelta(days=7 * w + 7):
                zeile[f"Woche {w}"] = None
                continue
            wieder = sum(
                1 for nn, start in leute
                if any(start < d <= start + timedelta(days=7 * w)
                       for d in tage_je.get(nn, [])))
            zeile[f"Woche {w}"] = round(prozent(wieder, len(leute)), 1)
        zeilen.append(zeile)
    return pd.DataFrame(zeilen)


@st.cache_data(ttl=900, show_spinner=False)
def neukunden_je_woche() -> pd.DataFrame:
    """Wie viele Spieler waren in einer Woche zum ersten Mal da?"""
    tage_je = spieltage_je_spieler()
    erster, _letzter = _datenstand()
    if not tage_je or erster is None:
        return pd.DataFrame()
    vorlauf = erster + timedelta(days=14)
    zaehler = {}
    for nn, tage in tage_je.items():
        if not tage or tage[0] < vorlauf:
            continue
        woche = tage[0] - timedelta(days=tage[0].weekday())
        zaehler[woche] = zaehler.get(woche, 0) + 1
    if not zaehler:
        return pd.DataFrame()
    return pd.DataFrame(
        [{"Woche": str(w), "Neue Spieler": n} for w, n in sorted(zaehler.items())])


@st.cache_data(ttl=900, show_spinner=False)
def event_teilnehmer_details(datum: str, event_id: str) -> pd.DataFrame:
    """
    Je Teilnehmer eines Events: war er vorher da, kam er danach wieder?

    Für den Blick auf die einzelnen Menschen statt nur auf die Quote —
    wer neu war und wiederkam, ist die wertvollste Gruppe.
    """
    tag = parse_date_safe(datum)
    b = loadsheet("buchungen")
    if tag is None or b.empty or "Event_Id" not in b.columns:
        return pd.DataFrame()
    ev = b[(b["analysis_date"].astype(str) == str(datum))
           & (b["Event_Id"].astype(str) == str(event_id))]
    if ev.empty:
        return pd.DataFrame()

    tage_je = spieltage_je_spieler()
    zeilen = []
    for _, r in ev.drop_duplicates(subset=["Name_norm"]).iterrows():
        nn = str(r["Name_norm"])
        tage = tage_je.get(nn, [])
        vorher = [d for d in tage if d < tag]
        nachher = [d for d in tage if d > tag]
        zeilen.append({
            "Name": str(r["Name"]),
            "Wellpass": str(r.get("Relevant", "")),
            "Bezahlt": parse_betrag(r.get("Bezahlt")),
            "Besuche vorher": len(vorher),
            "Letzter Besuch davor": str(vorher[-1]) if vorher else "—",
            "Wieder da am": str(nachher[0]) if nachher else "—",
            "Tage bis Rückkehr": (nachher[0] - tag).days if nachher else None,
            "Status": ("Ohne Vorbesuch · wiedergekommen" if not vorher and nachher else
                       "Ohne Vorbesuch · noch nicht wieder" if not vorher else
                       "Stammgast · wiedergekommen" if nachher else
                       "Stammgast · noch nicht wieder"),
        })
    return pd.DataFrame(zeilen).sort_values(
        ["Besuche vorher", "Name"], ascending=[True, True])


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
 .pc-vorschlag .grund {{ color:var(--dim); font-size:.76rem; margin-left:.4rem; }}
 .pc-vorschlag.nachhol {{
  background:rgba(74,222,128,.09); border-color:rgba(74,222,128,.4);
 }}
 .pc-vorschlag.nachhol b {{ color:{C['ok']}; }}
 /* Seitenspalte: überzählige Check-ins */
 .pc-zahl {{
  font-size:2.4rem; font-weight:800; color:var(--volt); line-height:1;
 }}
 .pc-zahl-sub {{ color:var(--dim); font-size:.76rem; margin-top:.2rem; }}
 .pc-uez {{
  background:var(--ink1); border:1px solid var(--line);
  border-left:3px solid var(--line-str); border-radius:var(--r-sm);
  padding:.6rem .8rem; margin-bottom:.35rem;
 }}
 .pc-uez.treffer {{ border-left-color:var(--volt); }}
 .pc-uez .nm {{ font-weight:600; color:var(--text); font-size:.9rem; }}
 .pc-uez .mt {{ color:var(--dim); font-size:.74rem; margin-top:.15rem; }}
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
  background:var(--volt) !important; border-color:var(--volt) !important;
  font-weight:700 !important;
 }}
 /* Streamlit legt den Text in ein eigenes Element — die Farbe muss
    deshalb auch auf alle Kinder gesetzt werden, sonst bleibt sie weiss. */
 div.stButton > button[kind="primary"], div.stButton > button[kind="primary"] *,
 div.stDownloadButton > button[kind="primary"],
 div.stDownloadButton > button[kind="primary"] * {{
  color:#0A0A0A !important; fill:#0A0A0A !important;
 }}
 div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover {{
  background:#EFFF4D !important;
 }}
 div.stButton > button[kind="primary"]:hover *,
 div.stDownloadButton > button[kind="primary"]:hover * {{
  color:#0A0A0A !important;
 }}
 /* Nicht-Primärbuttons: heller Text auf dunklem Grund */
 div.stButton > button:not([kind="primary"]) *,
 div.stDownloadButton > button:not([kind="primary"]) * {{
  color:inherit !important;
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
 /* aktives Modul — sofort erkennbar wo man ist */
 section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
  background:var(--volt) !important; color:#0A0A0A !important;
  border-color:var(--volt) !important; font-weight:700 !important;
 }}
 section[data-testid="stSidebar"] div.stButton > button[kind="primary"] * {{
  color:#0A0A0A !important;
 }}
 section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{
  background:var(--volt) !important; filter:brightness(1.08);
 }}
 section[data-testid="stSidebar"] div.stButton > button:disabled,
 section[data-testid="stSidebar"] div.stButton > button:disabled * {{
  color:var(--faint) !important; opacity:.55;
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
 /* ═══ HANDY ═══
    Keine Funktion verschwindet — Streamlit stapelt Spalten unter dieser
    Breite ohnehin schon automatisch untereinander. Hier geht's nur um
    Feintuning: weniger verschwendeter Platz, grössere Tippflächen. */
 @media (max-width: 640px) {{
  .block-container {{ padding-top:1.1rem; padding-left:.8rem; padding-right:.8rem; padding-bottom:2rem; }}
  .pc-head {{ padding:1.1rem 1.2rem; margin-bottom:1rem; }}
  .pc-head h1 {{ font-size:1.15rem; }}
  .pc-head .mark {{ width:36px; }}
  .pc-kpi {{ padding:.85rem .95rem; }}
  .pc-kpi .v {{ font-size:1.35rem; }}
  .pc-card {{ padding:.85rem 1rem; }}
  .pc-box {{ padding:.75rem .9rem; font-size:.85rem; }}
  .pc-tile {{ min-height:auto; padding:1rem 1.1rem 1.15rem; }}
  .pc-streak {{ padding:.9rem 1.1rem; }}
  .pc-streak .n {{ font-size:1.8rem; }}
  .pc-zahl {{ font-size:1.9rem; }}
  /* Buttons: Reihen aus mehreren Spalten (z.B. Senden/Nachfassen/
     Erledigt) werden von Streamlit automatisch untereinander gestapelt —
     jeder Button wird dadurch volle Breite. Hier nur die Tippfläche
     grosszügiger machen, nicht die Optik ändern. */
  div.stButton > button, div.stDownloadButton > button {{
   padding:.62rem 1.15rem !important; font-size:.88rem !important;
   min-height:2.6rem;
  }}
  .stTabs [data-baseweb="tab"] {{ padding:.45rem .7rem; font-size:.78rem; }}
  [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p {{
   font-size:.82rem !important;
  }}
  h1 {{ font-size:1.4rem !important; }}
  h2 {{ font-size:1.2rem !important; }}
  h3, h4 {{ font-size:1.05rem !important; }}
 }}
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
    {(name_norm, startzeit): {"summe": …, "kleinste": …, "zeilen": …}}

    Die Summe allein reicht nicht. Bezahlt jemand für einen Gast mit,
    stehen mehrere Zeilen auf seinem Namen — beim Aufsummieren sieht er
    dann aus wie ein Vollzahler, obwohl eine der Zeilen sein eigener
    rabattierter Platz war.

    Typischer Fall: jemand zahlt 16,50 € für seinen Gast und 4,50 € für
    sich mit Wellpass. Summiert ergibt das 21 € — und die App hielt
    daraufhin den Gast für den Rabattträger.

    Deshalb wird zusätzlich die kleinste Einzelzahlung mitgeführt.
    Rückerstattungen bleiben aussen vor, sonst wäre die kleinste Zahlung
    immer der negative Betrag.
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
    if df.empty:
        return {}

    out = {}
    for schluessel, gruppe in df.groupby(["_nn", "_dt"]):
        betraege = [float(x) for x in gruppe["_bt"]]

        # Rückerstattungen mit ihrer Ursprungszahlung verrechnen.
        #
        # Wer umbucht, hinterlässt mehrere Zeilen für denselben Slot:
        # die alte Zahlung, die Rückerstattung und die neue Zahlung.
        # Ferenc hatte fünf Zeilen — 13,50 / 9,00 / 13,50 / −9,00 /
        # −13,50. Übrig bleibt eine Zahlung über 13,50 €, also Vollpreis.
        # Ohne Verrechnung galten die 9,00 € aus der stornierten Buchung
        # als kleinste Zahlung, und er wurde für einen Rabattträger
        # gehalten.
        #
        # Eine 0,00-€-Zeile ist dagegen keine Rückerstattung, sondern der
        # Beweis für einen vollen Wellpass-Rabatt — die bleibt.
        offen = sorted([x for x in betraege if x > 0])
        nullen = [x for x in betraege if x == 0]
        for erstattung in sorted([-x for x in betraege if x < 0]):
            passend = [p for p in offen if abs(p - erstattung) < 0.01]
            if passend:
                offen.remove(passend[0])

        effektiv = sorted(offen + nullen)
        out[schluessel] = {
            "summe": float(sum(betraege)),
            "kleinste": effektiv[0] if effektiv else float(sum(betraege)),
            "zeilen": len(effektiv),
            "werte": effektiv,          # die wirksamen Einzelzahlungen
        }
    return out


def _event_zahlungs_index(pdf: pd.DataFrame) -> dict:
    """
    Was jeder Teilnehmer für ein Event bezahlt hat.

    → {datum: {name_norm: {"betrag": …, "dt": …}}}

    Event-Zahlungen stehen unter einer eigenen SKU („Tournament
    registration"). Der normale Zahlungs-Index lässt nur Buchungen und
    Open Matches durch und hat sie deshalb komplett verworfen — für ein
    Event gab es bislang keinen einzigen Zahlungsbeleg, obwohl dort der
    Preis pro Kopf sauber einzeln drinsteht.

    Zweiter Unterschied: Bei einer normalen Buchung ist `Service date`
    der Beginn, bei einem Event das Ende. Ein Abgleich über den exakten
    Zeitstempel geht deshalb ins Leere. Gruppiert wird hier nach Tag,
    die Uhrzeit bleibt für die Zuordnung zum Zeitfenster erhalten.

    Erstattungen werden verrechnet: Wer storniert hat, war nicht dabei
    und darf die Preisstufen des Events nicht verfälschen.
    """
    if pdf.empty or "Service date" not in pdf.columns:
        return {}
    if "Product SKU" not in pdf.columns or "User name" not in pdf.columns:
        return {}
    df = pdf[pdf["Product SKU"].astype(str)
             .str.contains("tournament|event|activity", case=False, na=False)].copy()
    if df.empty:
        return {}
    df["_dt"] = df["Service date"].map(parse_datetime_safe)
    df["_nn"] = df["User name"].map(normalize_name)
    df["_bt"] = df["Total"].map(parse_betrag)
    df = df[df["_dt"].notna()]
    df = df[df["_nn"].astype(str).str.len() > 0]
    if df.empty:
        return {}

    out = {}
    df["_tag"] = df["_dt"].map(lambda d: d.date())
    for (nn, tag), gruppe in df.groupby(["_nn", "_tag"]):
        netto = round(float(gruppe["_bt"].sum()), 2)
        if netto <= 0:
            continue          # storniert oder vollständig erstattet
        out.setdefault(tag, {})[str(nn)] = {
            "betrag": netto,
            "dt": max(gruppe["_dt"]),
        }
    return out


def _event_rabatte(zahlungen: dict) -> tuple:
    """
    Aus den gezahlten Beträgen eines Events ableiten, wer rabattiert hat.

    → (vollpreis, {name_norm: rabatt}, sicher)

    Weder der Eventpreis noch der Wellpass-Rabatt stehen irgendwo in den
    Rohdaten. Beides ist pro Event frei gesetzt — mal 8 €, mal 10 €, mal
    15 € Nachlass auf einen jedes Mal anderen Grundpreis. Der
    Standardabzug von 12 € greift hier nicht, und ein fester Schwellwert
    wäre auch keine Lösung: Er müsste den Rabatt schon kennen, den er
    finden soll, und würde bei einem Event mit 5 € Nachlass schweigen.

    Deshalb kommt der Maßstab aus dem Event selbst. Der höchste gezahlte
    Betrag ist der Vollpreis, jeder Betrag darunter ist rabattiert. Das
    ist unabhängig von der Höhe des Rabatts und vom Preis des Events.

    `sicher` ist False, wenn alle denselben Betrag gezahlt haben. Dann
    fehlt der Vollzahler als Vergleich — entweder hatte niemand Wellpass
    oder ausnahmslos alle. Dieser Fall wird angezeigt, nicht geraten.
    """
    werte = [d["betrag"] for d in zahlungen.values() if d["betrag"] > 0]
    if not werte:
        return 0.0, {}, False
    vollpreis = max(werte)
    rabatte = {nn: round(vollpreis - d["betrag"], 2)
               for nn, d in zahlungen.items() if d["betrag"] > 0}
    return vollpreis, rabatte, len(set(werte)) > 1


def _event_altzeilen_entfernen(eintraege: list) -> int:
    """
    Beim erneuten Import eines Events die alten Court-Einzelzeilen
    wegräumen.

    Ein Event wird jetzt als eine Zeile je Teilnehmer gespeichert, mit
    allen belegten Courts zusammen im Feld `Court`. Früher — und in
    jedem Altbestand — stand dort ein einzelner Court, und die Zeile
    gab es fünfmal.

    Der Fachschlüssel des Imports enthält den Court. Die alten Zeilen
    sehen dadurch aus wie andere Buchungen und werden beim Aktualisieren
    nicht ersetzt, sondern bleiben neben den neuen stehen: derselbe
    Spieltag zweimal, einmal richtig und einmal falsch.

    Entfernt wird eng begrenzt — nur Zeilen mit demselben Tag, derselben
    Startzeit und genau einem der Courts, die dieses Event belegt hat.
    Eine normale Buchung zur selben Zeit auf einem anderen Court bleibt
    unangetastet.

    → Anzahl entfernter Zeilen
    """
    if not eintraege:
        return 0
    b = loadsheet("buchungen")
    noetig = {"analysis_date", "Service_Zeit", "Court"}
    if b.empty or not noetig <= set(b.columns):
        return 0

    ziel = {(str(t), str(z), str(c)) for t, z, c in eintraege}
    schluessel = list(zip(b["analysis_date"].astype(str),
                          b["Service_Zeit"].astype(str),
                          b["Court"].astype(str)))
    behalten = [k not in ziel for k in schluessel]
    entfernt = len(b) - sum(behalten)
    if entfernt:
        savesheet(b[pd.Series(behalten, index=b.index)], "buchungen")
    return entfernt


def _events_zusammenfassen(b: pd.DataFrame) -> pd.DataFrame:
    """
    Die Court-Zeilen eines Events zu einer Veranstaltung zusammenfassen.

    Playtomic schreibt ein Event einmal pro belegtem Court. Der Mexicano
    vom 16.08. steht deshalb fünfmal in der Datei — fünf Zeilen mit
    identischem Preis und identischer Teilnehmerliste. Das ist eine
    Veranstaltung, kein fünffaches Spiel: Ohne Zusammenfassung landet
    jeder Teilnehmer fünfmal in der Auswertung und jeder vergessene
    Check-in fünfmal in den offenen Fällen.

    Die Courts gehen dabei nicht verloren. Wie viele Plätze wie lange
    belegt waren, bleibt in `_ev_courts` erhalten — sonst fehlte dem
    Event später seine Auslastung, obwohl es die halbe Halle blockiert.
    """
    b = b.copy()
    b["_ev_courts"] = 0
    b["_ev_titel"] = ""
    if "_event" not in b.columns:
        b["_event"] = ""
        return b

    ist_ev = b["_event"].astype(str) != ""
    if not ist_ev.any():
        return b

    behalten = set()
    for _, gruppe in b[ist_ev].groupby(["_datum", "_event"], sort=False):
        courts = sorted({str(x) for x in gruppe["_court"]})
        erster = gruppe.index[0]
        b.at[erster, "_ev_courts"] = len(courts)
        b.at[erster, "_ev_titel"] = event_titel(gruppe.iloc[0])
        b.at[erster, "_court"] = ", ".join(courts)
        behalten.add(erster)

    weg = [i for i in b.index[ist_ev] if i not in behalten]
    return b.drop(index=weg)


def _zerlege_zahlung(betrag: float, voll: float, rabattiert: float,
                     max_plaetze: int) -> tuple:
    """
    Aus einem gezahlten Betrag herauslesen, wie viele Plätze darin
    stecken — und wie viele davon rabattiert waren.

    Eine Zahlung deckt nicht zwingend genau einen Platz: Wer für sich
    und einen Mitspieler zahlt, hat beides in einer Summe. Aus dem
    Betrag lässt sich aber zurückrechnen, wie er zustande kam.

    Beispiel bei 13,50 € Platzpreis und 13,00 € Rabatt:
      27,00 €  = 2 volle Plätze, kein Rabatt
       1,00 €  = 2 rabattierte Plätze
      14,00 €  = 1 voller + 1 rabattierter Platz

    → (volle, rabattierte) oder None, wenn der Betrag nicht aufgeht
    """
    if voll <= 0:
        return None
    beste = None
    for k in range(0, max_plaetze + 1):
        for m in range(0, max_plaetze + 1):
            if k + m < 1 or k + m > max_plaetze:
                continue
            if abs(k * voll + m * rabattiert - betrag) < 0.01:
                # Die sparsamste Erklärung gewinnt: möglichst wenige
                # Plätze für den Betrag.
                if beste is None or (k + m) < sum(beste):
                    beste = (k, m)
    return beste


def _wellpass_traeger(teilnehmer, start, pro_platz, n_wellpass, zahlungen,
                      checkin_namen=None, wellpass_bekannt=None) -> set:
    """
    Wer von den Teilnehmern hatte den Rabatt?

    Grundlage sind die Zahlungen — nur dort steht, was geflossen ist.
    Für jede Zahlung wird zurückgerechnet, aus wie vielen vollen und wie
    vielen rabattierten Plätzen sie besteht.

    Dazu kommt die Paar-Struktur: Playtomic listet die Teilnehmer in
    Zweiergruppen (Plätze 1+2 sind ein Paar, 3+4 das andere). Zahlt
    jemand für zwei Plätze, zahlt er für sich und seinen Paar-Partner —
    nicht für irgendwen am Court. Damit lässt sich eine Zahlung genau
    den beiden Menschen zuordnen, die sie betrifft.

    Bleibt innerhalb eines Paares offen, wer von beiden den Rabatt
    hatte, entscheidet ein vorhandener Check-in: Wer eingecheckt hat,
    ist nachweislich Wellpass-Mitglied.

    Die Regel gilt für jede Buchung gleich; es gibt keine
    Sonderbehandlung einzelner Personen.
    """
    roh = [(normalize_name(n), n) for n, _ in teilnehmer]
    namen = [nn for nn, urspr in roh
             if nn not in TEAM_NORM and not ist_platzhalter(urspr)]
    if n_wellpass <= 0 or not namen:
        return set()
    if not zahlungen:
        return set(namen)

    # Wer für diesen Tag überhaupt eine eigene Zahlungszeile hat — nur
    # für die ist der Rabatt aus den Zahlungen heraus belegbar. Ohne
    # jeden Beleg (auch nicht über die Zahlung eines Paar-Partners
    # erklärt) darf niemand als Rabattträger gelten — sonst wird z.B.
    # ein Vereinsname wie „FC Nürnberg" oder ein Gast, dessen Sitzplatz
    # jemand anderes komplett mitbezahlt hat, fälschlich zum
    # Wellpass-Verdächtigen.
    #
    # Vorher galt bei n_wellpass >= Teilnehmerzahl automatisch „sind
    # sowieso alle Träger" — ganz ohne Belegprüfung. Das traf echte
    # Vereins-/Platzhalterbuchungen genauso wie Mitspieler, deren Platz
    # ein anderer bezahlt hat.
    namen_mit_beleg = {nn for nn in namen if zahlungen.get((nn, start)) is not None}

    checkin_namen = checkin_namen or set()
    # Wer irgendwann einmal eingecheckt hat, ist nachweislich
    # Wellpass-Mitglied. Das gilt auch dann noch, wenn er an diesem
    # Tag den Check-in vergessen hat — und genau dann wird das Signal
    # gebraucht.
    wellpass_bekannt = wellpass_bekannt or set()

    # Paare aus der Teilnehmerreihenfolge: (1,2) und (3,4)
    paare = []
    for i in range(0, len(roh), 2):
        gruppe = [nn for nn, urspr in roh[i:i + 2]
                  if nn in namen]
        if gruppe:
            paare.append(gruppe)

    kandidaten = [wellpass_abzug_am(start)]
    for weiterer in CONFIG["wellpass_abzug_alternativen"]:
        if float(weiterer) not in kandidaten:
            kandidaten.append(float(weiterer))

    bestes = None
    for abzug in kandidaten:
        rabattiert = max(0.0, pro_platz - abzug)
        traeger, offen_paare, unklar, erklaerte = set(), [], set(), 0

        for paar in paare:
            # Was hat jeder im Paar bezahlt, und wie viele rabattierte
            # Plätze stecken darin?
            eigene = {}          # nn → (volle, rabattierte)
            unlesbar = set()
            for nn in paar:
                daten = zahlungen.get((nn, start))
                if daten is None:
                    continue
                volle = rabatte_nn = 0
                lesbar = True
                for betrag in (daten.get("werte") or [daten["summe"]]):
                    teil = _zerlege_zahlung(betrag, pro_platz, rabattiert,
                                            len(namen))
                    if teil is None:
                        lesbar = False
                        break
                    volle += teil[0]
                    rabatte_nn += teil[1]
                if lesbar:
                    eigene[nn] = (volle, rabatte_nn)
                else:
                    unlesbar.add(nn)

            # Wer weder selbst gezahlt hat noch von einem lesbaren
            # Zahlungsbetrag erfasst ist, bleibt offen.
            ohne_beleg = [nn for nn in paar
                          if nn not in eigene and nn not in unlesbar]
            unklar.update(unlesbar)

            if not eigene:
                unklar.update(ohne_beleg)
                continue

            rabatte = sum(m for _, m in eigene.values())
            plaetze_gedeckt = sum(k + m for k, m in eigene.values())
            erklaerte += rabatte

            # Deckt die Zahlung des Paares alle seine Plätze ab, sind die
            # Mitgenommenen erklärt — sonst bleiben sie offen.
            alle_gedeckt = plaetze_gedeckt >= len(paar) - len(unlesbar)
            if not alle_gedeckt:
                unklar.update(ohne_beleg)

            if rabatte == 0:
                continue                      # dieses Paar zahlte voll

            # Die eigene Zahlung wiegt am schwersten: Wer bezahlt, zahlt
            # seinen eigenen Platz zum eigenen Tarif und die Plätze der
            # Mitgenommenen zum vollen Preis. Enthält seine Zahlung also
            # einen rabattierten Platz, ist das seiner.
            #
            # Beispiel: 4,50 € + 16,50 € auf einem Namen heisst — eigener
            # Platz mit Rabatt, ein voller Platz für jemanden mitbezahlt.
            mitgenommen = [nn for nn in paar
                           if nn not in eigene and nn not in unlesbar]
            uebrig = 0

            for nn, (_, m) in eigene.items():
                if m > 0:
                    traeger.add(nn)
                    uebrig += m - 1       # weitere Rabatte für Mitgenommene

            if uebrig <= 0:
                # Alle Rabatte sind den Zahlern zugeordnet — die
                # Mitgenommenen haben Vollpreis gekostet.
                continue

            if uebrig >= len(mitgenommen):
                traeger.update(mitgenommen)
                continue

            # Mehr Mitgenommene als übrige Rabatte — wer war es?
            eingecheckt = [nn for nn in mitgenommen if nn in checkin_namen]
            mitglieder = [nn for nn in mitgenommen if nn in wellpass_bekannt]
            if len(eingecheckt) == uebrig:
                traeger.update(eingecheckt)          # Check-in an dem Tag
            elif len(mitglieder) == uebrig:
                traeger.update(mitglieder)           # bekannte Mitglieder
            else:
                offen_paare.append(mitgenommen)

        if (not unklar and not offen_paare
                and erklaerte == n_wellpass and len(traeger) == n_wellpass):
            return traeger

        rest = traeger | unklar | {nn for paar in offen_paare for nn in paar}
        if bestes is None or len(rest) < len(bestes):
            bestes = rest

    # Bleibt es nach allen Abzug-Kandidaten unklar, wird nur noch
    # jemand mit eigenem Zahlungsbeleg als Träger geführt — alles
    # andere wäre eine Vermutung ohne Nachweis.
    ergebnis = bestes if bestes is not None else set(namen)
    return ergebnis & namen_mit_beleg

def _als_rohbuchungen(tage=None) -> pd.DataFrame:
    """
    Aus den gespeicherten Buchungszeilen wieder eine Rohtabelle bauen.

    Grundlage für das Neuberechnen: Die Zeilen einer Buchung teilen sich
    Datum, Uhrzeit und Court — daran lassen sie sich wieder zu einer
    Buchung mit ihren Teilnehmern zusammenfassen. Die Reihenfolge der
    Zeilen bleibt erhalten, weil davon die Paar-Zuordnung abhängt.
    """
    b = loadsheet("buchungen")
    if b.empty or "analysis_date" not in b.columns:
        return pd.DataFrame()

    if tage:
        b = b[b["analysis_date"].astype(str).isin({str(t) for t in tage})]
    if b.empty:
        return pd.DataFrame()

    zeilen = []
    schluessel = ["analysis_date", "Service_Zeit", "Court"]
    for (tag, zeit, court), gruppe in b.groupby(schluessel, sort=False):
        erste = gruppe.iloc[0]
        dauer = pd.to_numeric(erste.get("Dauer"), errors="coerce")
        if pd.isna(dauer) or dauer <= 0:
            # Altbestand ohne Dauer: aus dem alten Listenpreis
            # zurückrechnen. Der wurde mit dem Tarif der Startzeit
            # gerechnet, also ist die Umkehrung eindeutig.
            start = parse_datetime_safe(f"{tag} {zeit}")
            satz = stundensatz(start, ist_single_court(str(court))) if start else 0
            liste_alt = parse_betrag(erste.get("Listenpreis"))
            dauer = round(liste_alt / satz * 60) if satz else 90

        ist_event = str(erste.get("Event", "")) == "Ja"

        eintrag = {
            "booking_start_date": f"{tag}T{zeit}",
            "price": f"{parse_betrag(erste.get('Bezahlt'))} EUR",
            "resource_name": str(court),
            "duration (minutes)": int(dauer),
            "is_canceled": "false",
        }

        # Ein Event muss vollständig zurückgebaut werden, sonst frisst
        # das Neuberechnen die Veranstaltung auf: ohne `booking_type`
        # und `activity_id` gilt sie wieder als normale Buchung, und
        # ohne die Court-Zeilen fehlt ihr die Auslastung. Die Grenze von
        # vier Teilnehmern würde ausserdem 16 von 20 Leuten löschen.
        grenze = 4
        if ist_event:
            grenze = EVENT_MAX_PLAETZE
            eintrag["booking_type"] = "OPEN_PLAY"
            eintrag["activity_id"] = str(erste.get("Event_Id", "") or f"ev-{tag}-{zeit}")
            eintrag["activity_name"] = str(erste.get("Event_Name", "") or "Event")

        for i, (_, r) in enumerate(gruppe.iterrows(), start=1):
            if i > grenze:
                break
            eintrag[f"participant_name_{i}"] = str(r.get("Name", ""))
            eintrag[f"participant_email_{i}"] = str(r.get("Email", "") or "")

        if ist_event:
            # Je belegtem Court eine Zeile — genau die Form, in der
            # Playtomic das Event geliefert hat.
            courts = [c.strip() for c in str(court).split(",") if c.strip()]
            for einzel in (courts or [str(court)]):
                kopie = dict(eintrag)
                kopie["resource_name"] = einzel
                zeilen.append(kopie)
        else:
            zeilen.append(eintrag)

    return pd.DataFrame(zeilen)


def _als_rohcheckins(tage=None) -> pd.DataFrame:
    """Gespeicherte Check-ins zurück ins Rohformat."""
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns:
        return pd.DataFrame()
    if tage:
        c = c[c["analysis_date"].astype(str).isin({str(t) for t in tage})]
    if c.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "Vor- & Nachname": c["Name"].astype(str),
        "Datum": c["analysis_date"].astype(str),
        "Zeit": c.get("Checkin_Zeit", pd.Series([""] * len(c))).astype(str),
    })


def neu_berechnen(tage=None) -> bool:
    """
    Die Auswertung aus den gespeicherten Daten neu rechnen.

    Nötig, wenn sich die Rechenregeln geändert haben — Preise, Tarife,
    Wellpass-Abzug. Die Rohdaten bleiben, nur die abgeleiteten Spalten
    werden ersetzt.

    Unberührt bleiben: erledigte Fälle, bestätigte Namensverknüpfungen
    und zugeordnete Nachholungen. Die stehen in eigenen Blättern und
    werden hier nicht angefasst.
    """
    roh_b = _als_rohbuchungen(tage)
    roh_c = _als_rohcheckins(tage)
    if roh_b.empty:
        st.error("❌ Keine gespeicherten Buchungen zum Neuberechnen.")
        return False
    if roh_c.empty:
        # Ohne Check-ins wäre jede Buchung ein Fall — das wäre Unsinn
        st.error("❌ Für diesen Zeitraum sind keine Check-ins gespeichert.")
        return False

    # WICHTIG: Hier wird bewusst NICHT vorab gelöscht.
    #
    # Früher wurden die betroffenen Tage zuerst aus „buchungen“ und
    # „checkins“ entfernt (bei „Alle Tage“ blieb dabei buchstäblich
    # nichts übrig — das ganze Blatt wurde geleert) und erst danach neu
    # befüllt. Schlug irgendetwas dazwischen fehl — ein Google-Limit,
    # ein Verbindungsabbruch, irgendein Fehler in der Berechnung —, blieb
    # das Blatt leer. Genau das hat die Daten einmal komplett gelöscht.
    #
    # _analysieren() schreibt seine Zeilen über append_rows(...,
    # aktualisieren=True) — das ersetzt vorhandene Zeilen mit
    # übereinstimmendem Schlüssel (Tag+Name+Zeit+Court) UND behält den
    # Rest, in einem einzigen Schreibvorgang. Kein Zwischenzustand, in
    # dem das Blatt leer wäre. Einziger Kompromiss: fällt eine Buchung
    # durch die Neuberechnung ganz weg (kein neuer Treffer mit demselben
    # Schlüssel), bleibt ihre alte Zeile stehen, statt gelöscht zu
    # werden — das lässt sich bei Bedarf über „Einzelne Tage entfernen“
    # nachträglich bereinigen. Deutlich harmloser als ein leeres Blatt.
    zahlungen = _zahlungs_index(loadsheet("playtomic_raw"))
    erfolg = _analysieren(roh_b, roh_c, None, zahlungen_index=zahlungen)
    if erfolg:
        cache_leeren()
    return erfolg


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

    pdf = parse_playtomic(p_datei) if p_datei is not None else None
    return _analysieren(bdf, cdf, pdf)


def _analysieren(bdf, cdf, pdf=None, zahlungen_index=None) -> bool:
    """
    Der eigentliche Abgleich — getrennt vom Einlesen, damit dieselbe
    Rechnung auch auf bereits gespeicherte Daten angewandt werden kann
    (Knopf „Neu berechnen").
    """
    # ── Zahlungen (optional: Umsatz + präzise Wellpass-Zuordnung) ──────
    neu_raw = 0
    zahlungen = zahlungen_index or {}
    if pdf is not None and not pdf.empty:
        neu_raw = append_rows(pdf, "playtomic_raw", id_spalte="Payment id")
        if not zahlungen:
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
    if "booking_end_date" in b.columns:
        b["_ende"] = b["booking_end_date"].map(parse_datetime_safe)
    else:
        b["_ende"] = pd.Series([None] * len(b), index=b.index)

    # Spieldauer bestimmen.
    #
    # Playtomic liefert die Spalte „duration (minutes)" nicht in jedem
    # Export. Fehlt sie, wird die Dauer aus Anfangs- und Endzeit
    # berechnet; erst wenn auch das nicht geht, greift der Standardwert.
    # Vorher brach der Import an dieser Stelle ab.
    if "duration (minutes)" in b.columns:
        b["_min"] = pd.to_numeric(b["duration (minutes)"], errors="coerce")
    else:
        b["_min"] = pd.Series([float("nan")] * len(b), index=b.index)

    aus_zeiten = [
        (ende - start).total_seconds() / 60.0
        if (start is not None and ende is not None and ende > start) else None
        for start, ende in zip(b["_start"], b["_ende"])]
    b["_min"] = b["_min"].fillna(pd.Series(aus_zeiten, index=b.index))

    # Unplausible Werte verwerfen — sonst stimmt der Listenpreis nicht
    b.loc[(b["_min"] < 15) | (b["_min"] > 600), "_min"] = float("nan")
    b["_min"] = b["_min"].fillna(CONFIG.get("standard_dauer_minuten", 90))

    b["_single"] = b["resource_name"].map(ist_single_court)
    b["_court"] = b["resource_name"].astype(str)

    # ── Events erkennen und zusammenfassen ──────────────────────────────
    b["_event"] = [event_kennung(r) for _, r in b.iterrows()]
    b = _events_zusammenfassen(b)

    # Event-Zahlungen stehen unter eigener SKU und fehlen im normalen
    # Zahlungs-Index. Nur laden, wenn überhaupt ein Event dabei ist.
    event_zahlungen = {}
    if (b["_event"].astype(str) != "").any():
        quelle = pdf if (pdf is not None and not pdf.empty) else loadsheet("playtomic_raw")
        if quelle is not None and not quelle.empty:
            event_zahlungen = _event_zahlungs_index(quelle)

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
    # Check-ins, die bereits als Nachholung einen älteren Fall geschlossen
    # haben. Sie sind aufgebraucht und dürfen ihren eigenen Tag nicht
    # noch einmal decken.
    verbraucht = verbrauchte_checkins()

    # Alle Namen, die je eingecheckt haben — inklusive der bestätigten
    # Schreibvarianten. Beleg dafür, dass jemand Wellpass-Mitglied ist.
    alle_wellpass = set(c["Name_norm"].astype(str)) if not c.empty else set()
    for buchung_name, ziel in mapping.items():
        gname = str(ziel["checkin_name"] if isinstance(ziel, dict) else ziel)
        if gname in alle_wellpass:
            alle_wellpass.add(str(buchung_name))

    b_tag = dict(tuple(b.groupby("_datum")))
    c_tag = dict(tuple(c.groupby("Checkin_Datum")))

    buchungen_out, checkins_out, kunden_out = [], [], []
    # Welche Court-Einzelzeilen ein Event ersetzt — siehe
    # _event_altzeilen_entfernen.
    event_altzeilen = []

    for i, tag in enumerate(alle_tage):
        balken.progress((i + 1) / len(alle_tage))
        status.caption(f"{tag.strftime('%d.%m.%Y')} · {i+1}/{len(alle_tage)}")

        bt = b_tag.get(tag, pd.DataFrame())
        ct = c_tag.get(tag, pd.DataFrame())
        checkin_namen = set(ct["Name_norm"]) if not ct.empty else set()
        zeit_je_name = (dict(zip(ct["Name_norm"], ct["Checkin_Zeit"]))
                        if not ct.empty else {})
        schon_zugeordnet = set()

        # ── Ein Check-in pro Person und Tag ──────────────────────────────
        #
        # EGYM vergütet pro Person und Tag genau einmal. Also kann ein
        # Check-in auch nur EINEN rabattierten Platz decken. Wer am selben
        # Tag zweimal mit Wellpass-Rabatt spielt, hat beim zweiten Mal
        # einen ungedeckten Rabatt — obwohl er eingecheckt hat.
        #
        # Vorher war das eine reine Mitgliedschaftsprüfung: derselbe
        # Check-in galt für jede Buchung des Tages. Der zweite Rabatt
        # fiel damit durchs Raster.
        checkin_frei = set(checkin_namen)

        # Check-ins, die schon einen älteren Fall geschlossen haben, sind
        # verbraucht — sie decken ihren eigenen Tag nicht mehr.
        for nn_ci in list(checkin_frei):
            ziel = verbraucht.get(checkin_schluessel(str(tag), nn_ci))
            if ziel and not str(ziel).startswith(f"{tag}|"):
                checkin_frei.discard(nn_ci)

        def _checkin_name(nn_roh):
            """Welcher Check-in-Name gehört zu diesem Spieler?"""
            if nn_roh in checkin_frei:
                return nn_roh
            if nn_roh in mapping:
                g = mapping[nn_roh]
                gname = g["checkin_name"] if isinstance(g, dict) else g
                if gname in checkin_frei:
                    return gname
            return None

        def _buchung_zaehlt(row_b) -> bool:
            """Zählt diese Buchung für die Wellpass-Rechnung?"""
            tn = _teilnehmer_liste(row_b, _zeilen_plaetze(row_b))
            if not tn:
                return False
            namen = [normalize_name(n) for n, _ in tn]
            if any(k in namen[0] for k in ("schule", "gruppe", "kurs",
                                           "training", "turnier")):
                return False
            return not all(n in TEAM_NORM for n in namen)

        # Spielt jemand mehrfach am Tag, zählt der Check-in für die
        # Buchung, die zeitlich am nächsten liegt.
        if not bt.empty:
            bt = bt.sort_values("_start")
        besitzer = {}
        for pos, (_, row_b) in enumerate(bt.iterrows()):
            if not _buchung_zaehlt(row_b):
                # Team-, Schul- und Gruppenbuchungen haben keinen
                # Wellpass-Rabatt. Ein Check-in an so einem Tag gehört
                # zu keinem Anspruch und bleibt deshalb bewusst als
                # überzählig sichtbar — auch bei Mitarbeitern.
                continue
            for name_b, _m in _teilnehmer_liste(row_b, _zeilen_plaetze(row_b)):
                ziel = _checkin_name(normalize_name(name_b))
                if ziel is None:
                    continue
                schon_zugeordnet.add(ziel)
                ci_std = stunde_aus_zeit(zeit_je_name.get(ziel, ""))
                abstand = (abs(ci_std - row_b["_start"].hour)
                           if ci_std >= 0 else 99)
                if ziel not in besitzer or abstand < besitzer[ziel][1]:
                    besitzer[ziel] = (pos, abstand)

        for pos, (_, row) in enumerate(bt.iterrows()):
            ev_id = str(row.get("_event", "") or "")
            teilnehmer = _teilnehmer_liste(row, _zeilen_plaetze(row))
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

            ev_person, ev_titel_txt, ev_unsicher = {}, "", False

            if ev_id:
                # ── Event ────────────────────────────────────────────────
                # Preis und Rabatt kommen aus den Zahlungen des Events
                # selbst. Der Stundentarif gilt hier nicht, und `price`
                # der Zeile ist der Gesamtumsatz der Veranstaltung —
                # daraus einen Platzpreis zu rechnen ergab bisher einen
                # negativen Rabatt und damit null erkannte Wellpässe.
                #
                # Anders als bei einer Buchung wird hier pro Kopf
                # gerechnet: Jede Zahlung steht einzeln in den Rohdaten,
                # es muss also nichts aus einer Summe zurückgerechnet
                # werden.
                ev_titel_txt = str(row.get("_ev_titel", "") or "Event")
                for einzel in str(row["_court"]).split(", "):
                    if einzel.strip():
                        event_altzeilen.append(
                            (str(tag), str(row["_zeit"]), einzel.strip()))
                ende = (row["_ende"] if pd.notna(row["_ende"])
                        else row["_start"] + timedelta(minutes=float(row["_min"])))
                # Der Zahlungs-Zeitstempel eines Events ist dessen Ende,
                # nicht der Beginn. Ein grosszügiges Fenster fängt beide
                # Schreibweisen ab und trennt trotzdem zwei Events, die
                # am selben Tag zu verschiedenen Zeiten laufen.
                von, bis = row["_start"] - timedelta(hours=2), ende + timedelta(hours=2)
                fenster = {nn_z: d for nn_z, d in event_zahlungen.get(tag, {}).items()
                           if von <= d["dt"] <= bis}
                vollpreis, rabatte, sicher = _event_rabatte(fenster)
                ev_unsicher = not sicher

                liste = vollpreis
                plaetze = len(teilnehmer)
                pro_platz = vollpreis
                for nn_t in namen_norm:
                    bez = fenster.get(nn_t, {}).get("betrag")
                    rab = float(rabatte.get(nn_t, 0.0))
                    # Ohne Zahlungsbeleg kein Rabattverdacht — genau wie
                    # bei einer normalen Buchung.
                    ev_person[nn_t] = (bez if bez is not None else vollpreis, rab,
                                       bool(sicher and bez is not None and rab > 0.5))
                n_wellpass = sum(1 for v in ev_person.values() if v[2])
            else:
                liste = listenpreis(row["_start"], row["_min"], bool(row["_single"]))
                plaetze = court_plaetze(row["_court"])
                pro_platz = round(liste / max(plaetze, 1), 2)

                # Sitzt jemand vom Team mit drin, zahlt der 0 € — dessen Platz
                # darf nicht als Wellpass-Rabatt gezählt werden.
                #
                # Bei einem Event gilt das ausdrücklich NICHT: Dort zahlt
                # auch ein Dauergast echtes Startgeld. Würde sein Platz
                # hier abgezogen, verschöben sich die Preisstufen für
                # alle anderen. Aus der Nachrichten-Logik bleibt er
                # trotzdem heraus — das entscheidet `team` weiter unten.
                team_im_spiel = sum(1 for n in namen_norm if n in TEAM_NORM)
                liste_effektiv = liste - team_im_spiel * pro_platz
                n_wellpass = wellpass_anzahl(liste_effektiv, row["_preis"],
                                             max(plaetze - team_im_spiel, 1),
                                             datum=tag)

            # Wer von den Teilnehmern hat eingecheckt?
            eingecheckt = []
            for name, _mail in teilnehmer:
                ziel = _checkin_name(normalize_name(name))
                if ziel is None:
                    continue
                # Er war da — der Check-in gehört zu einer Buchung und
                # taucht deshalb nicht als überzählig auf.
                schon_zugeordnet.add(ziel)
                # Gutgeschrieben wird er aber nur einmal, bei der
                # zeitlich passenden Buchung.
                if besitzer.get(ziel, (None, 0))[0] == pos:
                    eingecheckt.append(ziel)

            fehlend = max(0, n_wellpass - len(eingecheckt))
            # Check-ins des Tages mitgeben: Wer eingecheckt hat, ist
            # nachweislich Wellpass-Mitglied — das entscheidet, wenn
            # innerhalb eines Paares offen bleibt, wer den Rabatt hatte.
            if ev_id:
                # Beim Event ist der Träger direkt belegt: Er hat
                # nachweislich weniger gezahlt als der Vollzahler. Die
                # Rückrechnung aus Paaren und Sammelzahlungen, die eine
                # Buchung nötig macht, entfällt hier komplett.
                traeger = {nn_t for nn_t, v in ev_person.items() if v[2]}
            else:
                traeger = _wellpass_traeger(teilnehmer, row["_start"], pro_platz,
                                            n_wellpass, zahlungen,
                                            checkin_namen=checkin_namen,
                                            wellpass_bekannt=alle_wellpass)

            for name, mail in teilnehmer:
                nn = normalize_name(name)
                hat_checkin = nn in eingecheckt or (
                    nn in mapping and
                    (mapping[nn]["checkin_name"] if isinstance(mapping[nn], dict)
                     else mapping[nn]) in eingecheckt)
                team = nn in TEAM_NORM
                platzhalter = ist_platzhalter(name)

                # Fehler: hatte nachweislich den Rabatt, keinen Check-in,
                # gehört nicht zum Team.
                # Sicherung: ohne echten Preisnachlass gibt es nichts zu melden.
                #
                # Platzhalter wie „Player 2" sind ausgenommen: die haben
                # keine Nummer, keine E-Mail und keinen Wellpass. Wer da
                # wirklich gespielt hat, weiss nur der Buchende.
                if ev_id:
                    # Beim Event steht der Preis pro Kopf einzeln in den
                    # Rohdaten — jede Zeile trägt deshalb ihren eigenen
                    # Betrag statt eines auf die Plätze geteilten
                    # Buchungspreises.
                    p_bezahlt, p_rabatt, p_wellpass = ev_person.get(
                        nn, (liste, 0.0, False))
                    p_liste, p_betrag = liste, p_bezahlt
                    p_rabatte_n = 1 if p_wellpass else 0
                    p_relevant = p_wellpass
                    fehler = (p_wellpass and not hat_checkin
                              and not team and not platzhalter)
                else:
                    p_liste, p_bezahlt, p_betrag = liste, row["_preis"], pro_platz
                    p_rabatte_n = n_wellpass
                    p_relevant = n_wellpass > 0
                    echter_nachlass = (liste - row["_preis"]) > 0.5
                    fehler = (echter_nachlass and fehlend > 0 and nn in traeger
                              and not hat_checkin and not team and not platzhalter)

                buchungen_out.append({
                    "Datum": str(tag),
                    "Name": name,
                    "Name_norm": nn,
                    "Email": mail,
                    "Court": row["_court"],
                    "Service_Zeit": row["_zeit"],
                    "Dauer": int(row["_min"]),
                    "Listenpreis": p_liste,
                    "Bezahlt": p_bezahlt,
                    "Betrag": p_betrag,
                    "Plaetze": plaetze,
                    "Wellpass_Rabatte": p_rabatte_n,
                    "Teilnehmer": len(teilnehmer),
                    "Checkin_Zeit": zeit_je_name.get(nn, ""),
                    "Relevant": "Ja" if p_relevant else "Nein",
                    # Event-Merkmale — auch für spätere Auswertungen:
                    # Auslastung (wie viele Courts wie lange belegt) und
                    # Wiederkehrer-Vergleich vor/nach einer Veranstaltung.
                    "Event": "Ja" if ev_id else "Nein",
                    "Event_Name": ev_titel_txt,
                    "Event_Id": ev_id,
                    "Event_Courts": int(row.get("_ev_courts", 0) or 0),
                    "Event_Unklar": "Ja" if (ev_id and ev_unsicher) else "Nein",
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

    # aktualisieren=True: ein erneut hochgeladener Tag überschreibt die
    # alte Auswertung, statt als Dublette übersprungen zu werden.
    # Erst die überholten Court-Einzelzeilen des Events wegräumen, dann
    # schreiben — sonst stünde derselbe Spieltag doppelt in der Tabelle.
    _event_altzeilen_entfernen(event_altzeilen)

    neu_b = append_rows(pd.DataFrame(buchungen_out), "buchungen",
                        ["analysis_date", "Name_norm", "Service_Zeit", "Court"],
                        aktualisieren=True)
    neu_c = append_rows(pd.DataFrame(checkins_out), "checkins",
                        ["analysis_date", "Name_norm", "Checkin_Zeit"],
                        aktualisieren=True)

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

    # Eindeutige Namenszuordnungen gleich mit erledigen — das sind reine
    # Schreibweisen-Unterschiede und müssen dir nicht vorgelegt werden.
    auto = []
    if einstellung("auto_zuordnung_an", True):
        try:
            auto = auto_zuordnungen_uebernehmen()
        except Exception:
            auto = []

    st.success(f"✅ {neu_b} Buchungszeilen · {neu_c} Check-ins · "
               f"{neu_k} Kunden ergänzt"
               + (f" · {neu_raw} Zahlungszeilen" if neu_raw else ""))
    if auto:
        box(f"⚡ <b>{len(auto)} eindeutige Namenszuordnungen</b> wurden "
            "gleich mit übernommen. Nachsehen und zurücknehmen kannst du "
            "sie unter Name-Abgleich → Gelernte Zuordnungen.", "ok")
    if neu_b or neu_c:
        st.balloons()
    else:
        box("Alle Daten waren bereits im System.", "info")
    return True


def tage_entfernen(tage: list) -> dict:
    """
    Buchungen, Check-ins und Zahlungen einzelner Tage löschen.

    Für den Fall, dass ein Tag falsch verarbeitet wurde: löschen,
    Exporte für den Zeitraum neu hochladen, fertig. Erledigte Fälle,
    Verknüpfungen und Nachholungen bleiben unberührt.
    """
    ziel = {str(t) for t in tage}
    entfernt = {}

    for blatt in ("buchungen", "checkins"):
        df = loadsheet(blatt)
        if df.empty or "analysis_date" not in df.columns:
            continue
        behalten = df[~df["analysis_date"].astype(str).isin(ziel)]
        entfernt[blatt] = len(df) - len(behalten)
        if entfernt[blatt]:
            savesheet(behalten, blatt)

    # Zahlungen tragen ihr Datum in "Service date"
    roh = loadsheet("playtomic_raw")
    if not roh.empty and "Service date" in roh.columns:
        tag_spalte = roh["Service date"].map(
            lambda w: str(parse_datetime_safe(w).date())
            if parse_datetime_safe(w) else "")
        behalten = roh[~tag_spalte.isin(ziel)]
        entfernt["playtomic_raw"] = len(roh) - len(behalten)
        if entfernt["playtomic_raw"]:
            savesheet(behalten, "playtomic_raw")

    st.session_state["_auto_erledigt"] = set()
    st.session_state["_auto_protokoll"] = []
    cache_leeren()
    return entfernt


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
                    "so hoch wie der Mittelwert. Meist stecken dahinter "
                    "Dubletten aus überschneidenden Exporten.", "warn")

            pruef = betraege_verdaechtig()
            if pruef["betroffen"]:
                box(f"⚠️ <b>Beträge vermutlich verfälscht.</b> "
                    f"{pruef['anteil']:.0f} % der Zahlungen liegen über 100 € — "
                    "bei Court-Anteilen ist das unrealistisch.<br><br>"
                    "Ursache: Google Sheets liest „13,5“ als 135, weil es das "
                    "Komma als Tausendertrennzeichen deutet. Zurückrechnen lässt "
                    "sich das nicht sicher.<br><br>"
                    "<b>Lösung:</b> unten <i>Daten zurücksetzen → Zahlungen</i> "
                    "wählen und den Monatsexport einmal neu hochladen. Die "
                    "neue Version schreibt die Beträge eindeutig.", "err")

            st.markdown("")
            st.markdown("**Dubletten bereinigen**")
            st.caption("Entfernt doppelte Zeilen, die vor der Umstellung "
                       "entstanden sind. Es gehen keine echten Daten verloren — "
                       "nur exakte Kopien werden entfernt.")
            if st.button("🧹 Jetzt bereinigen", type="primary",
                         use_container_width=True):
                with st.spinner("Prüfe alle Datenblätter…"):
                    ergebnis = []
                    for blatt, idsp in (("playtomic_raw", "Payment id"),
                                        ("buchungen", None),
                                        ("checkins", None)):
                        vor, nach = dubletten_bereinigen(blatt, idsp)
                        if vor != nach:
                            ergebnis.append(f"{blatt}: {vor} → {nach}")
                if ergebnis:
                    st.success("✅ Bereinigt · " + " · ".join(ergebnis))
                else:
                    st.info("Keine Dubletten gefunden — die Daten sind sauber.")
                st.rerun()

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
                st.toast("Cache geleert.")
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
        with st.expander("🔄 Neu berechnen", expanded=False):
            box("Rechnet die Auswertung aus den gespeicherten Daten neu — "
                "ohne dass du etwas hochladen musst. Sinnvoll, wenn sich "
                "Preise, Tarife oder der Wellpass-Abzug geändert haben.",
                "info")

            n1, n2 = st.columns(2)
            with n1:
                st.markdown("**Wird neu gerechnet**")
                st.caption("· Listenpreis\n\n· erkannte Wellpass-Rabatte\n\n"
                           "· wer den Rabatt hatte\n\n· offene Fälle")
            with n2:
                st.markdown("**Bleibt unberührt**")
                st.caption("· erledigte Fälle mit Grund\n\n"
                           "· gelernte Namenszuordnungen\n\n"
                           "· zugeordnete Nachholungen\n\n"
                           "· Zahlungen und Kundenliste")

            tage_alle = verfuegbare_tage()
            if not tage_alle:
                box("Noch keine Daten im System.", "info")
            else:
                umfang = st.radio(
                    "Umfang", ["Alle Tage", "Einzelne Tage wählen"],
                    horizontal=True, key="neu_umfang",
                    label_visibility="collapsed")
                ziel = (None if umfang == "Alle Tage"
                        else st.multiselect("Tage", tage_alle,
                                            format_func=datum_lang,
                                            key="neu_tage"))
                anzahl = len(tage_alle) if ziel is None else len(ziel)
                if anzahl:
                    st.caption(f"{anzahl} "
                               + ("Tag" if anzahl == 1 else "Tage")
                               + " werden neu gerechnet.")
                    if st.button(f"🔄 {anzahl} "
                                 + ("Tag" if anzahl == 1 else "Tage")
                                 + " neu berechnen", type="primary",
                                 use_container_width=True, key="neu_start"):
                        if neu_berechnen(ziel):
                            st.rerun()

        st.markdown("---")
        with st.expander("📆 Einzelne Tage entfernen"):
            box("Wenn ein einzelner Tag falsch verarbeitet wurde: hier "
                "löschen und die Exporte für den Zeitraum neu hochladen. "
                "Erledigte Fälle, Verknüpfungen und Nachholungen bleiben "
                "erhalten.", "info")

            tage = verfuegbare_tage()
            if not tage:
                box("Noch keine Tage im System.", "info")
            else:
                schnell = st.radio(
                    "Auswahl", ["Gestern", "Heute", "Letzte 7 Tage",
                                "Selbst wählen"],
                    horizontal=True, key="loesch_modus",
                    label_visibility="collapsed")

                heute = date.today()
                if schnell == "Gestern":
                    wahl = [t for t in tage
                            if t == str(heute - timedelta(days=1))]
                elif schnell == "Heute":
                    wahl = [t for t in tage if t == str(heute)]
                elif schnell == "Letzte 7 Tage":
                    grenze = str(heute - timedelta(days=7))
                    wahl = [t for t in tage if t >= grenze]
                else:
                    wahl = st.multiselect("Tage", tage, format_func=datum_lang,
                                          key="loesch_tage")

                if not wahl:
                    box("Für diese Auswahl liegen keine Daten vor.", "info")
                else:
                    zeilen = sum(len(tag_details(t)) for t in wahl)
                    st.caption(f"Betroffen: {len(wahl)} "
                               + ("Tag" if len(wahl) == 1 else "Tage")
                               + f" · {zeilen} Buchungszeilen")
                    for t in wahl[:7]:
                        st.caption(f"· {datum_lang(t)}")
                    if len(wahl) > 7:
                        st.caption(f"· … und {len(wahl) - 7} weitere")

                    if st.button(f"🗑 {len(wahl)} "
                                 + ("Tag" if len(wahl) == 1 else "Tage")
                                 + " entfernen", type="primary",
                                 use_container_width=True, key="loesch_ok"):
                        raus = tage_entfernen(wahl)
                        st.toast("Entfernt: "
                                 + " · ".join(f"{v} {k}"
                                              for k, v in raus.items() if v))
                        st.rerun()

        st.markdown("---")
        with st.expander("🧹 Daten zurücksetzen und neu hochladen"):
            box("Der saubere Weg, wenn die Auswertung nicht mehr stimmt: "
                "Rohdaten leeren, Exporte neu hochladen. Die App rechnet "
                "dann alles mit der aktuellen Logik durch.", "warn")

            b1, b2 = st.columns(2)
            with b1:
                st.markdown("**Wird geleert**")
                st.caption("· Zahlungen\n\n· Buchungen\n\n· Check-ins")
            with b2:
                st.markdown("**Bleibt erhalten**")
                st.caption("· gelernte Namenszuordnungen\n\n"
                           "· erledigte Fälle mit Grund\n\n"
                           "· zugeordnete Nachholungen\n\n"
                           "· Kundenliste mit Telefonnummern")

            was = st.selectbox("Was soll geleert werden?", [
                "Alles außer Zuordnungen",
                "Buchungen und Check-ins",
                "Zahlungen (Umsatzbasis)",
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
                # Sitzungssperre der Automatik lösen — nach dem Neuaufbau
                # sollen die Zuordnungen wieder greifen dürfen
                st.session_state["_auto_erledigt"] = set()
                st.session_state["_auto_protokoll"] = []
                cache_leeren()
                st.toast(f"Geleert: {', '.join(ziele)}")
                st.rerun()

            st.markdown("")
            st.caption("Danach unter *Buchungen + Check-ins* pro Zeitraum "
                       "hochladen: erst Bookings, dann Payments, dann "
                       "Check-ins. Mehrere Monate gehen nacheinander — "
                       "die App erkennt Dubletten selbst.")

        # ── Erledigte Fälle aufräumen ───────────────────────────────────
        with st.expander("✅ Erledigte Fälle aufräumen"):
            alle = erledigte_faelle()
            weg = redundante_korrekturen()

            box("Fälle, die du durch eine <b>Namensverknüpfung</b> geschlossen "
                "hast, lösen sich von selbst — die Verknüpfung ist gespeichert "
                "und greift bei jedem Durchlauf neu. Diese Einträge sind "
                "überflüssig.<br><br>"
                "<b>Nicht angetastet werden:</b> Nachholungen von einem "
                "anderen Tag und alles, was du von Hand entschieden hast — "
                "nicht gespielt, bezahlt, Kulanz. Das lässt sich nicht "
                "rekonstruieren.", "info")

            a1, a2 = st.columns(2)
            with a1:
                kpi("Erledigte Fälle", str(len(alle)))
            with a2:
                kpi("Davon überflüssig", str(len(weg)),
                    "durch Verknüpfung gedeckt")

            if weg.empty:
                box("Nichts aufzuräumen — jeder Eintrag trägt eine "
                    "Entscheidung, die sonst verloren ginge.", "ok")
            else:
                with st.expander(f"Die {len(weg)} Einträge ansehen"):
                    zeig = weg[["datum", "Name", "grund_label"]].copy()
                    zeig.columns = ["Spieltag", "Spieler", "Grund"]
                    st.dataframe(zeig, use_container_width=True,
                                 hide_index=True, height=260)
                if st.button(f"🧹 {len(weg)} überflüssige Einträge entfernen",
                             use_container_width=True, key="corr_aufraeumen"):
                    n = korrekturen_aufraeumen()
                    st.toast(f"{n} Einträge entfernt.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#   📊  MODUL · DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def _dash_tag():
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten. Starte in der Daten-Zentrale.", "warn")
        return

    # Der Wert der Selectbox ist die einzige Wahrheit.
    #
    # Vorher lief die Auswahl über einen eigenen Index. Streamlit merkt sich
    # den Wert eines Widgets mit festem key aber über den Neuaufbau hinweg —
    # der gemerkte Wert hat den vom Knopf gesetzten Index sofort wieder
    # überschrieben. Deshalb bewegte sich das Datum nicht.
    if ("tag_wahl" not in st.session_state
            or st.session_state.tag_wahl not in tage):
        st.session_state.tag_wahl = tage[0]

    idx = tage.index(st.session_state.tag_wahl)

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Früher", use_container_width=True,
                     disabled=idx >= len(tage) - 1, key="tag_frueher"):
            st.session_state.tag_wahl = tage[idx + 1]
            st.rerun()
    with c3:
        if st.button("Später →", use_container_width=True,
                     disabled=idx <= 0, key="tag_spaeter"):
            st.session_state.tag_wahl = tage[idx - 1]
            st.rerun()

    with c2:
        datum = st.selectbox(
            "Tag", tage, format_func=datum_lang,
            label_visibility="collapsed", key="tag_wahl")

    st.markdown("")
    k = tages_kennzahlen(datum)

    # Vergleich mit dem Vortag in den Daten
    idx = tage.index(datum)
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
            f"Potenzieller Verlust: {euro(len(fehler) * wellpass_wert_am(datum))}", "warn")

        for _, r in fehler.iterrows():
            kennung = f"dt_{r['Name_norm']}_{r['Datum']}"
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
                _erledigt_knopf(str(r["Name_norm"]), str(r["Datum"]),
                                key=f"dt_ok_{r['Name_norm']}_{r['Datum']}")

    # ── Erledigte Fälle dieses Tages ────────────────────────────────────
    erledigt_alle = erledigte_faelle()
    if not erledigt_alle.empty:
        erledigt_tag = erledigt_alle[erledigt_alle["datum"].astype(str) == str(datum)]
        if not erledigt_tag.empty:
            st.markdown("")
            with st.expander(f"✅ {len(erledigt_tag)} Fälle als erledigt "
                             "markiert — versehentlich? Hier zurücknehmen"):
                for i, (_, e) in enumerate(erledigt_tag.iterrows()):
                    u1, u2 = st.columns([3, 1.2])
                    with u1:
                        info = grund_info(e.get("grund", ""))
                        label = f"{info['icon']} {info['kurz']}"
                        st.markdown(f"**{e['Name']}**  {chip(label, 'soft')}",
                                    unsafe_allow_html=True)
                        wann = (e["_ts"].strftime("%d.%m. %H:%M")
                                if pd.notna(e.get("_ts")) else "")
                        notiz = str(e.get("notiz", "") or "").strip()
                        zeile = " · ".join(x for x in
                                           [f"erledigt am {wann}" if wann else "",
                                            notiz] if x)
                        if zeile:
                            st.caption(zeile)
                    with u2:
                        if st.button("Wieder öffnen", key=f"dt_undo_{i}_{datum}",
                                     use_container_width=True):
                            behebung_zuruecknehmen(str(e["name_norm"]),
                                                   str(e["datum"]))
                            st.toast("Fall ist wieder offen.")
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

    # ── Handlungsvorschläge ──────────────────────────────────────────────
    #
    # Unabhängig vom Monatsfilter oben — Trend und "seit Beginn der
    # Daten" beziehen sich immer auf den ganzen erfassten Zeitraum,
    # sonst verschwindet der Rückgang, sobald man einen einzelnen
    # Monat auswählt.
    st.markdown("")
    st.markdown("---")
    st.markdown("##### 📋 Handlungsvorschläge")

    vorschlaege = auslastung_vorschlaege()
    if not vorschlaege:
        box("Noch zu wenig Daten für verlässliche Vorschläge — braucht "
            "mindestens ein paar Wochen Verlauf.", "info")
    else:
        art_info = {
            "rueckgang": ("⚠️", "warn", "Rückläufig"),
            "leer":      ("👀", "info", "Tote Prime-Time"),
            "stark":     ("💡", "ok",   "Preis-Kandidat"),
        }
        anzahl_je_art = {}
        for v in vorschlaege:
            anzahl_je_art[v["art"]] = anzahl_je_art.get(v["art"], 0) + 1

        zusammenfassung = " · ".join(
            f"{art_info[art][0]} {n} {art_info[art][2]}"
            for art, n in anzahl_je_art.items() if art in art_info)
        st.caption(zusammenfassung)

        for v in vorschlaege[:15]:
            icon, farbe, _label = art_info.get(v["art"], ("•", "info", ""))
            box(f"{icon} {v['text']}", farbe)
        if len(vorschlaege) > 15:
            st.caption(f"… und {len(vorschlaege) - 15} weitere.")


@st.cache_data(ttl=900, show_spinner=False)
def anspruch_bilanz(monat: str) -> pd.DataFrame:
    """
    Die Gegenprobe: rabattierte Plätze gegen vergütete Check-ins,
    Spieler für Spieler.

    Unabhängig davon, welcher Check-in welchem Fall zugeordnet wurde.
    Pro Person und Tag zählt genau ein Check-in — wer an einem Tag
    zweimal mit Rabatt gespielt hat, hat einen ungedeckten Platz,
    auch wenn er eingecheckt war.
    """
    b = loadsheet("buchungen")
    c = loadsheet("checkins")
    if b.empty or "analysis_date" not in b.columns:
        return pd.DataFrame()

    mb = b[b["analysis_date"].astype(str).str.startswith(str(monat))].copy()
    if mb.empty or "Relevant" not in mb.columns:
        return pd.DataFrame()

    # Rabattierte Plätze je Spieler — Teamzeilen zählen nicht
    mb = mb[(mb["Relevant"].astype(str) == "Ja") &
            (mb["Team"].astype(str) != "Ja"
             if "Team" in mb.columns else True)]
    if mb.empty:
        return pd.DataFrame()

    rabatte = (mb.groupby(["Name_norm", "Name"]).size()
               .reset_index(name="rabattierte_plaetze"))

    # Vergütete Check-ins: einer pro Person und Tag
    if not c.empty and {"Name_norm", "analysis_date"} <= set(c.columns):
        mc = c[c["analysis_date"].astype(str).str.startswith(str(monat))]
        verguetet = (mc.drop_duplicates(subset=["Name_norm", "analysis_date"])
                     .groupby("Name_norm").size()
                     .reset_index(name="verguetete_checkins"))
    else:
        verguetet = pd.DataFrame(columns=["Name_norm", "verguetete_checkins"])

    # Namensvarianten zusammenführen
    mapping = mapping_laden()
    if mapping and not verguetet.empty:
        rueck = {}
        for buchung_name, ziel in mapping.items():
            gname = ziel["checkin_name"] if isinstance(ziel, dict) else ziel
            rueck[str(gname)] = str(buchung_name)
        verguetet["Name_norm"] = verguetet["Name_norm"].map(
            lambda n: rueck.get(str(n), str(n)))
        verguetet = (verguetet.groupby("Name_norm", as_index=False)
                     ["verguetete_checkins"].sum())

    stat = rabatte.merge(verguetet, on="Name_norm", how="left")
    stat["verguetete_checkins"] = (stat["verguetete_checkins"]
                                   .fillna(0).astype(int))

    # ── Namensvarianten, die noch nicht bestätigt sind ──────────────────
    #
    # Bis hierher zählt nur der exakt gleiche Name oder eine bestätigte
    # Verknüpfung. Playtomic und EGYM schreiben denselben Menschen aber
    # oft verschieden — „Katja Hero" gegen „Katja Herold". Die Person
    # stand dadurch mit null Check-ins und voller Lücke in der Liste,
    # obwohl sie jedes Mal eingecheckt hat.
    #
    # Solche Treffer werden getrennt ausgewiesen statt einfach
    # mitgezählt. Sie sind ein starker Hinweis, aber kein Beleg — und
    # eine vermutete Deckung darf einen echten Verlust nicht verstecken.
    offen_namen = set(stat.loc[stat["verguetete_checkins"]
                               < stat["rabattierte_plaetze"], "Name_norm"]
                      .astype(str))
    vermutet = {}
    if offen_namen and not c.empty and {"Name_norm", "analysis_date"} <= set(c.columns):
        mc = c[c["analysis_date"].astype(str).str.startswith(str(monat))]
        frei = (mc.drop_duplicates(subset=["Name_norm", "analysis_date"])
                .groupby("Name_norm").size().to_dict())
        schon_vergeben = set(stat["Name_norm"].astype(str))
        abgelehnt = rejected_matches_laden()
        for ziel in offen_namen:
            such_vor, such_nach = _namensteile(ziel)
            for kand, anzahl in frei.items():
                kand = str(kand)
                if kand in schon_vergeben:
                    continue          # gehört nachweislich jemand anderem
                if (kand, ziel) in abgelehnt or (ziel, kand) in abgelehnt:
                    continue
                kand_vor, kand_nach = _namensteile(kand)
                passt = (such_nach and kand_nach
                         and _teil_aehnlich(such_nach, kand_nach) >= 85
                         and _teil_aehnlich(such_vor, kand_vor) >= 55)
                if passt or _teilmengen_name(ziel, kand):
                    vermutet[ziel] = vermutet.get(ziel, 0) + int(anzahl)

    stat["vermutete_checkins"] = (stat["Name_norm"].astype(str)
                                  .map(lambda n: vermutet.get(n, 0)).astype(int))
    # Eine Vermutung kann die eigenen Rabatte nicht übersteigen
    stat["vermutete_checkins"] = stat[
        ["vermutete_checkins", "rabattierte_plaetze"]].min(axis=1)

    stat["luecke"] = (stat["rabattierte_plaetze"]
                      - stat["verguetete_checkins"]).clip(lower=0)
    stat["luecke_sicher"] = (stat["luecke"]
                             - stat["vermutete_checkins"]).clip(lower=0)
    satz = wellpass_wert_am(f"{monat}-01")
    stat["verlust"] = (stat["luecke_sicher"] * satz).round(2)

    return stat.sort_values(["luecke_sicher", "luecke", "rabattierte_plaetze"],
                            ascending=[False, False, False])


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
        kpi("Offen (roh)", euro(fehlend * wellpass_wert_am(f"{monat}-01")),
            "vor Klärung — Bilanz unten")

    st.markdown("")
    if fehlend == 0:
        box("✅ <b>Sauber.</b> Für jeden gegebenen Rabatt liegt ein vergüteter "
            "Check-in vor.", "ok")
    else:
        box(f"⚠️ <b>{fehlend} Rabatte ohne Vergütung</b> — das sind "
            f"{euro(fehlend * wellpass_wert_am(f'{monat}-01'))}, die dir für diesen Monat fehlen.",
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

    # ── Abgearbeitet ────────────────────────────────────────────────────
    #
    # Bewusst nur eine Zählung, kein Geldwert: Was hier zusammenkommt,
    # ist Bearbeitungsstand, keine Einnahme. Die Umsatzzahlen stammen
    # ausschliesslich aus den Playtomic-Zahlungen und den EGYM-Check-ins.
    st.markdown("---")
    erledigt = erledigte_faelle()
    if not erledigt.empty:
        erledigt = erledigt[erledigt["datum"].astype(str).str.startswith(monat)]
    anzahl_erledigt = len(erledigt)
    st.markdown(f"**Abgearbeitet:** {anzahl_erledigt} "
                + ("Fall" if anzahl_erledigt == 1 else "Fälle")
                + " in diesem Monat geschlossen")
    st.caption("Nur der Bearbeitungsstand — die Zahlen oben stammen "
               "ausschliesslich aus Playtomic und EGYM.")

    # ── Gegenprobe je Spieler ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Gegenprobe: Spieler für Spieler**")
    box("Rabattierte Plätze gegen vergütete Check-ins — unabhängig davon, "
        "welcher Check-in welchem Fall zugeordnet wurde. Pro Person und Tag "
        "zählt genau ein Check-in. Wer an einem Tag zweimal mit Rabatt "
        "gespielt hat, hat einen ungedeckten Platz, auch wenn er "
        "eingecheckt war.", "info")

    ab = anspruch_bilanz(monat)
    if ab.empty:
        box("Für diesen Monat liegen keine rabattierten Buchungen vor.", "info")
    else:
        luecken = ab[ab["luecke_sicher"] > 0]
        vermutet_gesamt = int(ab["vermutete_checkins"].sum())
        g1, g2, g3 = st.columns(3)
        with g1:
            kpi("Rabattierte Plätze", str(int(ab["rabattierte_plaetze"].sum())))
        with g2:
            kpi("Vergütete Check-ins", str(int(ab["verguetete_checkins"].sum())),
                f"+{vermutet_gesamt} über Namensvariante" if vermutet_gesamt else None)
        with g3:
            kpi("Ungedeckt", str(int(ab["luecke_sicher"].sum())),
                euro(float(ab["verlust"].sum())))

        if vermutet_gesamt:
            betroffen = int((ab["vermutete_checkins"] > 0).sum())
            box(f"🔤 <b>{vermutet_gesamt} Check-ins</b> bei <b>{betroffen} Spielern</b> "
                "hängen nur an einer Namensvariante — Playtomic und EGYM "
                "schreiben denselben Menschen verschieden — ein fehlender "
                "Buchstabe im Nachnamen genügt. Sie sind hier bereits abgezogen, gelten "
                "aber erst als belegt, wenn du sie im <b>Name-Abgleich</b> "
                "bestätigst.", "info")

        st.markdown("")
        if luecken.empty:
            box("✅ Jeder rabattierte Platz ist durch einen Check-in gedeckt.",
                "ok")
        else:
            zeig = luecken[["Name", "rabattierte_plaetze",
                            "verguetete_checkins", "vermutete_checkins",
                            "luecke_sicher", "verlust"]].copy()
            zeig["verlust"] = zeig["verlust"].map(euro)
            zeig.columns = ["Spieler", "Rabatte", "Check-ins",
                            "davon Namensvariante", "Lücke", "Entgangen"]
            st.dataframe(zeig, use_container_width=True, hide_index=True,
                         height=300)
            st.download_button(
                "⬇️ Als CSV",
                data=zeig.to_csv(index=False, sep=";").encode("utf-8-sig"),
                file_name=f"anspruchsluecken_{monat}.csv", mime="text/csv",
                use_container_width=True)

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


def monat_lang(monat: str) -> str:
    """'2026-07' → 'Juli 2026'"""
    try:
        return f"{MONATE_DE[int(monat[5:7]) - 1]} {monat[:4]}"
    except (ValueError, IndexError):
        return str(monat)


@st.cache_data(ttl=900, show_spinner=False)
def abzug_pruefen() -> dict:
    """
    Welcher Abzugsbetrag passt zu den vorhandenen Buchungen?

    Der Wert kann sich ändern — bei uns ist er schon von 13,00 € auf
    12,00 € gewandert. Stimmt die Einstellung nicht, verschwinden
    Buchungen mit mehreren Wellpass-Spielern lautlos aus der Kontrolle:
    Bei einem Rabatt geht die Rechnung zufällig noch auf, bei zwei bis
    vier nicht mehr.

    → {"eingestellt": …, "bester": …, "quoten": {betrag: quote}, …}
    """
    b = loadsheet("buchungen")
    leer = {"eingestellt": wellpass_abzug(), "bester": None,
            "quoten": {}, "geprueft": 0}
    if b.empty or "Listenpreis" not in b.columns:
        return leer

    # Eine Zeile je Buchung genügt
    schluessel = ["analysis_date", "Service_Zeit", "Court"]
    if not all(k in b.columns for k in schluessel):
        return leer
    buchungen = b.drop_duplicates(subset=schluessel)

    kandidaten = sorted({wellpass_abzug(), 12.0, 13.0, 13.5, 11.0})
    treffer = {k: 0 for k in kandidaten}
    geprueft = 0

    for _, r in buchungen.iterrows():
        # Events haben einen eigenen, frei gesetzten Rabatt (10 € statt
        # 12 €). Sie gehören nicht in die Statistik, die den normalen
        # Playtomic-Abzug bestimmt — sonst zieht ein einzelner Mexicano
        # den erkannten Standardabzug in die Irre.
        if str(r.get("Event", "")) == "Ja":
            continue
        liste = parse_betrag(r.get("Listenpreis"))
        bezahlt = parse_betrag(r.get("Bezahlt"))
        plaetze = court_plaetze(str(r.get("Court", "")))
        rabatt = round(liste - bezahlt, 2)
        if liste <= 0 or rabatt < 0.5:
            continue
        geprueft += 1
        for k in kandidaten:
            if wellpass_anzahl(liste, bezahlt, plaetze, abzug_wert=k) > 0:
                treffer[k] += 1

    if not geprueft:
        return leer

    quoten = {k: v / geprueft for k, v in treffer.items()}
    bester = max(quoten, key=lambda k: quoten[k])
    return {"eingestellt": wellpass_abzug(), "bester": bester,
            "quoten": quoten, "geprueft": geprueft}


@st.cache_data(ttl=900, show_spinner=False)
def checkins_roh_und_verguetet(monat: str):
    """
    Gescannte Check-ins gegen vergütete Check-ins.

    Wellpass vergütet pro Person und Tag genau einmal. Die Differenz
    sind Plätze, für die niemand zahlt.

    → (roh, vergütet, nicht vergütet)
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return 0, 0, 0
    m = c[c["analysis_date"].astype(str).str.startswith(str(monat))]
    if m.empty:
        return 0, 0, 0
    roh = len(m)
    verguetet = len(m.drop_duplicates(subset=["Name_norm", "analysis_date"]))
    return roh, verguetet, roh - verguetet


def _dash_einnahmen():
    """
    Nur harte Fakten: was Playtomic abgerechnet hat und was EGYM zahlt.

    Bewusst ohne Bearbeitungsgebühren, Überweisungen, Kulanz und
    sonstige Korrekturen — die stehen im Monatsabgleich. Hier geht es
    um die zwei Quellen, die wirklich Geld überweisen.
    """
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten. Lade zuerst die Playtomic-Exporte hoch.", "warn")
        return

    monate = sorted({t[:7] for t in tage}, reverse=True)
    monat = st.selectbox("Monat", monate, format_func=monat_lang,
                         key="ein_monat")

    k = monats_kennzahlen(monat)
    playtomic = float(k["umsatz"])
    wellpass = float(k["wellpass_wert"])
    gesamt = playtomic + wellpass

    box("Nur die beiden Quellen, die dir tatsächlich Geld überweisen. "
        "Gerechnet wird ausschliesslich mit den hochgeladenen Exporten — "
        "wie du einen Fall später abschliesst, ändert hier nichts.", "info")

    e1, e2, e3 = st.columns(3)
    with e1:
        kpi("Playtomic", euro(playtomic), f"{k['buchungen']} Buchungen")
    with e2:
        kpi("Wellpass", euro(wellpass),
            f"{k['wellpass_anzahl']} vergütete Check-ins")
    with e3:
        kpi("Gesamt", euro(gesamt), monat_lang(monat))

    # ── Wie sich die Wellpass-Zahl ergibt ───────────────────────────────
    roh, verguetet, doppelte = checkins_roh_und_verguetet(monat)
    if roh:
        w1, w2, w3 = st.columns(3)
        with w1:
            kpi("Check-ins gescannt", str(roh), "roh aus dem EGYM-Export")
        with w2:
            kpi("Davon vergütet", str(verguetet), "einer je Person und Tag")
        with w3:
            kpi("Nicht vergütet", str(doppelte), "zweiter Scan am selben Tag")
        if doppelte:
            box(f"ℹ️ <b>{doppelte} Check-ins bringen kein Geld.</b> "
                "Wellpass vergütet pro Person und Tag genau einmal. Wer "
                "zweimal am Tag eincheckt, wird nur einmal gezählt — der "
                "zweite Platz ist unbezahlt geblieben.", "info")

    if gesamt > 0:
        anteil = wellpass / gesamt * 100
        st.markdown("")
        st.caption(f"Wellpass macht {anteil:.0f} % der Einnahmen aus")
        st.progress(min(1.0, anteil / 100))

    # ── Aufschlüsselung Playtomic ───────────────────────────────────────
    st.markdown("---")
    st.markdown("**Woraus sich Playtomic zusammensetzt**")
    posten = [
        ("Online bezahlt", k["online"]),
        ("Über Guthaben", k["guthaben"]),
        ("Bälle", k["baelle"]),
        ("Schlägerverleih", k["schlaeger"]),
        ("Sonstiges", k["sonstige"]),
    ]
    tabelle = pd.DataFrame(
        [{"Posten": name, "Betrag": euro(wert)}
         for name, wert in posten if abs(wert) > 0.005])
    if tabelle.empty:
        box("Keine Umsätze in diesem Monat.", "info")
    else:
        st.dataframe(tabelle, use_container_width=True, hide_index=True)

    # ── Tag für Tag ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Tag für Tag**")

    monats_tage = sorted([t for t in tage if t.startswith(monat)])
    zeilen = []
    for t in monats_tage:
        tk = tages_kennzahlen(t)
        zeilen.append({
            "Datum": datum_kurz(t),
            "Playtomic": round(float(tk["umsatz"]), 2),
            "Wellpass": round(float(tk["wellpass_wert"]), 2),
            "Check-ins": int(tk["wellpass_anzahl"]),
            "Gesamt": round(float(tk["umsatz"]) + float(tk["wellpass_wert"]), 2),
        })

    if not zeilen:
        return

    df = pd.DataFrame(zeilen)

    zeig = df.copy()
    for spalte in ("Playtomic", "Wellpass", "Gesamt"):
        zeig[spalte] = zeig[spalte].map(euro)
    st.dataframe(zeig, use_container_width=True, hide_index=True, height=340)

    summe = pd.DataFrame([{
        "Datum": "Summe",
        "Playtomic": euro(df["Playtomic"].sum()),
        "Wellpass": euro(df["Wellpass"].sum()),
        "Check-ins": int(df["Check-ins"].sum()),
        "Gesamt": euro(df["Gesamt"].sum()),
    }])
    st.dataframe(summe, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Als CSV",
        data=df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"einnahmen_{monat}.csv", mime="text/csv",
        use_container_width=True)


def modul_dashboard():
    head("Business Dashboard", "Umsatz · Auslastung · Abgleich")
    t1, t2, t3, t4, t5 = st.tabs(["📅 Tag", "💰 Einnahmen", "📈 Monat",
                                  "🔥 Auslastung", "⚖️ Monatsabgleich"])
    with t1:
        _dash_tag()
    with t2:
        _dash_einnahmen()
    with t3:
        _dash_monat()
    with t4:
        _dash_auslastung()
    with t5:
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
                                st.toast("✅ Gesendet.")
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
                            st.toast("✅ Gesendet.")
                            st.rerun()


def modul_spieler():
    head("Spieler & Community", "Rangliste · Vielspieler · Rückholung")
    t1, t2, t3, t4 = st.tabs(["🏆 Rangliste", "⭐ Vielspieler", "🔄 Rückholung",
                              "🔎 Analysen"])
    with t1:
        _spieler_rangliste()
    with t2:
        _vielspieler()
    with t3:
        _winback()
    with t4:
        _spieler_analysen()


def _spieler_analysen():
    """Segmente, Abwanderungsrisiko, Wellpass-Mix — für Schlüsse, nicht nur Zahlen."""
    segmente = spieler_segmente()
    if segmente.empty:
        box("Noch keine Spielerdaten.", "info")
        return

    # ── Segment-Übersicht ────────────────────────────────────────────────
    st.markdown("##### Segmente")
    st.caption("Grobe Einteilung nach Buchungsanzahl und letztem Besuch — "
               "für den schnellen Überblick, nicht für die Wissenschaft.")

    reihenfolge = ["Stammspieler", "Rückläufig", "Gelegenheit", "Neu", "Verloren"]
    zaehler = segmente["Segment"].value_counts().to_dict()
    spalten = st.columns(len(reihenfolge))
    for col, seg in zip(spalten, reihenfolge):
        with col:
            kpi(seg, str(zaehler.get(seg, 0)))

    st.markdown("")
    st.markdown("---")

    # ── Abwanderungsrisiko ───────────────────────────────────────────────
    st.markdown("##### Abwanderungsrisiko")
    box("Vergleicht die aktuelle Pause jedes Spielers mit seinem eigenen "
        "üblichen Abstand zwischen zwei Besuchen — nicht mit einem festen "
        "Tage-Wert für alle. Ein Vielspieler, der sonst alle 3 Tage kommt "
        "und jetzt 10 Tage weg ist, wird hier sichtbar, lange bevor er in "
        "die normale Rückholung fallen würde.", "info")

    rhythmus = spieler_rhythmus()
    if rhythmus.empty:
        box("Noch zu wenig wiederholte Besuche für eine Rhythmus-Analyse "
            "(mindestens 3 Besuche pro Spieler nötig).", "info")
    else:
        schwelle = st.slider(
            "Risiko-Schwelle (aktuelle Pause ÷ üblicher Abstand)",
            1.0, 5.0, 1.5, step=0.1,
            help="1.5 heisst: schon 50% länger weg als sonst üblich.")
        risiko = rhythmus[rhythmus["Risiko"] >= schwelle]

        if risiko.empty:
            box("✅ Niemand über der Schwelle — alle Vielspieler in ihrem "
                "gewohnten Rhythmus.", "ok")
        else:
            st.caption(f"{len(risiko)} von {len(rhythmus)} Spielern mit "
                       "wiederkehrendem Besuch über der Schwelle.")
            for _, r in risiko.head(30).iterrows():
                einstufung = ("err" if r["Risiko"] >= 2.5
                             else "warn" if r["Risiko"] >= 1.8 else "soft")
                risiko_chip = chip(f"{r['Risiko']:.1f}×", einstufung)
                st.markdown(
                    f"<div class='pc-row'><div><span class='nm'>{r['Name']}</span>"
                    f"<span class='mt'>&nbsp;· sonst alle {r['Ø Abstand']:.0f} Tage, "
                    f"jetzt {int(r['Aktuelle Pause'])} Tage weg</span></div>"
                    f"<div>{risiko_chip}</div></div>",
                    unsafe_allow_html=True)

    st.markdown("")
    st.markdown("---")

    # ── Wellpass-Mix ─────────────────────────────────────────────────────
    st.markdown("##### Wellpass-Mix")
    st.caption("Wie viel Prozent der Buchungen jedes Spielers mit "
               "Wellpass-Rabatt liefen. Nahe 100% heisst: fast reiner "
               "Wellpass-Kunde. Nahe 0%: zahlt praktisch immer voll.")

    relevante = segmente[segmente["buchungen"] >= 3].copy()
    if relevante.empty:
        box("Noch zu wenig Buchungen pro Spieler für den Wellpass-Mix.", "info")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Fast reine Wellpass-Nutzer**")
            for _, r in (relevante.sort_values("Wellpass-Anteil", ascending=False)
                        .head(8).iterrows()):
                st.markdown(f"<div class='pc-row'><span class='nm'>{r['Name']}</span>"
                            f"<span class='mt'>{r['Wellpass-Anteil']:.0f}% "
                            f"({int(r['buchungen'])} Buchungen)</span></div>",
                            unsafe_allow_html=True)
        with c2:
            st.markdown("**Zahlen praktisch immer voll**")
            for _, r in (relevante.sort_values("Wellpass-Anteil", ascending=True)
                        .head(8).iterrows()):
                st.markdown(f"<div class='pc-row'><span class='nm'>{r['Name']}</span>"
                            f"<span class='mt'>{r['Wellpass-Anteil']:.0f}% "
                            f"({int(r['buchungen'])} Buchungen)</span></div>",
                            unsafe_allow_html=True)


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


@st.cache_data(ttl=900, show_spinner=False)
def kontakt_index() -> dict:
    """
    Telefon und E-Mail aller Kunden — EINMAL aufgebaut, danach nur noch
    nachgeschlagen.

    Vorher wurde für jeden einzelnen Aufruf die komplette customers-Tabelle
    geladen und alle Namen neu normalisiert. Bei acht Fällen und 160
    überzähligen Check-ins waren das hunderte Durchläufe pro Seitenaufruf.

    → {name_norm: {"phone": …, "email": …}}
    """
    kunden = loadsheet("customers")
    idx = {}
    if kunden.empty or "name" not in kunden.columns:
        return idx

    hat_tel = "phone_number" in kunden.columns
    hat_mail = "email" in kunden.columns

    anzahl = len(kunden)
    namen = kunden["name"].tolist()
    tele = kunden["phone_number"].tolist() if hat_tel else [""] * anzahl
    mails = kunden["email"].tolist() if hat_mail else [""] * anzahl

    for roh_name, roh_tel, roh_mail in zip(namen, tele, mails):
        norm = normalize_name(roh_name)
        if not norm:
            continue
        eintrag = idx.setdefault(norm, {"phone": "", "email": ""})

        if not eintrag["phone"]:
            tel = telefon_normalisieren(roh_tel)
            if tel:
                eintrag["phone"] = tel
        if not eintrag["email"]:
            mail = str(roh_mail or "").strip()
            if "@" in mail:
                eintrag["email"] = mail

    return idx


def telefon_fuer(name: str) -> str:
    return kontakt_index().get(normalize_name(name), {}).get("phone", "")


def email_fuer(name: str) -> str:
    return kontakt_index().get(normalize_name(name), {}).get("email", "")


# ── Nachrichtenvorlagen ───────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def checkins_von_am(name_norm: str, datum: str) -> int:
    """
    Wie oft hat diese Person an diesem Tag eingecheckt?

    Zählt auch Check-ins unter einer bestätigten Namensvariante.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns or "Name_norm" not in c.columns:
        return 0

    gesucht = {str(name_norm)}
    ziel = mapping_laden().get(str(name_norm))
    if ziel:
        gesucht.add(str(ziel["checkin_name"] if isinstance(ziel, dict) else ziel))

    tag = c[c["analysis_date"].astype(str) == str(datum)]
    if tag.empty:
        return 0

    treffer = tag[tag["Name_norm"].astype(str).isin(gesucht)]
    if treffer.empty:
        return 0

    # Check-ins, die als Nachholung einem anderen Tag zugeordnet wurden,
    # gehören nicht mehr hierher.
    verbraucht = verbrauchte_checkins()
    if verbraucht:
        offen = [nn for nn in treffer["Name_norm"].astype(str)
                 if checkin_schluessel(str(datum), nn) not in verbraucht]
        return len(offen)
    return len(treffer)


@st.cache_data(ttl=600, show_spinner=False)
def rabattierte_buchungen_am(name_norm: str, datum: str) -> int:
    """Wie viele rabattierte Buchungen hat diese Person an dem Tag?"""
    b = loadsheet("buchungen")
    if b.empty or "analysis_date" not in b.columns:
        return 0
    tag = b[(b["analysis_date"].astype(str) == str(datum)) &
            (b["Name_norm"].astype(str) == str(name_norm))]
    if tag.empty or "Relevant" not in tag.columns:
        return 0
    schluessel = [k for k in ("Service_Zeit", "Court") if k in tag.columns]
    if schluessel:
        tag = tag.drop_duplicates(subset=schluessel)
    return int((tag["Relevant"].astype(str) == "Ja").sum())


def ist_zweitbuchung(name_norm: str, datum: str) -> bool:
    """
    Zweite rabattierte Buchung am selben Tag, obwohl eingecheckt wurde?

    EGYM vergütet pro Person und Tag nur einmal. Wer zweimal am Tag mit
    Wellpass-Rabatt spielt, hat beim zweiten Mal einen Platz bekommen,
    für den niemand zahlt. Das ist kein vergessener Check-in — der
    Spieler muss den zweiten Platz nachträglich bezahlen.

    Beide Bedingungen müssen erfüllt sein: ein eigener Check-in UND
    mindestens zwei rabattierte Buchungen an dem Tag. Sonst wird schon
    die erste und einzige Buchung als Zweitbuchung ausgewiesen — was
    genau falsch herum ist, denn dann fehlt der Check-in schlicht.
    """
    return (rabattierte_buchungen_am(name_norm, datum) >= 2
            and checkins_von_am(name_norm, datum) > 0)


def zweitbuchung_nachricht(name: str, datum: str, zeit: str = "",
                           betrag: float = None) -> str:
    """Nachricht für die zweite Buchung am selben Tag."""
    vorname = name.split()[0] if " " in name else name
    wann = f"am {datum}" + (f" um {zeit} Uhr" if zeit else "")
    summe = euro(betrag) if betrag else "den Platzanteil"
    return f"""🔵 Hey {vorname}!

Du warst {wann} zum zweiten Mal an dem Tag bei uns — stark. 👀

Eine Sache dazu: Wellpass vergütet pro Person und Tag nur einen
Check-in. Dein zweiter Check-in zählt also nicht, und der Platz ist
bei uns offen geblieben.

Kannst du {summe} nachzahlen? PayPal: {CONFIG['email']}

Beim nächsten Mal am besten gleich mitbuchen, dann ist es
unkomplizierter.

⚡ Once in. Never out.
Dein {CONFIG['name']} Team"""


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
    sheet_zeile_setzen("whatsapp_log", {
        "key": wa_key(name_norm, datum, betrag), "name": name, "datum": datum,
        "betrag": betrag, "to_number": nummer, "art": art,
        "timestamp": datetime.now().isoformat()})
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

AUTO_SCHWELLE_STANDARD = 95.0
AUTO_ABSTAND = 8.0     # Vorsprung zum zweitbesten Kandidaten


@st.cache_data(ttl=600, show_spinner=False)
def buchungsnamen_am_tag(datum: str) -> dict:
    """Alle Spielernamen mit Buchung an diesem Tag. → {norm: anzeige}"""
    b = loadsheet("buchungen")
    if b.empty or "analysis_date" not in b.columns:
        return {}
    tag = b[b["analysis_date"].astype(str) == str(datum)]
    if tag.empty:
        return {}
    return dict(zip(tag["Name_norm"].astype(str), tag["Name"].astype(str)))


def auto_kandidaten_von_checkins(tage: list, schwelle: float) -> list:
    """
    Dieselbe Frage von der anderen Seite: Zu welchem Buchungsnamen
    gehört ein überzähliger Check-in?

    Nötig, weil die Suche über die offenen Fälle einen ganzen Fall
    verpasst: Steht jemand aus irgendeinem Grund nicht als offener Fall
    da — etwa weil er nicht als Rabattträger erkannt wurde oder der Fall
    schon von Hand geschlossen wurde — wird sein Check-in nie geprüft
    und bleibt für immer als überzählig stehen. Genau so blieb
    ein Check-in liegen, obwohl die Person unter leicht anderer
    Schreibweise an dem Tag gespielt hat.
    """
    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()
    gefunden = []

    for tag in tage:
        ueber = offene_checkins(tag)
        if ueber.empty:
            continue

        namen = buchungsnamen_am_tag(tag)
        if not namen:
            continue

        # Wer an dem Tag unter eigenem Namen eingecheckt hat, ist
        # jemand anderes — der kommt als Ziel nicht in Frage.
        eigene_checkins = set(ueber["Name_norm"].astype(str))
        kandidaten = [n for n in namen
                      if n not in eigene_checkins and n not in mapping]
        if not kandidaten:
            continue

        for _, r in ueber.iterrows():
            ci_norm = str(r["Name_norm"])
            ci_name = str(r["Name"])

            treffer = fuzzy_match(ci_norm, kandidaten, mapping, abgelehnt)
            if not treffer:
                continue
            bester, score, _quelle = treffer[0]
            if score < schwelle:
                continue
            if len(treffer) > 1 and score - treffer[1][1] < AUTO_ABSTAND:
                continue

            gefunden.append({
                "datum": tag, "name": namen[bester], "name_norm": bester,
                "checkin": ci_name, "checkin_norm": ci_norm,
                "score": score, "grund": "Name + Buchung am selben Tag",
            })
    return gefunden


def auto_kandidaten(tage: list = None, schwelle: float = None) -> list:
    """
    Fälle, bei denen die Zuordnung eindeutig genug ist, um sie ohne
    Rückfrage zu übernehmen.

    Zwei Bedingungen, nicht nur eine:
      1. Der beste Vorschlag liegt über der Schwelle
      2. Er hat deutlichen Vorsprung zum zweitbesten — sonst könnten
         zwei ähnliche Namen um denselben Check-in konkurrieren und
         die Entscheidung wäre Zufall

    Bewusst nur Zuordnungen am Spieltag selbst. Das ist eine reine
    Schreibweisen-Korrektur: der Check-in ist da und von EGYM bezahlt,
    es ändert sich kein Geld. Nachholungen an Folgetagen bleiben bei
    dir — da wird tatsächlich ein Anspruch geschlossen.

    → [{datum, name, name_norm, checkin, checkin_norm, score, grund}, …]
    """
    if schwelle is None:
        schwelle = float(einstellung("auto_schwelle", AUTO_SCHWELLE_STANDARD))
    if tage is None:
        tage = verfuegbare_tage()

    gefunden = []
    for tag in tage:
        offen = offene_fehler(tag)
        if offen.empty:
            continue

        vergeben = set()
        for _, r in offen.iterrows():
            name = str(r["Name"])
            nn = str(r["Name_norm"])
            vorschlaege = zuordnung_vorschlag(
                name, tag, mail=email_fuer(name),
                zeit=str(r.get("Service_Zeit", "")))
            if not vorschlaege:
                continue

            bester, bester_norm, score, _zeit, grund = vorschlaege[0]
            if score < schwelle:
                continue
            # Zweitbester zu dicht dran → lieber nachfragen
            if len(vorschlaege) > 1 and score - vorschlaege[1][2] < AUTO_ABSTAND:
                continue
            # Denselben Check-in nicht zweimal vergeben
            if bester_norm in vergeben:
                continue

            vergeben.add(bester_norm)
            gefunden.append({
                "datum": tag, "name": name, "name_norm": nn,
                "checkin": bester, "checkin_norm": bester_norm,
                "score": score, "grund": grund,
            })

    # Zweite Blickrichtung: von den überzähligen Check-ins aus.
    # Beide Wege finden teils dieselben Paare — Dubletten fliegen raus.
    schon = {(k["datum"], k["name_norm"]) for k in gefunden}
    for k in auto_kandidaten_von_checkins(tage, schwelle):
        if (k["datum"], k["name_norm"]) not in schon:
            schon.add((k["datum"], k["name_norm"]))
            gefunden.append(k)

    return gefunden


def auto_zuordnungen_uebernehmen(tage: list = None,
                                 schwelle: float = None) -> list:
    """Die eindeutigen Zuordnungen tatsächlich speichern."""
    kandidaten = auto_kandidaten(tage, schwelle)
    if not kandidaten:
        return []
    mapping_mehrere_hinzufuegen([
        (k["name_norm"], k["checkin_norm"], k["score"]) for k in kandidaten])
    cache_leeren()
    return kandidaten


def _wa_auto_block(tage: list):
    """
    Eindeutige Zuordnungen selbst erledigen — ohne Rückfrage.

    Gegen Endlosschleifen: jeder bereits behandelte Fall wird für diese
    Sitzung vermerkt. Selbst wenn eine Zuordnung wider Erwarten nicht
    greift, wird sie kein zweites Mal geschrieben.
    """
    if not einstellung("auto_zuordnung_an", True):
        return

    schon = st.session_state.setdefault("_auto_erledigt", set())
    protokoll = st.session_state.setdefault("_auto_protokoll", [])

    neue = [k for k in auto_kandidaten(tage)
            if f"{k['datum']}|{k['name_norm']}" not in schon]

    if neue:
        mapping_mehrere_hinzufuegen([
            (k["name_norm"], k["checkin_norm"], k["score"]) for k in neue])
        for k in neue:
            schon.add(f"{k['datum']}|{k['name_norm']}")
        protokoll.extend(neue)
        cache_leeren()
        st.rerun()

    if not protokoll:
        return

    schwelle = float(einstellung("auto_schwelle", AUTO_SCHWELLE_STANDARD))
    box(f"⚡ <b>{len(protokoll)} eindeutige Zuordnungen automatisch "
        f"übernommen</b> (ab {schwelle:.0f} % und mit klarem Vorsprung zum "
        "zweitbesten). Reine Schreibweisen-Unterschiede — der Check-in lag "
        "vor und war von EGYM bezahlt.", "ok")

    with st.expander("Ansehen, was übernommen wurde"):
        st.dataframe(pd.DataFrame([{
            "Spieltag": datum_kurz(k["datum"]),
            "Playtomic": k["name"],
            "Wellpass": k["checkin"],
            "Sicherheit": f"{k['score']:.0f} %",
            "Belege": k["grund"],
        } for k in protokoll]), use_container_width=True, hide_index=True,
            height=min(320, 60 + 35 * len(protokoll)))
        st.caption("Zurücknehmen unter Name-Abgleich → Gelernte Zuordnungen. "
                   "Stellt sich später heraus, dass es zwei Personen sind, "
                   "meldet sich der Konflikte-Tab von selbst.")
    st.markdown("---")


@st.cache_data(ttl=600, show_spinner=False)
def checkin_erklaerung(name_norm: str, datum: str) -> dict:
    """
    Warum steht dieser Check-in in der Liste?

    Drei mögliche Gründe, und die machen einen grossen Unterschied:

      • Der Name hat an dem Tag selbst gespielt, aber ohne Rabatt →
        der Check-in ist erklärt, nur gibt es keinen Anspruch dazu
      • Ein ähnlicher Name hat gespielt → wahrscheinlich eine andere
        Schreibweise, gehört zusammengeführt
      • Niemand passt → derjenige war wohl gar nicht da, oder es ist
        eine Nachholung für einen früheren Tag

    → {"art": …, "text": …, "treffer": …}
    """
    b = loadsheet("buchungen")
    if b.empty or "analysis_date" not in b.columns:
        return {"art": "unklar", "text": "", "treffer": ""}

    tag = b[b["analysis_date"].astype(str) == str(datum)]
    if tag.empty:
        return {"art": "kein_spiel",
                "text": "an diesem Tag gibt es keine Buchungen",
                "treffer": ""}

    # Exakt derselbe Name mit einer Buchung an dem Tag?
    eigene = tag[tag["Name_norm"].astype(str) == str(name_norm)]
    if not eigene.empty:
        mit_rabatt = (eigene["Relevant"].astype(str) == "Ja").any()
        if mit_rabatt:
            return {"art": "gespielt_rabatt",
                    "text": "hat an diesem Tag mit Rabatt gespielt",
                    "treffer": str(eigene.iloc[0]["Name"])}
        return {"art": "gespielt_ohne_rabatt",
                "text": "hat gespielt, aber ohne Wellpass-Rabatt bezahlt — "
                        "es gibt keinen Anspruch dazu",
                "treffer": str(eigene.iloc[0]["Name"])}

    # Ähnlicher Name mit Buchung — vermutlich andere Schreibweise
    kandidaten = tag.drop_duplicates(subset=["Name_norm"])
    bester, bester_score, beste_zeit = None, 0.0, ""
    for _, r in kandidaten.iterrows():
        treffer = fuzzy_match(str(name_norm), [str(r["Name_norm"])], {}, set())
        if treffer and treffer[0][1] > bester_score:
            bester = str(r["Name"])
            bester_score = treffer[0][1]
            beste_zeit = str(r.get("Service_Zeit", ""))

    if bester and bester_score >= 65:
        return {"art": "aehnlicher_name",
                "text": f"ähnlicher Name mit Buchung um {beste_zeit} "
                        f"({bester_score:.0f} %) — vermutlich dieselbe Person",
                "treffer": bester}

    return {"art": "kein_spiel",
            "text": "keine passende Buchung an diesem Tag — "
                    "entweder nicht gespielt oder Nachholung für einen "
                    "früheren Tag",
            "treffer": ""}


@st.cache_data(ttl=600, show_spinner=False)
def redundante_korrekturen() -> pd.DataFrame:
    """
    Erledigte Fälle, die sich von selbst erledigen würden.

    Hast du „Ist dieselbe Person" geklickt, ist die Verknüpfung dauerhaft
    gespeichert. Der Fall löst sich dann allein durch das Mapping — der
    Eintrag in den Korrekturen ist nur noch Ballast.

    Nicht redundant und deshalb unantastbar:
      • Nachholungen von einem anderen Tag — die hängen am Check-in,
        nicht am Namen
      • Alles, was du von Hand entschieden hast: nicht gespielt,
        bezahlt, Kulanz. Das kann keine Logik der Welt rekonstruieren.
    """
    df = erledigte_faelle()
    if df.empty:
        return pd.DataFrame()

    gedeckt = mapping_gedeckt_je_tag()
    if not gedeckt:
        return pd.DataFrame()

    zuordnung = loadsheet("checkin_zuordnung",
                          SHEET_SPALTEN["checkin_zuordnung"])
    # Fälle, die an einem Check-in von einem anderen Tag hängen
    fremde_nachholung = set()
    if not zuordnung.empty and "fall_key" in zuordnung.columns:
        for _, z in zuordnung.iterrows():
            if str(z.get("checkin_datum")) != str(z.get("fall_datum")):
                fremde_nachholung.add(
                    f"{z.get('fall_name')}_{z.get('fall_datum')}")

    behalten = []
    for _, r in df.iterrows():
        key = f"{r['name_norm']}_{r['datum']}"
        if key in fremde_nachholung:
            behalten.append(False)
            continue
        # Nur solche, die das Mapping ohnehin abdeckt
        behalten.append(
            str(r["name_norm"]) in gedeckt.get(str(r["datum"]), set()))

    return df[pd.Series(behalten, index=df.index)]


def korrekturen_aufraeumen() -> int:
    """Die redundanten Einträge entfernen. → Anzahl"""
    weg = redundante_korrekturen()
    if weg.empty:
        return 0

    corr = loadsheet("corrections", SHEET_SPALTEN["corrections"])
    if corr.empty or "key" not in corr.columns:
        return 0

    raus = {f"{r['name_norm']}_{r['datum']}" for _, r in weg.iterrows()}
    behalten = corr[~corr["key"].astype(str).isin(raus)]
    savesheet(behalten, "corrections")
    cache_leeren()
    return len(corr) - len(behalten)


def _wa_seitenspalte(datum: str, offen_heute: pd.DataFrame):
    """Überzählige Check-ins — zum Zuordnen."""
    rueck = fenster_rueckblick()
    heute = parse_date_safe(datum) or date.today()

    st.markdown("##### Überzählige Check-ins")

    umfang = st.radio(
        "Zeitraum", ["Nur dieser Tag", f"Letzte {rueck} Tage"],
        key=f"uez_umfang_{datum}", horizontal=True,
        label_visibility="collapsed")

    if umfang == "Nur dieser Tag":
        von = bis = heute
        st.caption(f"{datum_kurz(datum)} · eingecheckt, aber keiner "
                   "Buchung zugeordnet")
    else:
        von = heute - timedelta(days=rueck)
        bis = heute + timedelta(days=fenster_nachhol())
        st.caption(f"letzte {rueck} Tage · eingecheckt, aber keiner "
                   "Buchung zugeordnet")

    ueber = offene_checkins_zeitraum(von, bis)

    if ueber.empty:
        box("✅ Keine überzähligen Check-ins in diesem Zeitraum.", "ok")
        return

    st.markdown(f'<div class="pc-zahl">{len(ueber)}</div>'
                f'<div class="pc-zahl-sub">offen · '
                f'{euro(len(ueber) * wellpass_wert_am(datum))} bereits vergütet</div>',
                unsafe_allow_html=True)
    st.markdown("")

    # Zuordnungsziele: offene Fälle des gewählten Tages UND die davor.
    #
    # Ein nachgeholter Check-in gehört fast immer zu einem älteren Fall.
    # Vorher standen nur die Fälle des angezeigten Tages zur Auswahl —
    # bei einem Check-in, der Tage später kam, war die Liste leer und
    # die Zuordnung von Hand unmöglich.
    ziele, ziele_alt = {}, {}
    for _, f in offen_heute.iterrows():
        ziele[f"{f['Name']}  ·  {str(f.get('Service_Zeit',''))}"] = (
            str(f["Name_norm"]), str(f["Datum"]))

    grenze = str((heute - timedelta(days=fenster_nachhol())))
    for tag in verfuegbare_tage():
        if not (grenze <= str(tag) < str(datum)):
            continue
        for _, f in offene_fehler(tag).iterrows():
            schluessel = (f"{f['Name']}  ·  {datum_kurz(tag)}"
                          f" {str(f.get('Service_Zeit',''))}")
            ziele_alt[schluessel] = (str(f["Name_norm"]), str(f["Datum"]))

    # Liegen passende Fälle knapp ausserhalb des Fensters? Dann ist die
    # Einstellung das Problem, nicht die Datenlage — das soll man sehen,
    # statt vor einer leeren Liste zu stehen.
    aelter_ausserhalb = 0
    if not ueber.empty:
        for tag in verfuegbare_tage():
            if str(tag) >= grenze or str(tag) >= str(datum):
                continue
            aelter_ausserhalb += len(offene_fehler(tag))

    if not ziele and not ziele_alt:
        box("Für diesen Tag und die Tage davor gibt es keine offenen "
            "Fälle zum Zuordnen.", "info")
    elif not ziele and ziele_alt:
        st.caption(f"Keine offenen Fälle am {datum_kurz(datum)} — angeboten "
                   f"werden die {len(ziele_alt)} offenen Fälle der letzten "
                   f"{fenster_nachhol()} Tage.")

    if aelter_ausserhalb:
        box(f"👀 <b>{aelter_ausserhalb} weitere offene Fälle</b> liegen mehr "
            f"als {fenster_nachhol()} Tage zurück und werden deshalb nicht "
            "angeboten. Passt keiner der Vorschläge, erhöhe das "
            "Nachhol-Fenster unter <i>Einstellungen → Zuordnung</i>.", "info")

    # Zielnamen einmal vorbereiten — vorher wurden Normalisierung und
    # E-Mail-Suche für jeden Check-in erneut durchlaufen, und danach im
    # Anzeige-Block gleich noch ein zweites Mal.
    ziel_daten = []
    for label in ziele:
        klarname = label.split("  ·  ")[0]
        ziel_daten.append((label, normalize_name(klarname),
                           email_fuer(klarname)))

    # Nach Relevanz sortieren: passende zuerst, dann zeitlich nah
    ueber = ueber.copy()
    raenge, naehen, beste = [], [], []
    for _, r in ueber.iterrows():
        ci_norm = str(r["Name_norm"])
        ci_name = str(r["Name"])
        bester_key, bester = None, 0.0
        for label, ziel_norm, ziel_mail in ziel_daten:
            sc = fuzz.token_set_ratio(ziel_norm, ci_norm)
            if ziel_mail:
                sc = max(sc, email_aehnlichkeit(ziel_mail, ci_name))
            if sc >= bester:
                bester_key, bester = label, sc
        ci_d = parse_date_safe(str(r["analysis_date"]))
        raenge.append(bester)
        naehen.append(abs((ci_d - heute).days) if ci_d else 99)
        beste.append(bester_key)
    ueber["_rang"] = raenge
    ueber["_naehe"] = naehen
    ueber["_bester"] = beste
    ueber = ueber.sort_values(["_rang", "_naehe"], ascending=[False, True])

    passend = int((ueber["_rang"] >= 80).sum())
    if passend and ziele:
        box(f"<b>{passend}</b> passen zu einem Fall dieses Tages.", "ok")

    nur_passend = False
    if len(ueber) > 12:
        nur_passend = st.toggle("Nur passende zeigen", value=bool(passend),
                                key=f"uez_filter_{datum}")
    if nur_passend:
        ueber = ueber[ueber["_rang"] >= 70]
        if ueber.empty:
            box("Keine passenden Check-ins für diesen Tag.", "info")
            return

    st.markdown("")

    for i, (_, r) in enumerate(ueber.head(30).iterrows()):
        ci_datum = str(r["analysis_date"])
        ci_name = str(r["Name"])
        ci_norm = str(r["Name_norm"])
        ci_zeit = str(r.get("Checkin_Zeit", "")).strip()
        abstand = (parse_date_safe(ci_datum) - heute).days \
            if parse_date_safe(ci_datum) else 0

        if abstand == 0:
            hinweis = "gleicher Tag"
        elif abstand > 0:
            hinweis = f"{abstand} Tage danach"
        else:
            hinweis = f"{abs(abstand)} Tage davor"

        # Bester Treffer steht schon aus der Bewertung oben fest
        bester_key = r.get("_bester")
        bester_score = float(r.get("_rang", 0))

        rahmen = "pc-uez treffer" if bester_score >= 80 else "pc-uez"
        warnung = nachhol_warnung(ci_norm, ci_datum) if abstand != 0 else ""
        erklaerung = checkin_erklaerung(ci_norm, ci_datum)
        st.markdown(
            f'<div class="{rahmen}">'
            f'<div class="nm">{ci_name}</div>'
            f'<div class="mt">{datum_kurz(ci_datum)}'
            + (f' · {ci_zeit}' if ci_zeit else '')
            + f' · {hinweis}</div></div>', unsafe_allow_html=True)

        # Warum steht er hier? Ohne das ist die Liste nicht zu deuten.
        if erklaerung["art"] == "gespielt_ohne_rabatt":
            box(f"ℹ️ <b>{erklaerung['treffer']}</b> {erklaerung['text']}.",
                "info")
        elif erklaerung["art"] == "aehnlicher_name":
            st.caption(f"↳ {erklaerung['treffer']}: {erklaerung['text']}")
            # Direkt verknüpfen — unabhängig davon, ob es dazu einen
            # offenen Fall gibt. Sonst bleibt so ein Check-in ewig
            # liegen, weil er nirgends auftaucht wo man ihn zuordnen kann.
            ziel_norm = normalize_name(erklaerung["treffer"])
            if st.button(f"↔ Ist {erklaerung['treffer']}",
                         key=f"uez_map_{datum}_{i}", use_container_width=True):
                mapping_hinzufuegen(ziel_norm, ci_norm, bester_score)
                cache_leeren()
                st.toast("Als dieselbe Person gemerkt.")
                st.rerun()
        elif warnung:
            box(warnung, "warn")
        elif abstand != 0:
            st.caption(f"↳ {erklaerung['text']}")

        alle_ziele = {**ziele, **ziele_alt}
        if not alle_ziele:
            continue

        if bester_score >= 80 and bester_key in ziele:
            if st.button(f"✓ = {bester_key.split('  ·  ')[0]}",
                         key=f"uez_q_{datum}_{i}",
                         type="secondary" if warnung else "primary",
                         use_container_width=True):
                nn, dt = ziele[bester_key]
                if nachholung_speichern(ci_datum, ci_norm, dt, nn):
                    st.toast("Zugeordnet.")
                    st.rerun()

        with st.expander("Anderem Fall zuordnen"):
            # Nach Namensähnlichkeit sortiert — der wahrscheinlichste
            # Treffer steht oben, auch wenn er von einem früheren Tag ist.
            sortiert = sorted(
                alle_ziele.keys(),
                key=lambda k: -fuzz.token_set_ratio(
                    _vergleichsform(normalize_name(k.split("  ·  ")[0])),
                    _vergleichsform(ci_norm)))

            def _ziel_label(k):
                if k == "—":
                    return "—"
                klar = k.split("  ·  ")[0]
                punkte = fuzz.token_set_ratio(
                    _vergleichsform(normalize_name(klar)),
                    _vergleichsform(ci_norm))
                aelter = " · früherer Tag" if k in ziele_alt else ""
                return f"{k}   ({punkte:.0f} %{aelter})"

            wahl = st.selectbox("Fall", ["—"] + sortiert,
                                format_func=_ziel_label,
                                key=f"uez_s_{datum}_{i}",
                                label_visibility="collapsed")
            if wahl != "—":
                nn, dt = alle_ziele[wahl]
                if dt != ci_datum:
                    st.caption(f"Fall vom {datum_kurz(dt)} — der Check-in "
                               f"kam {(parse_date_safe(ci_datum) - parse_date_safe(dt)).days} "
                               "Tage später.")
                if st.button("Zuordnen", key=f"uez_b_{datum}_{i}",
                             use_container_width=True):
                    if nachholung_speichern(ci_datum, ci_norm, dt, nn):
                        st.toast("Zugeordnet.")
                        st.rerun()
        st.markdown("")


def _wa_fall(r, i: int, datum: str):
    """Ein einzelner Fall mit allen Aktionen."""
    name = str(r["Name"])
    nn = str(r["Name_norm"])
    betrag = r.get("Betrag", 0)
    zeit = str(r.get("Service_Zeit", "")).strip()
    court = str(r.get("Court", "")).strip()
    nummer = telefon_fuer(name)
    mail = email_fuer(name)
    gesendet = schon_gesendet(nn, datum, betrag)

    liste_r = parse_betrag(r.get("Listenpreis", 0))
    bezahlt_r = parse_betrag(r.get("Bezahlt", 0))

    # Zweite rabattierte Buchung am selben Tag? Dann ist es kein
    # vergessener Check-in, sondern ein unbezahlter Platz.
    zweitbuchung = ist_zweitbuchung(nn, datum)

    status = ""
    if zweitbuchung:
        status = '<span class="pc-chip warn">2. Buchung am Tag</span>'
    elif gesendet:
        seit = (datetime.now() - gesendet).days
        frist = fenster_nachhol()
        if seit > frist:
            status = '<span class="pc-chip err">Frist abgelaufen</span>'
        else:
            status = (f'<span class="pc-chip soft">angeschrieben · '
                      f'noch {frist - seit} Tage</span>')

    st.markdown(
        f'<div class="pc-card"><div class="pc-fall">'
        f'<div><span class="nm">{name}</span>'
        f'<span class="mt">&nbsp;· {zeit} Uhr · {court} · '
        f'{euro(liste_r)} → {euro(bezahlt_r)}</span></div>'
        f'<div>{status}</div></div></div>', unsafe_allow_html=True)

    k1, k2 = st.columns(2)
    with k1:
        st.caption(f"📱 {nummer}" if len(nummer) > 5 else "📱 keine Nummer")
    with k2:
        st.caption(f"✉️ {mail}" if mail else "✉️ keine E-Mail")

    if zweitbuchung:
        offen_betrag = round(max(0.0, parse_betrag(r.get("Betrag", 0))
                                 or (liste_r - bezahlt_r)), 2)
        box(f"⚠️ <b>Zweite Buchung an diesem Tag.</b> "
            f"{name} hat am {datum_kurz(datum)} bereits eingecheckt — "
            "Wellpass vergütet aber nur einen Check-in pro Person und Tag. "
            "Dieser Platz ist also unbezahlt geblieben. Kein vergessener "
            "Check-in, sondern eine offene Zahlung.", "warn")
        st.caption(f"Nachzuzahlen: {euro(offen_betrag)} · beim Erledigen "
                   "den Grund „Bezahlt\" mit dem tatsächlichen Betrag wählen")

    # ── Vorschlag am selben Tag ─────────────────────────────────────
    #
    # Bei einer Zweitbuchung ist der Check-in bereits vorhanden und
    # verbraucht — eine Namenszuordnung oder Nachholung würde den Fall
    # fälschlich schliessen. Beides bleibt deshalb aus.
    vorschlaege = ([] if zweitbuchung
                   else zuordnung_vorschlag(name, datum, mail=mail, zeit=zeit))
    if vorschlaege:
        bester, bester_norm, score, ci_zeit, grund = vorschlaege[0]
        sicherheit = ("lime" if score >= 85 else "warn" if score >= 70 else "err")
        st.markdown(
            f'<div class="pc-vorschlag"><b>{bester}</b>'
            + (f' um {ci_zeit}' if ci_zeit else '')
            + f' hat eingecheckt — dieselbe Person? '
            f'{chip(f"{score:.0f}%", sicherheit)} '
            f'<span class="grund">{grund}</span></div>',
            unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        with v1:
            if st.button("✓ Ist dieselbe", key=f"wa_zu_{datum}_{i}",
                         type="primary", use_container_width=True):
                mapping_hinzufuegen(nn, bester_norm, score)
                if nachholung_speichern(datum, bester_norm, datum, nn):
                    st.toast("Gemerkt.")
                    st.rerun()
        with v2:
            if st.button("✗ Nein", key=f"wa_ab_{datum}_{i}",
                         use_container_width=True):
                rejected_speichern(nn, bester_norm)
                st.rerun()

    # ── Nachholung an einem Folgetag ────────────────────────────────
    nachhol = ([] if zweitbuchung
               else [x for x in nachhol_kandidaten(name, datum) if x[4] > 0])
    if nachhol:
        a, kn, cd, sc, tg = nachhol[0]
        st.markdown(
            f'<div class="pc-vorschlag nachhol">🔄 <b>{a}</b> hat am '
            f'<b>{datum_kurz(cd)}</b> eingecheckt — {tg} '
            + ("Tag" if tg == 1 else "Tage") + f' später. '
            f'{chip(f"{sc:.0f}%", "lime" if sc >= 85 else "warn")}</div>',
            unsafe_allow_html=True)

        # Beleg zeigen, nicht nur behaupten
        eigene = eigener_anspruch(kn, cd)
        st.caption(
            f"Beleg: „{a}“ hat am {datum_kurz(cd)} "
            + ("**nicht gespielt** — der Check-in gehört zu keiner Buchung."
               if not eigene else
               f"**selbst {eigene}× gespielt** — Vorsicht.")
            + f"  ·  Namensähnlichkeit {sc:.0f} %")

        warnung = nachhol_warnung(kn, cd)
        if warnung:
            box(warnung, "warn")

        if st.button("✓ Nachgeholt — Fall schliessen",
                     key=f"wa_nh_{datum}_{i}",
                     type="secondary" if warnung else "primary",
                     use_container_width=True):
            if nachholung_speichern(cd, kn, datum, nn):
                st.toast("Fall geschlossen.")
                st.rerun()

    # ── Aktionen ────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        kann = len(nummer) > 5 and twilio_bereit()
        beschriftung = "Erneut senden" if gesendet else "Senden"
        if st.button(beschriftung, key=f"wa_s_{datum}_{i}", type="primary",
                     use_container_width=True, disabled=not kann):
            txt = (zweitbuchung_nachricht(name, datum_kurz(datum), zeit,
                                          parse_betrag(r.get("Betrag", 0)))
                   if zweitbuchung
                   else reminder_nachricht(name, datum_kurz(datum), zeit))
            with st.spinner("Sende…"):
                if whatsapp_senden(f"whatsapp:{nummer}", txt):
                    whatsapp_loggen(name, nn, datum, betrag, nummer)
                    st.toast("✅")
                    st.rerun()
    with c2:
        if st.button("Nachfassen", key=f"wa_n_{datum}_{i}",
                     use_container_width=True,
                     disabled=not (gesendet and len(nummer) > 5
                                   and twilio_bereit())):
            txt = zweiter_reminder(name, datum_kurz(datum))
            with st.spinner("Sende…"):
                if whatsapp_senden(f"whatsapp:{nummer}", txt):
                    whatsapp_loggen(name, nn, datum, betrag, nummer,
                                    art="nachfassen")
                    st.toast("✅")
                    st.rerun()
    with c3:
        _erledigt_knopf(nn, datum, key=f"wa_e_{datum}_{i}")

    with st.expander("Nachricht ansehen"):
        st.code(zweitbuchung_nachricht(name, datum_kurz(datum), zeit,
                                       parse_betrag(r.get("Betrag", 0)))
                if zweitbuchung
                else reminder_nachricht(name, datum_kurz(datum), zeit),
                language=None)
    st.markdown("")


def _wa_tagesarbeit():
    """Ein Tag, alle Fälle — mit den überzähligen Check-ins daneben."""
    tage_alle = verfuegbare_tage()
    if not tage_alle:
        box("Noch keine Daten. Starte in der Daten-Zentrale.", "warn")
        return

    # Erst die eindeutigen Fälle wegräumen, dann der Rest von Hand —
    # auf ALLEN Tagen, unabhängig vom Filter unten.
    _wa_auto_block(tage_alle)

    # Alle Tageszähler in EINEM Durchlauf statt einer pro Dropdown-Eintrag
    zaehler = offene_je_tag()

    nur_offene = st.checkbox(
        "Nur Tage mit offenen Fällen anzeigen", key="wa_nur_offene_tage",
        help="Blendet Tage aus, die schon sauber sind — für den "
             "Überblick beim Nacharbeiten mehrerer Tage.")
    tage = [t for t in tage_alle if zaehler.get(str(t), 0) > 0] \
        if nur_offene else tage_alle
    if not tage:
        box("✅ Alle Tage sind sauber — keine offenen Fälle.", "ok")
        return

    # Auswahl läuft direkt über den Widget-Wert — siehe Kommentar im
    # Dashboard. Mit einem separaten Index blieb das Datum stehen.
    if ("wa_tag_wahl" not in st.session_state
            or st.session_state.wa_tag_wahl not in tage):
        st.session_state.wa_tag_wahl = tage[0]

    idx = tage.index(st.session_state.wa_tag_wahl)

    # Der Schlüssel enthält die Zählerstände und den gewählten Tag.
    # Ändert sich einer von beiden, baut Streamlit das Feld neu auf.
    # Ohne das behielt die geschlossene Anzeige ihre alte Beschriftung —
    # oben stand noch "1 offen", während in der Liste schon "sauber" stand.
    stand = f"{idx}_{hash(tuple(sorted(zaehler.items())))}"
    wahl_key = f"wa_tag_wahl_{stand}"
    for alt in [k for k in list(st.session_state)
                if k.startswith("wa_tag_wahl_") and k != wahl_key]:
        del st.session_state[alt]

    n1, n2, n3 = st.columns([1, 3, 1])
    with n1:
        if st.button("← Früher", use_container_width=True,
                     disabled=idx >= len(tage) - 1, key="wa_frueher"):
            st.session_state.wa_tag_wahl = tage[idx + 1]
            st.rerun()
    with n3:
        if st.button("Später →", use_container_width=True,
                     disabled=idx <= 0, key="wa_spaeter"):
            st.session_state.wa_tag_wahl = tage[idx - 1]
            st.rerun()
    with n2:
        def _tag_label(t):
            n = zaehler.get(str(t), 0)
            return datum_lang(t) + (f"  ·  {n} offen" if n else "  ·  sauber")

        gewaehlt = st.selectbox("Tag", tage, index=idx,
                                format_func=_tag_label,
                                label_visibility="collapsed", key=wahl_key)
        if gewaehlt != st.session_state.wa_tag_wahl:
            st.session_state.wa_tag_wahl = gewaehlt
            st.rerun()

    datum = st.session_state.wa_tag_wahl
    offen = offene_fehler(datum)

    st.markdown("")

    # ── Kennzahlen des Tages ────────────────────────────────────────
    angeschrieben = 0
    for _, r in offen.iterrows():
        if schon_gesendet(str(r["Name_norm"]), datum, r.get("Betrag", 0)):
            angeschrieben += 1

    k1, k2, k3 = st.columns(3)
    with k1:
        kpi("Offene Fälle", str(len(offen)), datum_lang(datum))
    with k2:
        kpi("Angeschrieben", str(angeschrieben),
            f"{len(offen) - angeschrieben} noch nicht")
    with k3:
        kpi("Offener Wert", euro(len(offen) * wellpass_wert_am(datum)))

    st.markdown("")

    # ── Zwei Spalten ────────────────────────────────────────────────
    links, rechts = st.columns([2, 1], gap="medium")

    with links:
        if offen.empty:
            box("✅ Für diesen Tag ist alles geklärt.", "ok")
        else:
            offen = offen.copy()
            offen["_nummer"] = offen["Name"].map(telefon_fuer)
            erreichbar = offen[offen["_nummer"].astype(str).str.len() > 5]

            if twilio_bereit() and not erreichbar.empty:
                noch_offen = [r for _, r in erreichbar.iterrows()
                              if not schon_gesendet(str(r["Name_norm"]), datum,
                                                    r.get("Betrag", 0))]
                if noch_offen:
                    if st.button(f"⚡ Alle {len(noch_offen)} anschreiben",
                                 type="primary", use_container_width=True,
                                 key=f"wa_alle_{datum}"):
                        balken = st.progress(0.0)
                        gesendet = 0
                        for j, r in enumerate(noch_offen):
                            balken.progress((j + 1) / len(noch_offen))
                            txt = reminder_nachricht(
                                str(r["Name"]), datum_kurz(datum),
                                str(r.get("Service_Zeit", "")))
                            if whatsapp_senden(f"whatsapp:{r['_nummer']}", txt):
                                whatsapp_loggen(str(r["Name"]), str(r["Name_norm"]),
                                                datum, r.get("Betrag", 0),
                                                str(r["_nummer"]))
                                gesendet += 1
                            time.sleep(0.4)
                        balken.progress(1.0)
                        st.success(f"✅ {gesendet} Nachrichten verschickt")
                        if gesendet:
                            st.balloons()
                        st.rerun()
                    st.markdown("")

            for i, (_, r) in enumerate(offen.iterrows()):
                _wa_fall(r, i, datum)

    with rechts:
        _wa_seitenspalte(datum, offen)


@st.cache_data(ttl=600, show_spinner=False)
def checkin_zuordnungen(datum: str) -> pd.DataFrame:
    """
    Für einen Tag: jeder EGYM-Check-in und die Buchung, der er
    zugerechnet wurde.

    Zum Nachprüfen gedacht — nicht zum Rechnen. Zeigt genau das, was
    die App intern angenommen hat, damit Fehlzuordnungen auffallen.
    """
    c = loadsheet("checkins")
    b = loadsheet("buchungen")
    if c.empty or "analysis_date" not in c.columns:
        return pd.DataFrame()

    tag_c = c[c["analysis_date"].astype(str) == str(datum)].copy()
    if tag_c.empty:
        return pd.DataFrame()
    tag_c = tag_c.drop_duplicates(subset=["Name_norm"])

    tag_b = (b[b["analysis_date"].astype(str) == str(datum)]
             if not b.empty and "analysis_date" in b.columns
             else pd.DataFrame())

    mapping = mapping_laden()
    rueck = {}
    for buchung_name, ziel in mapping.items():
        gname = str(ziel["checkin_name"] if isinstance(ziel, dict) else ziel)
        rueck.setdefault(gname, []).append(str(buchung_name))

    verbraucht = verbrauchte_checkins()

    zeilen = []
    for _, r in tag_c.iterrows():
        ci_norm = str(r["Name_norm"])
        eintrag = {
            "Check-in": str(r["Name"]),
            "Zeit": str(r.get("Checkin_Zeit", "")),
            "Zugeordnet zu": "",
            "E-Mail": "",
            "Court": "",
            "Spielzeit": "",
            "Weg": "",
        }

        # 1. Nachholung für einen anderen Tag
        ziel_fall = verbraucht.get(checkin_schluessel(str(datum), ci_norm))
        if ziel_fall:
            fall_datum, fall_name = str(ziel_fall).split("|", 1)
            eintrag["Zugeordnet zu"] = fall_name
            eintrag["Spielzeit"] = datum_kurz(fall_datum)
            eintrag["Weg"] = ("Nachholung für einen früheren Tag"
                              if fall_datum != str(datum)
                              else "von dir zugeordnet")
            zeilen.append(eintrag)
            continue

        # 2. Direkt über den Namen
        treffer = (tag_b[tag_b["Name_norm"].astype(str) == ci_norm]
                   if not tag_b.empty else pd.DataFrame())
        weg = "Name identisch"

        # 3. Über eine bestätigte Verknüpfung
        if treffer.empty and ci_norm in rueck and not tag_b.empty:
            treffer = tag_b[tag_b["Name_norm"].astype(str).isin(rueck[ci_norm])]
            weg = "bestätigte Verknüpfung"

        if treffer.empty:
            eintrag["Zugeordnet zu"] = "— keiner Buchung —"
            eintrag["Weg"] = checkin_erklaerung(ci_norm, datum)["text"]
        else:
            z = treffer.iloc[0]
            eintrag["Zugeordnet zu"] = str(z["Name"])
            eintrag["E-Mail"] = str(z.get("Email", "") or "")
            eintrag["Court"] = str(z.get("Court", "") or "")
            eintrag["Spielzeit"] = str(z.get("Service_Zeit", "") or "")
            eintrag["Weg"] = weg
        zeilen.append(eintrag)

    return pd.DataFrame(zeilen)


def _wa_pruefen():
    """Zuordnungen eines Tages zum Nachprüfen."""
    tage = verfuegbare_tage()
    if not tage:
        box("Noch keine Daten.", "warn")
        return

    box("Hier steht für jeden EGYM-Check-in, welcher Buchung die App ihn "
        "zugerechnet hat — und auf welchem Weg. Reine Kontrollansicht: "
        "Nichts davon lässt sich hier ändern.", "info")

    datum = st.selectbox("Tag", tage, format_func=datum_lang,
                         key="pruef_tag")

    df = checkin_zuordnungen(datum)
    if df.empty:
        box("An diesem Tag gab es keine Check-ins.", "info")
        return

    zugeordnet = int((df["Zugeordnet zu"] != "— keiner Buchung —").sum())
    p1, p2, p3 = st.columns(3)
    with p1:
        kpi("Check-ins", str(len(df)))
    with p2:
        kpi("Zugeordnet", str(zugeordnet))
    with p3:
        kpi("Offen", str(len(df) - zugeordnet),
            euro(len(df) * wellpass_wert_am(datum)) + " vergütet")

    st.markdown("")
    st.dataframe(df, use_container_width=True, hide_index=True,
                 height=min(600, 60 + 35 * len(df)))

    st.download_button(
        "⬇️ Als CSV",
        data=df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"zuordnungen_{datum}.csv", mime="text/csv",
        use_container_width=True)

    st.caption("Spalte Weg — 'Name identisch' heisst, Playtomic und EGYM "
               "schreiben denselben Namen. 'Bestätigte Verknüpfung' heisst, "
               "du oder die Automatik habt die beiden Namen einmal "
               "zusammengeführt.")


def _freigabe_dialog(name: str, name_norm: str):
    """Der Hinweis, dass jemand wieder freigegeben werden muss."""
    box(f"🔓 <b>{name} hat keine offene Sperre mehr.</b><br>"
        "Der Wellpass-Zugang ist damit nicht automatisch wieder offen — "
        "das musst du bei EGYM selbst freischalten. Erst danach hier "
        "bestätigen.", "warn")
    f1, f2 = st.columns([1.4, 1])
    with f1:
        if st.button("✅ Zugang wieder freigegeben", key=f"fg_ok_{name_norm}",
                     use_container_width=True, type="primary"):
            freigabe_bestaetigen(name_norm)
            st.toast(f"{name} ist freigegeben.")
            st.rerun()
    with f2:
        if st.button("Später", key=f"fg_spaeter_{name_norm}",
                     use_container_width=True):
            st.rerun()


def _freigaben_anzeigen():
    """
    Wer wieder freigegeben werden muss — bewusst ganz oben.

    Die Aufgabe bleibt so lange stehen, bis sie bestätigt wird. Ein
    Spieler, dessen Sperre rechnerisch erledigt ist, aber bei EGYM noch
    hängt, ist sonst der Fall, der niemandem auffällt.
    """
    freigaben = offene_freigaben()
    if freigaben.empty:
        return

    st.markdown("##### 🔓 Freigabe nötig")
    for _, f in freigaben.iterrows():
        nn = str(f["name_norm"])
        name = str(f.get("name") or nn)
        # Als echtes Fenster, wo Streamlit es kann — sonst als
        # hervorgehobener Kasten an derselben Stelle.
        dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
        if dialog and not st.session_state.get(f"_fg_gesehen_{nn}"):
            st.session_state[f"_fg_gesehen_{nn}"] = True

            @dialog(f"{name} wieder freigeben?")
            def _zeigen(name=name, nn=nn):
                _freigabe_dialog(name, nn)
            _zeigen()
        else:
            _freigabe_dialog(name, nn)
    st.markdown("---")


def _gesperrt_zeile(g, i: int):
    """
    Eine gesperrte Person mit der Möglichkeit, einen nachgeholten
    Check-in von Hand einer ihrer Sperren zuzuordnen.
    """
    nn = str(g["Name_norm"])
    name = str(g["Name"])
    anzahl = int(g["Anzahl gesperrt"])

    s1, s2 = st.columns([2.6, 1.2])
    with s1:
        farbe = "err" if anzahl > 1 else "warn"
        st.markdown(f"**{name}**  {chip(f'{anzahl}× gesperrt', farbe)}",
                    unsafe_allow_html=True)
        st.caption(f"Spieltage: {g['Tage']}")
    with s2:
        with st.popover("Check-in zuordnen", use_container_width=True):
            _sperre_zuordnen(nn, name, i)


def _sperre_zuordnen(nn: str, name: str, i: int):
    """
    Auswahl: welcher nachgeholte Check-in gehört zu welcher Sperre?

    Beides wird ausdrücklich gewählt. Automatisch passiert hier nichts —
    ein Check-in bringt Geld und eine Sperre trifft einen Menschen.
    """
    faelle = gesperrt_faelle(nn)
    if faelle.empty:
        st.caption("Keine offene Sperre mehr.")
        return

    st.caption("1 · Welche Sperre wird ausgeglichen?")
    tage = [str(x) for x in faelle["datum"]]
    ziel = st.radio("Sperre", tage, key=f"sp_fall_{i}",
                    format_func=lambda t: f"Spieltag {datum_kurz(t)}",
                    label_visibility="collapsed")

    # Für Gesperrte gilt ein weiteres Zeitfenster — die melden sich
    # selten innerhalb der üblichen fünf Tage.
    fenster = int(einstellung("sperre_nachhol_fenster_tage",
                              CONFIG["sperre_nachhol_fenster_tage"]))
    kandidaten = [k for k in nachhol_kandidaten(name, ziel, fenster=fenster)
                  if k[4] > 0]

    st.caption("2 · Welcher Check-in wird dafür verwendet?")
    if not kandidaten:
        st.caption(f"Kein freier Check-in in den {fenster} Tagen nach "
                   f"dem {datum_kurz(ziel)} gefunden.")
        return

    for k, (anzeige, kand_norm, ci_datum, score, tage_danach) in enumerate(kandidaten[:8]):
        st.markdown(f"**{anzeige}** · {datum_kurz(ci_datum)} "
                    f"({tage_danach} Tage später) · {score:.0f}%")
        warnung = nachhol_warnung(kand_norm, ci_datum)
        if warnung:
            box(warnung, "warn")
        if st.button("Diesen zuordnen", key=f"sp_zu_{i}_{k}",
                     use_container_width=True):
            if sperre_nachholung_zuordnen(nn, name, ziel, ci_datum, kand_norm):
                st.toast(f"Check-in zugeordnet — eine Sperre weniger für {name}.")
                st.rerun()


def _wa_uebersicht():
    """
    Der Überblick über alle Tage — nicht Tag für Tag, sondern pro Person.

    Gedacht für den Nachhol-Fall: wenn viele Tage auf einmal
    durchgearbeitet werden, geht in der Tag-für-Tag-Ansicht unter, dass
    dieselbe Person schon zum zweiten oder dritten Mal fehlt.
    """
    box("Zusammengefasst über alle Tage — für den Überblick, wenn du "
        "gerade mehrere Tage auf einmal nachholst.", "info")

    # ── Offene Fälle pro Person ─────────────────────────────────────────
    st.markdown("##### Offene Fälle pro Person")
    offen = offene_uebersicht()
    if offen.empty:
        box("✅ Keine offenen Fälle.", "ok")
    else:
        st.caption(f"{offen['Anzahl offen'].sum()} offene Fälle · "
                   f"{len(offen)} Personen")
        st.dataframe(
            offen[["Name", "Anzahl offen", "Ältester offener Fall", "Tage"]],
            use_container_width=True, hide_index=True,
            height=min(500, 60 + 35 * len(offen)))

    st.markdown("")
    st.markdown("---")

    # ── Freigabe nötig ───────────────────────────────────────────────────
    _freigaben_anzeigen()

    # ── Gesperrt-Historie ────────────────────────────────────────────────
    st.markdown("##### Gesperrte Spieler")
    st.caption("Je Person ein Eintrag pro fehlendem Check-in. Holt jemand "
               "einen nach, ordnest du ihn hier von Hand einer Sperre zu — "
               "die Zahl sinkt um eins.")
    gesperrt = gesperrt_historie()
    if gesperrt.empty:
        box('Noch niemand als „Gesperrt" erledigt markiert.', "info")
    else:
        wiederholt = int((gesperrt["Anzahl gesperrt"] > 1).sum())
        if wiederholt:
            box(f"⚠️ <b>{wiederholt} Personen</b> wurden mehrfach gesperrt.",
                "warn")
        for i, (_, g) in enumerate(gesperrt.iterrows()):
            _gesperrt_zeile(g, i)

    st.markdown("")
    st.markdown("---")

    # ── Zu viele Check-ins ↔ Offene Fälle zuordnen ──────────────────────
    st.markdown("##### Zu viele Check-ins ↔ Offene Fälle")
    st.caption("Links die Check-ins ohne passende Buchung, rechts die "
               "offenen Fälle daneben — zum Vergleichen und Zuordnen, "
               "über alle Tage statt immer nur einen.")

    ueber_roh = alle_checkins_ohne_buchung()
    tage_alle = verfuegbare_tage()
    offen_roh = alle_offenen_fehler(tage_alle) if tage_alle else pd.DataFrame()

    if ueber_roh.empty and offen_roh.empty:
        box("✅ Keine überzähligen Check-ins und keine offenen Fälle.", "ok")
    else:
        links, rechts = st.columns([3, 2], gap="medium")

        # Zuordnungsziele: alle aktuell offenen Fälle, über alle Tage
        ziel_daten = []
        for _, f in offen_roh.iterrows():
            label = f"{f['Name']}  ·  {datum_kurz(str(f['Datum']))}"
            ziel_daten.append((label, str(f["Name_norm"]), str(f["Datum"]),
                               email_fuer(str(f["Name"]))))

        def _erlaubte_ziele(ci_datum: str, ci_norm: str) -> list:
            """
            Welche offenen Fälle darf dieser Check-in überhaupt schliessen?

            Eine Nachholung läuft nur in eine Richtung: Der Check-in
            kommt NACH dem Spieltag, den er erklärt. Vorher verglich
            diese Ansicht ausschliesslich Namen — ein Check-in vom
            17.07. wurde dadurch als Nachholung für einen Fall vom
            16.08. angeboten, also für ein Spiel, das zu dem Zeitpunkt
            noch gar nicht stattgefunden hatte.

            Ausserdem gilt hier dasselbe wie überall sonst: Wer am Tag
            des Check-ins selbst mit Rabatt gespielt hat, braucht ihn
            für sich — EGYM vergütet pro Person und Tag nur einmal.
            """
            if eigener_anspruch(ci_norm, ci_datum):
                return []
            ci_d = parse_date_safe(ci_datum)
            if ci_d is None:
                return []
            fenster = max(fenster_nachhol(),
                          int(einstellung("sperre_nachhol_fenster_tage",
                                          CONFIG["sperre_nachhol_fenster_tage"])))
            erlaubt = []
            for label, ziel_norm, ziel_datum, ziel_mail in ziel_daten:
                ziel_d = parse_date_safe(ziel_datum)
                if ziel_d is None:
                    continue
                abstand = (ci_d - ziel_d).days
                if 0 < abstand <= fenster:
                    erlaubt.append((label, ziel_norm, ziel_datum, ziel_mail))
            return erlaubt

        with rechts:
            st.markdown("**Offene Fälle**")
            if offen_roh.empty:
                box("✅ Keine offenen Fälle.", "ok")
            else:
                st.caption(f"{len(offen_roh)} offen")
                zeig = offen_roh[["Name", "Datum", "Service_Zeit"]].copy()
                zeig["Datum"] = zeig["Datum"].astype(str).map(datum_kurz)
                zeig.columns = ["Name", "Tag", "Zeit"]
                st.dataframe(zeig, use_container_width=True, hide_index=True,
                             height=min(560, 60 + 35 * len(zeig)))

        with links:
            st.markdown("**Zu viele Check-ins**")
            if ueber_roh.empty:
                box("✅ Keine überzähligen Check-ins.", "ok")
            else:
                st.caption(f"{len(ueber_roh)} überzählig")

                # Für jeden überzähligen Check-in den besten offenen Fall
                # vorschlagen — dieselbe Namens-/E-Mail-Ähnlichkeit wie in
                # der Tagesarbeit, nur über den gesamten offenen Bestand
                # statt nur ein Zeitfenster um einen Tag.
                ueber = ueber_roh.copy()
                raenge, beste = [], []
                for _, r in ueber.iterrows():
                    ci_norm = str(r["Name_norm"])
                    ci_name = str(r["Name"])
                    bester_label, bester = None, 0.0
                    for label, ziel_norm, _zd, ziel_mail in _erlaubte_ziele(
                            str(r["analysis_date"]), ci_norm):
                        sc = fuzz.token_set_ratio(ziel_norm, ci_norm)
                        if ziel_mail:
                            sc = max(sc, email_aehnlichkeit(ziel_mail, ci_name))
                        if sc >= bester:
                            bester_label, bester = label, sc
                    raenge.append(bester)
                    beste.append(bester_label)
                ueber["_rang"] = raenge
                ueber["_bester"] = beste
                ueber = ueber.sort_values("_rang", ascending=False)

                nur_passend = False
                if ziel_daten and len(ueber) > 12:
                    nur_passend = st.toggle("Nur passende zeigen", value=True,
                                            key="ueb_nur_passend")
                anzeige = (ueber[ueber["_rang"] >= 70]
                          if nur_passend else ueber)
                if anzeige.empty:
                    box("Keine passenden Check-ins gefunden.", "info")
                if len(anzeige) > 40:
                    st.caption(f"Zeige die 40 relevantesten von "
                               f"{len(anzeige)}.")

                for i, (_, r) in enumerate(anzeige.head(40).iterrows()):
                    ci_datum = str(r["analysis_date"])
                    ci_name = str(r["Name"])
                    ci_norm = str(r["Name_norm"])
                    ci_zeit = str(r.get("Checkin_Zeit", "")).strip()

                    st.markdown(f"**{ci_name}** · {datum_kurz(ci_datum)}"
                               + (f" · {ci_zeit}" if ci_zeit else ""))
                    erklaerung = checkin_erklaerung(ci_norm, ci_datum)
                    if erklaerung.get("text"):
                        st.caption(f"↳ {erklaerung['text']}")

                    moeglich = _erlaubte_ziele(ci_datum, ci_norm)
                    if not moeglich:
                        st.caption("↳ Kein Fall zuordenbar — entweder hat er "
                                   "an diesem Tag selbst mit Rabatt gespielt, "
                                   "oder es gibt keinen offenen Fall davor.")
                        st.markdown("")
                        continue

                    warnung = nachhol_warnung(ci_norm, ci_datum)
                    if warnung:
                        box(warnung, "warn")

                    bester_label = r.get("_bester")
                    bester_score = float(r.get("_rang", 0))
                    if bester_label and bester_score >= 80:
                        ziel_norm, ziel_datum = next(
                            (zn, zd) for lbl, zn, zd, _m in moeglich
                            if lbl == bester_label)
                        if st.button(f"✓ Nachholung für {bester_label} "
                                    f"({bester_score:.0f}%)",
                                    key=f"ueb_q_{i}", type="primary",
                                    use_container_width=True):
                            if nachholung_speichern(ci_datum, ci_norm,
                                                    ziel_datum, ziel_norm):
                                st.toast("Zugeordnet.")
                                st.rerun()

                    if moeglich:
                        with st.expander("Anderem Fall zuordnen"):
                            optionen = ["—"] + [lbl for lbl, *_r in moeglich]
                            wahl = st.selectbox(
                                "Fall", optionen, key=f"ueb_sel_{i}",
                                label_visibility="collapsed")
                            if wahl != "—" and st.button(
                                    "Zuordnen", key=f"ueb_zu_{i}",
                                    use_container_width=True):
                                ziel_norm, ziel_datum = next(
                                    (zn, zd) for lbl, zn, zd, _m in moeglich
                                    if lbl == wahl)
                                if nachholung_speichern(ci_datum, ci_norm,
                                                        ziel_datum, ziel_norm):
                                    st.toast("Zugeordnet.")
                                    st.rerun()
                    st.markdown("")


def _ev_wirkung_block(zeile):
    """Die Wirkung eines Events — vorher, nachher, Kontrollgruppe."""
    w = event_wirkung(str(zeile["Datum"]), str(zeile["Event_Id"]))
    if not w:
        box("Keine Wirkungsdaten für dieses Event.", "info")
        return

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Teilnehmer", str(w["teilnehmer"]))
    with k2:
        kpi("ohne früheren Besuch", str(w["ohne_vorbesuch"]),
            f"in den {w['vorlauf_tage']} Tagen davor")
    with k3:
        kpi("davon wiedergekommen", str(w["ohne_vorbesuch_wieder"]),
            prozent_text(w["ohne_vorbesuch_wieder"], w["ohne_vorbesuch"]))
    with k4:
        kpi("Kontrollgruppe", str(w["kontrollgruppe"]),
            "aktiv im Monat davor, nicht dabei")

    st.markdown("")
    st.markdown("**Wiederkehr im Vergleich**")
    box("Die mittlere Spalte allein sagt nichts. Wenn ohnehin die Hälfte "
        "innerhalb einer Woche wiederkommt, sind 50 % nach dem Event kein "
        "Erfolg. Erst der Abstand zur Kontrollgruppe zeigt, ob das Event "
        "etwas bewegt hat.", "info")

    zeilen = []
    for n, d in w["fenster"].items():
        if not d["vollstaendig"]:
            zeilen.append({
                "Zeitfenster": f"{n} Tage",
                "vorher schon da": f"{d['vorher']} ({d['vorher_quote']:.0f} %)",
                "danach wieder da": "— noch offen —",
                "Kontrollgruppe": "—",
                "Unterschied": "—",
            })
            continue
        diff = d["nachher_quote"] - d["kontrolle_quote"]
        zeilen.append({
            "Zeitfenster": f"{n} Tage",
            "vorher schon da": f"{d['vorher']} ({d['vorher_quote']:.0f} %)",
            "danach wieder da": f"{d['nachher']} ({d['nachher_quote']:.0f} %)",
            "Kontrollgruppe": f"{d['kontrolle_quote']:.0f} %",
            "Unterschied": f"{diff:+.0f} Pp",
        })
    st.dataframe(pd.DataFrame(zeilen), use_container_width=True,
                 hide_index=True)

    if w.get("vorlauf_tage", 0) < 60:
        box(f"ℹ️ Vor dem Event liegen nur <b>{w['vorlauf_tage']} Tage</b> an "
            "Daten. „Ohne früheren Besuch\u201c heisst deshalb nicht "
            "zwangsläufig „neuer Gast\u201c — wer länger pausiert hatte, "
            "sieht hier genauso aus. Mit mehr geladenen Monaten wird die "
            "Zahl belastbar.", "info")

    unvollstaendig = [str(n) for n, d in w["fenster"].items()
                      if not d["vollstaendig"]]
    if unvollstaendig:
        stand = w.get("datenstand")
        box(f"⏳ Die Fenster über <b>{', '.join(unvollstaendig)} Tage</b> sind "
            f"noch nicht abgelaufen — die Daten reichen bis "
            f"{datum_kurz(str(stand)) if stand else 'unbekannt'}. Statt einer "
            "falschen Null steht dort nichts.", "warn")


def _ev_teilnehmer_block(zeile):
    """Die einzelnen Menschen hinter der Quote."""
    det = event_teilnehmer_details(str(zeile["Datum"]), str(zeile["Event_Id"]))
    if det.empty:
        box("Keine Teilnehmerdaten.", "info")
        return

    verteilung = det["Status"].value_counts().to_dict()
    spalten = st.columns(4)
    for col, status in zip(spalten, ["Ohne Vorbesuch · wiedergekommen",
                                     "Ohne Vorbesuch · noch nicht wieder",
                                     "Stammgast · wiedergekommen",
                                     "Stammgast · noch nicht wieder"]):
        with col:
            kpi(status.replace(" · ", "\n"), str(verteilung.get(status, 0)))

    st.markdown("")
    zeig = det.copy()
    zeig["Letzter Besuch davor"] = zeig["Letzter Besuch davor"].map(
        lambda x: datum_kurz(x) if x != "—" else "—")
    zeig["Wieder da am"] = zeig["Wieder da am"].map(
        lambda x: datum_kurz(x) if x != "—" else "—")
    zeig["Bezahlt"] = zeig["Bezahlt"].map(euro)
    st.dataframe(zeig, use_container_width=True, hide_index=True,
                 height=min(600, 60 + 35 * len(zeig)))
    st.download_button(
        "⬇️ Teilnehmer als CSV",
        data=zeig.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"event_{zeile['Datum']}.csv", mime="text/csv",
        use_container_width=True)


def modul_events():
    head("Events", "Was eine Veranstaltung wirklich gebracht hat")

    events = event_liste()
    if events.empty:
        box("Noch kein Event in den Daten. Ein Event erkennt die App an "
            "Playtomics Kennzeichnung (<code>OPEN_PLAY</code> mit "
            "Aktivitäts-Kennung) — lade einen Tag mit Veranstaltung hoch.",
            "info")
        return

    t1, t2 = st.tabs(["🗓 Einzelnes Event", "📈 Wiederkehr allgemein"])

    with t1:
        labels = [f"{datum_kurz(str(r['Datum']))} · {r['Name']} "
                  f"({r['Teilnehmer']} Teilnehmer)"
                  for _, r in events.iterrows()]
        wahl = st.selectbox("Event", labels, key="ev_wahl")
        zeile = events.iloc[labels.index(wahl)]

        if str(zeile.get("Unklar", "")) == "Ja":
            box("⚠️ Bei diesem Event haben alle denselben Betrag gezahlt. "
                "Ohne Vollzahler als Vergleich lässt sich nicht sagen, wer "
                "Wellpass genutzt hat — die Wellpass-Zahl unten ist deshalb "
                "nicht belastbar.", "warn")

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi("Umsatz", euro(float(zeile["Umsatz"])))
        with k2:
            kpi("Wellpass", str(int(zeile["Wellpass"])),
                prozent_text(int(zeile["Wellpass"]), int(zeile["Teilnehmer"])))
        with k3:
            kpi("Court-Stunden", f"{zeile['Court-Stunden']:.1f}",
                f"{int(zeile['Courts'])} Courts belegt")
        with k4:
            kpi("Offene Fälle", str(int(zeile["Offene Fälle"])),
                "fehlende Check-ins")

        st.markdown("")
        st.markdown("---")
        _ev_wirkung_block(zeile)
        st.markdown("")
        st.markdown("---")
        st.markdown("##### Teilnehmer im Einzelnen")
        _ev_teilnehmer_block(zeile)

        if len(events) > 1:
            st.markdown("")
            st.markdown("---")
            st.markdown("##### Alle Events im Vergleich")
            st.dataframe(events.drop(columns=["Event_Id", "Unklar"]),
                         use_container_width=True, hide_index=True)

    with t2:
        st.markdown("##### Kommen Neukunden wieder?")
        box("Von allen Spielern, die in einer Woche zum ersten Mal da waren: "
            "wie viele kamen innerhalb einer, zwei und vier Wochen wieder? "
            "Eine einzelne Quote sagt wenig — die Reihe zeigt, ob es besser "
            "wird. Wochen, deren Fenster noch läuft, bleiben leer.", "info")
        kurve = wiederkehr_kurve()
        if kurve.empty:
            box("Noch zu wenig Verlauf für eine Kohortenauswertung.", "info")
        else:
            st.dataframe(kurve, use_container_width=True, hide_index=True)

        st.markdown("")
        st.markdown("---")
        st.markdown("##### Neue Spieler je Woche")
        neu = neukunden_je_woche()
        if neu.empty:
            box("Noch keine Neukundendaten.", "info")
        else:
            st.dataframe(neu, use_container_width=True, hide_index=True,
                         height=min(420, 60 + 35 * len(neu)))
            st.caption("Erster Besuch innerhalb des ausgewerteten Zeitraums. "
                       "Wer schon am ersten Datentag da war, zählt nicht als "
                       "neu — sein echter Erstbesuch liegt davor.")


def modul_whatsapp():
    head("WhatsApp Reminder", "Tag für Tag abarbeiten")

    if not twilio_bereit():
        box("Twilio ist noch nicht eingerichtet — es wird nichts versendet. "
            "Die Nachrichten kannst du trotzdem sehen und kopieren.", "warn")
    if not QR_LINK:
        box("Der Wellpass-QR-Link fehlt — die Nachrichten gehen ohne QR raus.",
            "info")

    t1, t2, t3, t4, t5 = st.tabs(["📅 Tagesarbeit", "🔍 Zuordnung prüfen",
                                  "✅ Erledigt", "📊 Übersicht", "📜 Protokoll"])

    with t1:
        _wa_tagesarbeit()

    with t2:
        _wa_pruefen()

    # ── Erledigte Fälle ─────────────────────────────────────────────────
    with t3:
        box("Alle Fälle, die du als erledigt markiert oder zugeordnet hast. "
            "Versehentlich geklickt? Mit einem Klick wieder öffnen.", "info")

        erledigt = erledigte_faelle()
        if erledigt.empty:
            box("Noch nichts als erledigt markiert.", "info")
        else:
            st.caption(f"{len(erledigt)} erledigte Fälle · neueste zuerst")
            for i, (_, r) in enumerate(erledigt.head(60).iterrows()):
                e1, e2, e3 = st.columns([2.4, 1.4, 1.2])
                with e1:
                    info = grund_info(r.get("grund", ""))
                    label = f"{info['icon']} {info['kurz']}"
                    st.markdown(f"**{r['Name']}**  {chip(label, 'soft')}",
                                unsafe_allow_html=True)
                    # Bei Nachholungen zeigen, welcher Check-in den Fall
                    # geschlossen hat — damit nachvollziehbar bleibt,
                    # dass jeder Check-in nur einmal verwendet wurde.
                    if str(r.get("grund", "")) == "nachgeholt":
                        quelle = nachholung_quelle(str(r["name_norm"]),
                                                   str(r["datum"]))
                        if quelle:
                            st.caption(f"↳ Check-in vom "
                                       f"{datum_kurz(quelle['checkin_datum'])} "
                                       f"({quelle['checkin_name']})")
                with e2:
                    wann = (r["_ts"].strftime("%d.%m. %H:%M")
                            if pd.notna(r.get("_ts")) else "")
                    st.caption(f"Spieltag {datum_kurz(r['datum'])}"
                               + (f" · erledigt {wann}" if wann else ""))
                with e3:
                    if st.button("Wieder öffnen", key=f"wa_undo_{i}",
                                 use_container_width=True):
                        behebung_zuruecknehmen(str(r["name_norm"]),
                                               str(r["datum"]))
                        st.toast("Fall ist wieder offen.")
                        st.rerun()

    # ── Übersicht ───────────────────────────────────────────────────────
    with t4:
        _wa_uebersicht()

    # ── Protokoll ───────────────────────────────────────────────────────
    with t5:
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
        spalten = [c for c in ["name", "datum", "art", "timestamp"]
                   if c in log.columns]
        zeig = log[spalten].head(150).copy()
        zeig.columns = [{"name": "Spieler", "datum": "Spieltag",
                         "art": "Art", "timestamp": "Gesendet"}.get(c, c)
                        for c in spalten]
        st.dataframe(zeig, use_container_width=True, hide_index=True, height=420)



# ══════════════════════════════════════════════════════════════════════════════
#   🔄  NACHHOLUNGEN  —  Check-ins, die einen älteren Fall auflösen
# ══════════════════════════════════════════════════════════════════════════════

def checkin_schluessel(datum: str, name_norm: str) -> str:
    return f"{datum}|{name_norm}"


@st.cache_data(ttl=600, show_spinner=False)
def verbrauchte_checkins() -> dict:
    """
    Check-ins, die bereits einem älteren Fall zugeordnet wurden.
    → {checkin_schluessel: fall_schluessel}
    """
    df = loadsheet("checkin_zuordnung", SHEET_SPALTEN["checkin_zuordnung"])
    if df.empty or "checkin_key" not in df.columns:
        return {}
    return dict(zip(df["checkin_key"].astype(str),
                    df["fall_key"].astype(str)))


def nachholung_speichern(checkin_datum: str, checkin_name: str,
                         fall_datum: str, fall_name: str) -> bool:
    """
    Einen Check-in als Nachholung für einen älteren Fall festhalten.

    Damit gilt der Fall als geklärt und der Check-in ist verbraucht —
    er taucht nicht mehr als überzählig auf.

    Ein Check-in kann genau einen Fall schliessen. EGYM vergütet pro
    Person und Tag einmal, also gibt es auch nur einmal Geld. Ist der
    Check-in schon vergeben, wird hier abgelehnt statt still die alte
    Zuordnung zu überschreiben — sonst blieben beide Fälle geschlossen,
    obwohl nur einer bezahlt wurde.

    → True, wenn gespeichert wurde
    """
    ck = checkin_schluessel(checkin_datum, checkin_name)
    fk = checkin_schluessel(fall_datum, fall_name)

    schon_vergeben = verbrauchte_checkins().get(ck)
    if schon_vergeben and schon_vergeben != fk:
        alt_datum = schon_vergeben.split("|")[0]
        st.error(f"❌ Dieser Check-in vom {datum_kurz(checkin_datum)} ist "
                 f"bereits dem Fall vom {datum_kurz(alt_datum)} zugeordnet. "
                 "Ein Check-in kann nur einen Fall schliessen — EGYM zahlt "
                 "pro Person und Tag nur einmal.")
        return False

    sheet_zeile_setzen("checkin_zuordnung", {
        "checkin_key": ck,
        "fall_key": fk,
        "checkin_datum": checkin_datum,
        "checkin_name": checkin_name,
        "fall_datum": fall_datum,
        "fall_name": fall_name,
        "timestamp": datetime.now().isoformat(),
    }, schluessel_spalte="checkin_key")
    # Ein zugeordneter Check-in ist immer eine Nachholung — EGYM vergütet.
    als_behoben_markieren(fall_name, fall_datum, grund="nachgeholt")
    cache_leeren("checkin_zuordnung", "corrections",
                 funktionen=("offene_fehler", "offene_je_tag",
                             "verbrauchte_checkins", "offene_checkins",
                             "offene_checkins_zeitraum", "zuordnung_vorschlag",
                             "nachhol_kandidaten", "nachholung_quelle",
                             "anspruch_bilanz", "eigener_anspruch",
                             "anspruch_verdacht"))
    return True


@st.cache_data(ttl=600, show_spinner=False)
def nachholung_quelle(fall_name: str, fall_datum: str) -> dict:
    """Welcher Check-in hat diesen Fall geschlossen?"""
    df = loadsheet("checkin_zuordnung", SHEET_SPALTEN["checkin_zuordnung"])
    if df.empty or "fall_key" not in df.columns:
        return {}
    fk = checkin_schluessel(fall_datum, fall_name)
    treffer = df[df["fall_key"].astype(str) == fk]
    if treffer.empty:
        return {}
    z = treffer.iloc[0]
    return {"checkin_datum": str(z["checkin_datum"]),
            "checkin_name": str(z["checkin_name"])}


def nachholung_loesen(checkin_datum: str, checkin_name: str):
    """Eine Zuordnung wieder aufheben."""
    df = loadsheet("checkin_zuordnung", SHEET_SPALTEN["checkin_zuordnung"])
    if df.empty or "checkin_key" not in df.columns:
        return
    ck = checkin_schluessel(checkin_datum, checkin_name)
    treffer = df[df["checkin_key"].astype(str) == ck]
    df = df[df["checkin_key"].astype(str) != ck]
    savesheet(df, "checkin_zuordnung")
    # Zugehörigen Fall wieder öffnen
    if not treffer.empty:
        behebung_zuruecknehmen(str(treffer.iloc[0]["fall_name"]),
                               str(treffer.iloc[0]["fall_datum"]))
    cache_leeren("checkin_zuordnung", "corrections",
                 funktionen=("offene_fehler", "offene_je_tag",
                             "verbrauchte_checkins", "offene_checkins",
                             "offene_checkins_zeitraum", "zuordnung_vorschlag",
                             "nachhol_kandidaten", "nachholung_quelle"))


@st.cache_data(ttl=600, show_spinner=False)
def offene_checkins_zeitraum(von: date, bis: date) -> pd.DataFrame:
    """
    Alle Check-ins in einem Zeitraum, die keiner Buchung zugeordnet
    werden konnten und noch nicht als Nachholung verbraucht sind.
    """
    c = loadsheet("checkins")
    if c.empty or "analysis_date" not in c.columns:
        return pd.DataFrame()

    df = c.copy()
    df["_d"] = df["analysis_date"].map(parse_date_safe)
    df = df[df["_d"].notna()]
    df = df[(df["_d"] >= von) & (df["_d"] <= bis)]
    if df.empty or "Gespielt" not in df.columns:
        return pd.DataFrame()

    df = df[df["Gespielt"].astype(str) == "Nein"].copy()
    if df.empty:
        return df

    verbraucht = verbrauchte_checkins()
    if verbraucht:
        df["_key"] = df.apply(
            lambda r: checkin_schluessel(str(r["analysis_date"]),
                                         str(r["Name_norm"])), axis=1)
        df = df[~df["_key"].isin(verbraucht.keys())]

    belegt = mapping_belegte_checkins()
    if belegt and not df.empty:
        df = df[~df.apply(
            lambda r: str(r["Name_norm"]) in belegt.get(
                str(r["analysis_date"]), set()), axis=1)]

    return df.drop_duplicates(subset=["analysis_date", "Name_norm"])


@st.cache_data(ttl=600, show_spinner=False)
def nachhol_kandidaten(name: str, fall_datum: str,
                       fenster: int = None) -> list:
    """
    Hat diese Person nach dem Spieltag noch eingecheckt?

    Sucht in den Tagen nach dem Spiel nach unzugeordneten Check-ins,
    die zu diesem Namen passen. Genau das passiert, wenn jemand auf
    deine WhatsApp reagiert und den Check-in nachholt.

    → [(anzeigename, name_norm, checkin_datum, score, tage_danach), …]
    """
    fenster = fenster or fenster_nachhol()
    start = parse_date_safe(fall_datum)
    if start is None:
        return []

    offen = offene_checkins_zeitraum(start, start + timedelta(days=fenster))
    if offen.empty:
        return []

    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()
    ziel = normalize_name(name)
    mail = email_fuer(name)

    treffer = []
    for _, r in offen.iterrows():
        kand = str(r["Name_norm"])
        anzeige = str(r["Name"])
        ci_datum = str(r["analysis_date"])

        if (ziel, kand) in abgelehnt:
            continue

        # Am Spieltag selbst wäre es kein Nachholen, sondern eine
        # Namensvariante — die läuft über die normale Zuordnung.
        ci_d = parse_date_safe(ci_datum)
        tage_danach = (ci_d - start).days if ci_d else 0

        # Hat derjenige am Tag des Check-ins selbst mit Rabatt gespielt?
        # Dann braucht er den Check-in für sich — EGYM vergütet pro
        # Person und Tag nur einmal.
        if eigener_anspruch(kand, ci_datum):
            continue

        score = 0.0
        if ziel == kand:
            score = 100.0
        else:
            fm = fuzzy_match(ziel, [kand], mapping, abgelehnt)
            if fm:
                score = fm[0][1]
            if mail:
                score = max(score, email_aehnlichkeit(mail, anzeige))

        # Eine Nachholung hat Geldwirkung — hier zählt mehr als ein
        # hoher Punktwert.
        #
        # Entweder der Name stimmt praktisch überein (ab 88 %), oder der
        # Nachname passt eindeutig und der Gesamtwert ist solide. Das
        # zweite Kriterium fängt Fälle wie eine Kurzform des Vornamens
        # bei gleichem Nachnamen — die landen bei gut 80 % und wären
        # sonst durchgefallen. Namenspaare mit bloss ähnlichen
        # Anfangsbuchstaben bleiben trotzdem draussen, weil dort der
        # Nachname nicht passt.
        such_vor, such_nach = _namensteile(ziel)
        kand_vor, kand_nach = _namensteile(kand)
        # Nachname muss eindeutig passen — und der Vorname wenigstens
        # erkennbar. Sonst würden zwei verschiedene Menschen mit
        # gleichem Nachnamen zusammengeworfen.
        passt = (bool(such_nach) and bool(kand_nach)
                 and _teil_aehnlich(such_nach, kand_nach) >= 85
                 and _teil_aehnlich(such_vor, kand_vor) >= 55)

        if score >= 88 or (passt and score >= 70):
            treffer.append((anzeige, kand, ci_datum, round(score, 1),
                            tage_danach))

    return sorted(treffer, key=lambda x: (-x[3], x[4]))


def faelle_mit_nachricht(tage: list) -> pd.DataFrame:
    """
    Offene Fälle, bei denen bereits eine WhatsApp rausging.
    Ergänzt um Versandzeitpunkt und verstrichene Tage.
    """
    offen = alle_offenen_fehler(tage)
    if offen.empty:
        return offen

    log = loadsheet("whatsapp_log", SHEET_SPALTEN["whatsapp_log"])
    if log.empty or "key" not in log.columns:
        offen["_gesendet"] = pd.NaT
        offen["_tage_seit"] = -1
        return offen

    zeitpunkt = {}
    for _, l in log.iterrows():
        try:
            zeitpunkt[str(l["key"])] = datetime.fromisoformat(str(l["timestamp"]))
        except (ValueError, TypeError):
            continue

    def suchen(r):
        return zeitpunkt.get(wa_key(str(r["Name_norm"]), str(r["Datum"]),
                                    r.get("Betrag", 0)))

    offen = offen.copy()
    offen["_gesendet"] = offen.apply(suchen, axis=1)
    offen["_tage_seit"] = offen["_gesendet"].map(
        lambda t: (datetime.now() - t).days if pd.notna(t) else -1)
    return offen


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

@st.cache_data(ttl=900, show_spinner=False)
def playtomic_spieler() -> dict:
    """
    Alle Namen, die in Playtomic als Spieler auftauchen.

    Das ist ein starkes Signal für die Namenszuordnung: Taucht ein
    Check-in-Name in Playtomic überhaupt nicht auf, ist er fast sicher
    nur die EGYM-Schreibweise einer bekannten Person. Hat er dagegen
    eigene Buchungen, ist er ein eigenständiger Mensch — dann wäre die
    Zuordnung falsch.

    → {name_norm: Anzahl Spieltage}
    """
    b = loadsheet("buchungen")
    if b.empty or "Name_norm" not in b.columns or "analysis_date" not in b.columns:
        return {}
    return (b.groupby(b["Name_norm"].astype(str))["analysis_date"]
            .nunique().astype(int).to_dict())


@st.cache_data(ttl=900, show_spinner=False)
def spieltage_von(name_norm: str) -> set:
    """An welchen Tagen hat dieser Name in Playtomic gespielt?"""
    b = loadsheet("buchungen")
    if b.empty or "Name_norm" not in b.columns:
        return set()
    treffer = b[b["Name_norm"].astype(str) == str(name_norm)]
    if treffer.empty:
        return set()
    return set(treffer["analysis_date"].astype(str))


@st.cache_data(ttl=900, show_spinner=False)
def mapping_konflikte() -> list:
    """
    Verknüpfungen, die nicht mehr stimmen können.

    Spielen beide Namen am selben Tag eigenständig in Playtomic, sind
    es zwei verschiedene Menschen — dann wurde die Zuordnung damals
    falsch bestätigt und verfälscht seitdem jede Auswertung.

    → [{buchung, checkin, art, hinweis, tage}, …]
    """
    mapping = mapping_laden()
    if not mapping:
        return []

    konflikte = []
    for buchung_name, ziel in mapping.items():
        checkin_name = str(ziel["checkin_name"] if isinstance(ziel, dict)
                           else ziel)
        tage_b = spieltage_von(str(buchung_name))
        tage_c = spieltage_von(checkin_name)

        if not tage_c:
            continue    # Name existiert nur bei EGYM — alles in Ordnung

        gemeinsam = sorted(tage_b & tage_c, reverse=True)
        if gemeinsam:
            konflikte.append({
                "buchung": str(buchung_name), "checkin": checkin_name,
                "art": "hart", "tage": gemeinsam,
                "hinweis": (f"Beide haben am {datum_kurz(gemeinsam[0])} "
                            "gespielt — das können nicht dieselben sein."),
            })
        else:
            konflikte.append({
                "buchung": str(buchung_name), "checkin": checkin_name,
                "art": "weich", "tage": sorted(tage_c, reverse=True),
                "hinweis": (f"„{checkin_name}“ hat {len(tage_c)} eigene "
                            "Spieltage in Playtomic — prüfen."),
            })

    return sorted(konflikte, key=lambda k: (k["art"] != "hart",
                                            -len(k["tage"])))


def modul_matching():
    head("Name-Abgleich", "Playtomic ↔ Wellpass zusammenführen")

    box("Playtomic und EGYM schreiben Namen oft unterschiedlich — "
        "„M. Sidorov“ hier, „Marcel Sidorov“ dort. Dann meldet die App fälschlich "
        "einen fehlenden Check-in. Hier bestätigst du die Zuordnung einmal, "
        "danach erkennt die App sie automatisch.", "info")

    mapping = mapping_laden()
    abgelehnt = rejected_matches_laden()
    konflikte = mapping_konflikte()

    titel_konflikt = ("⚠️ Konflikte" + (f"  ·  {len(konflikte)}" if konflikte
                                        else ""))
    t1, t2, t3 = st.tabs(["🔍 Vorschläge", "📚 Gelernte Zuordnungen",
                          titel_konflikt])

    # ── Vorschläge ──────────────────────────────────────────────────────
    # Eigene Funktion, weil hier mehrfach früh abgebrochen wird. Vorher
    # stand hier ein return mitten im Tab — das hat die anderen Tabs
    # gleich mit beendet, sie blieben leer.
    def _vorschlaege_tab():
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
                        eigene = playtomic_spieler().get(best, 0)
                        vorschlaege.append({
                            "buchung": str(r["Name"]),
                            "buchung_norm": str(r["Name_norm"]),
                            "checkin": namen_anzeige.get(best, best),
                            "checkin_norm": best,
                            "score": score, "tag": tag,
                            "eigene_tage": eigene,
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

            eigene = v.get("eigene_tage", 0)
            if eigene:
                box(f"⚠️ „{v['checkin']}“ hat <b>{eigene} eigene Spieltage</b> "
                    "in Playtomic — also einen eigenen Account. Das spricht "
                    "stark dagegen, dass es dieselbe Person ist.", "warn")
            else:
                box(f"„{v['checkin']}“ kommt in Playtomic nicht vor — der "
                    "Name existiert nur bei EGYM. Das spricht dafür, dass es "
                    "dieselbe Person ist.", "ok")

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("✓ Ist dieselbe Person", key=f"mm_ok_{i}",
                             type="secondary" if eigene else "primary",
                             use_container_width=True):
                    mapping_hinzufuegen(v["buchung_norm"], v["checkin_norm"],
                                        v["score"])
                    cache_leeren()
                    st.toast("Gemerkt.")
                    st.rerun()
            with c2:
                if st.button("✗ Nicht dieselbe", key=f"mm_no_{i}",
                             use_container_width=True):
                    rejected_speichern(v["buchung_norm"], v["checkin_norm"])
                    st.rerun()
            with c3:
                st.caption(f"Spieltag {datum_kurz(v['tag'])}")

        box("Bestätigte Zuordnungen greifen sofort — auch rückwirkend auf "
            "bereits verarbeitete Tage. Ein erneuter Import ist nicht nötig.",
            "info")

    with t1:
        _vorschlaege_tab()

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

    # ── Konflikte ───────────────────────────────────────────────────────
    with t3:
        box("Eine Verknüpfung kann sich im Nachhinein als falsch "
            "herausstellen — nämlich dann, wenn der Wellpass-Name plötzlich "
            "eigene Buchungen in Playtomic hat. Spielen beide am selben Tag, "
            "sind es zwei verschiedene Menschen und die Zuordnung verfälscht "
            "seitdem jede Auswertung.", "info")

        if not konflikte:
            box("✅ Keine widersprüchlichen Verknüpfungen. Alle "
                "Wellpass-Namen existieren nur bei EGYM.", "ok")
        else:
            hart = [k for k in konflikte if k["art"] == "hart"]
            weich = [k for k in konflikte if k["art"] == "weich"]

            if hart:
                box(f"❌ <b>{len(hart)} sichere Fehlverknüpfungen.</b> "
                    "Beide Namen haben am selben Tag gespielt.", "warn")
            if weich:
                box(f"👀 <b>{len(weich)} zu prüfen.</b> Der Wellpass-Name hat "
                    "eigene Spieltage, aber nie am selben Tag.", "info")

            for i, k in enumerate(konflikte):
                farbe = C["err"] if k["art"] == "hart" else C["warn"]
                st.markdown(f"""
                <div class="pc-card" style="border-left:3px solid {farbe};">
                  <div style="display:flex;justify-content:space-between;
                              align-items:center;">
                    <div>
                      <span style="color:{C['dim']};font-size:.78rem;">
                        Playtomic</span><br>
                      <span style="font-weight:600;color:{C['text']};">
                        {k['buchung']}</span>
                    </div>
                    <div style="font-size:1.3rem;color:{farbe};">↮</div>
                    <div style="text-align:right;">
                      <span style="color:{C['dim']};font-size:.78rem;">
                        Wellpass</span><br>
                      <span style="font-weight:600;color:{C['text']};">
                        {k['checkin']}</span>
                    </div>
                  </div>
                  <div style="margin-top:.6rem;color:{C['dim']};
                              font-size:.82rem;">{k['hinweis']}</div>
                </div>""", unsafe_allow_html=True)

                k1, k2 = st.columns([1, 2])
                with k1:
                    if st.button("Verknüpfung lösen", key=f"mk_del_{i}",
                                 type="primary" if k["art"] == "hart"
                                 else "secondary",
                                 use_container_width=True):
                        mapping_entfernen(k["buchung"])
                        rejected_speichern(k["buchung"], k["checkin"])
                        st.toast("Verknüpfung gelöst.")
                        st.rerun()
                with k2:
                    st.caption("Spieltage: " + ", ".join(
                        datum_kurz(t) for t in k["tage"][:6])
                        + (" …" if len(k["tage"]) > 6 else ""))
                st.markdown("")

            box("Nach dem Lösen die betroffenen Tage in der Daten-Zentrale "
                "neu verarbeiten, damit die Auswertung wieder stimmt.", "info")


# ══════════════════════════════════════════════════════════════════════════════
#   ⚙️  MODUL · EINSTELLUNGEN
# ══════════════════════════════════════════════════════════════════════════════

def modul_einstellungen():
    head("Einstellungen", "Ziele · Konfiguration · System")

    t1, t2, t3, t4 = st.tabs(["🎯 Ziele", "⚡ Zuordnung", "🔍 Suche",
                              "🩺 System"])

    # ── Automatische Zuordnung ──────────────────────────────────────────
    with t2:
        st.markdown("##### Sichere Zuordnungen automatisch übernehmen")
        st.caption("Ist eine Namenszuordnung eindeutig, muss sie dir nicht "
                   "einzeln vorgelegt werden. Betrifft nur Zuordnungen am "
                   "Spieltag selbst — reine Schreibweisen-Unterschiede, bei "
                   "denen der Check-in vorliegt und von EGYM bezahlt ist. "
                   "Nachholungen an Folgetagen bleiben immer bei dir.")

        an = st.toggle("Automatisch vorschlagen",
                       value=bool(einstellung("auto_zuordnung_an", True)),
                       key="auto_an")

        wert = st.slider(
            "Ab welcher Sicherheit?", min_value=85, max_value=100,
            value=int(einstellung("auto_schwelle", AUTO_SCHWELLE_STANDARD)),
            step=1, key="auto_schwelle_regler",
            help="Zusätzlich muss der beste Vorschlag mindestens "
                 f"{AUTO_ABSTAND:.0f} Punkte Vorsprung zum zweitbesten haben.")

        if st.button("Speichern", type="primary", key="auto_speichern"):
            einstellung_setzen("auto_zuordnung_an", bool(an))
            einstellung_setzen("auto_schwelle", float(wert))
            # Sitzungssperre lösen, damit die neue Schwelle sofort greift
            st.session_state["_auto_erledigt"] = set()
            st.session_state["_auto_protokoll"] = []
            cache_leeren()
            st.toast("Gespeichert.")
            st.rerun()

        st.markdown("---")
        st.markdown("##### EGYM-Vergütung")
        st.caption("Was EGYM pro Check-in zahlt. Ändert sich der Satz, wird "
                   "er ab dem angegebenen Tag verwendet — ältere Monate "
                   "rechnen weiter mit ihrem alten Satz, sonst wären "
                   "rückwirkend alle Zahlen falsch.")

        saetze = wellpass_saetze()
        st.dataframe(pd.DataFrame([{
            "Gültig ab": datum_kurz(x["ab"]) if x["ab"] > "2001" else "Beginn",
            "EGYM zahlt": euro(x["brutto"]),
            f"davon {CONFIG['wellpass_anteil']*100:.0f} % für dich":
                euro(round(x["brutto"] * CONFIG["wellpass_anteil"], 2)),
        } for x in saetze]), use_container_width=True, hide_index=True)

        st.caption(f"Aktuell gültig: {euro(wellpass_wert_am(date.today()))} "
                   "pro Check-in")

        with st.expander("Neuen Satz eintragen"):
            sp1, sp2 = st.columns(2)
            with sp1:
                ab = st.date_input("Gültig ab", value=date.today(),
                                   key="satz_ab", format="DD.MM.YYYY")
            with sp2:
                brutto = st.number_input("EGYM zahlt (brutto) in €",
                                         min_value=1.0, max_value=50.0,
                                         value=float(wellpass_brutto_am(
                                             date.today())),
                                         step=0.5, format="%.2f",
                                         key="satz_brutto")
            st.caption(f"Für dich: "
                       f"{euro(round(brutto * CONFIG['wellpass_anteil'], 2))} "
                       "pro Check-in")
            if st.button("Satz hinzufügen", type="primary", key="satz_neu"):
                neue = [x for x in saetze if x["ab"] != str(ab)]
                neue.append({"ab": str(ab), "brutto": float(brutto)})
                einstellung_setzen("wellpass_saetze",
                                   sorted(neue, key=lambda x: x["ab"]))
                cache_leeren()
                st.toast("Satz gespeichert.")
                st.rerun()

            if len(saetze) > 1:
                weg = st.selectbox("Satz entfernen",
                                   [x["ab"] for x in saetze[1:]],
                                   format_func=datum_kurz, key="satz_weg")
                if st.button("Entfernen", key="satz_loeschen"):
                    einstellung_setzen(
                        "wellpass_saetze",
                        [x for x in saetze if x["ab"] != weg])
                    cache_leeren()
                    st.toast("Entfernt.")
                    st.rerun()

        st.markdown("---")
        st.markdown("##### Wellpass-Abzug")
        st.caption("Was Playtomic pro Wellpass-Spieler vom Platzpreis "
                   "abzieht. Nicht zu verwechseln mit der EGYM-Vergütung. "
                   "Der Wert hat sich im Betrieb schon geändert.")

        pruef = abzug_pruefen()
        if pruef["geprueft"]:
            eigene = pruef["quoten"].get(pruef["eingestellt"], 0)
            beste = pruef["quoten"].get(pruef["bester"], 0)
            if pruef["bester"] != pruef["eingestellt"] and beste - eigene > 0.05:
                box(f"⚠️ <b>Der eingestellte Abzug passt nicht.</b><br>"
                    f"Mit {pruef['eingestellt']:.2f} € gehen "
                    f"{eigene*100:.0f} % der rabattierten Buchungen auf, "
                    f"mit <b>{pruef['bester']:.2f} €</b> dagegen "
                    f"{beste*100:.0f} %.<br><br>"
                    "Stimmt der Wert nicht, verschwinden Buchungen mit "
                    "mehreren Wellpass-Spielern lautlos aus der Kontrolle.",
                    "warn")
            else:
                box(f"✅ Der Abzug von {pruef['eingestellt']:.2f} € passt zu "
                    f"{eigene*100:.0f} % der {pruef['geprueft']} rabattierten "
                    "Buchungen.", "ok")

            with st.expander("Wie gut passen die Alternativen?"):
                st.dataframe(pd.DataFrame([
                    {"Abzug": f"{k:.2f} €",
                     "Buchungen gehen auf": f"{v*100:.0f} %",
                     "": "← eingestellt" if k == pruef["eingestellt"] else ""}
                    for k, v in sorted(pruef["quoten"].items())]),
                    use_container_width=True, hide_index=True)

        abzug_hist = wellpass_abzug_saetze()
        st.dataframe(pd.DataFrame([{
            "Gültig ab": datum_kurz(x["ab"]) if x["ab"] > "2001" else "Beginn",
            "Abzug je Spieler": euro(x["abzug"]),
        } for x in abzug_hist]), use_container_width=True, hide_index=True)

        box("Massgeblich ist der Tag der <b>Buchung</b>, nicht der Spieltag. "
            "Weil zwei Wochen im Voraus gebucht werden kann, laufen nach "
            "einer Umstellung noch wochenlang Buchungen mit dem alten "
            "Rabatt ein. Die App probiert deshalb zuerst den Wert des "
            "Spieltags und fällt sonst auf die anderen bekannten Werte "
            "zurück — beide Fälle werden erkannt.", "info")

        with st.expander("Neuen Abzug eintragen"):
            ap1, ap2 = st.columns(2)
            with ap1:
                a_ab = st.date_input("Gültig ab", value=date.today(),
                                     key="abzug_ab", format="DD.MM.YYYY")
            with ap2:
                a_wert = st.number_input(
                    "Abzug je Wellpass-Spieler in €", min_value=1.0,
                    max_value=30.0, value=float(wellpass_abzug()),
                    step=0.5, format="%.2f", key="abzug_wert")
            if st.button("Abzug hinzufügen", type="primary",
                         key="abzug_speichern"):
                neue = [x for x in abzug_hist if x["ab"] != str(a_ab)]
                neue.append({"ab": str(a_ab), "abzug": float(a_wert)})
                einstellung_setzen("wellpass_abzug_saetze",
                                   sorted(neue, key=lambda x: x["ab"]))
                cache_leeren()
                st.toast("Gespeichert. Betroffene Tage neu hochladen.")
                st.rerun()

            if len(abzug_hist) > 1:
                a_weg = st.selectbox("Eintrag entfernen",
                                     [x["ab"] for x in abzug_hist[1:]],
                                     format_func=datum_kurz, key="abzug_weg")
                if st.button("Entfernen", key="abzug_loeschen"):
                    einstellung_setzen(
                        "wellpass_abzug_saetze",
                        [x for x in abzug_hist if x["ab"] != a_weg])
                    cache_leeren()
                    st.toast("Entfernt.")
                    st.rerun()

        st.caption("Nach einer Änderung die betroffenen Tage neu hochladen — "
                   "die Rabatt-Erkennung steckt in den gespeicherten Zeilen.")

        st.markdown("---")
        st.markdown("##### Zeiträume für Nachholungen")
        st.caption("Wie lange nach dem Spieltag zählt ein Check-in noch als "
                   "Nachholung? Und wie weit zurück sollen überzählige "
                   "Check-ins in der Seitenspalte auftauchen?")

        nachhol = st.slider(
            "Nachholung möglich bis … Tage nach dem Spiel",
            min_value=1, max_value=60, value=fenster_nachhol(), step=1,
            key="fenster_nachhol_regler",
            help="Steht das auf 5, lässt sich ein Check-in vom 15.07. nicht "
                 "mehr einem Spieltag vom 08.07. zuordnen — das sind 7 Tage.")

        rueckblick = st.slider(
            "Überzählige Check-ins anzeigen … Tage zurück",
            min_value=7, max_value=120, value=fenster_rueckblick(), step=1,
            key="fenster_rueck_regler",
            help="Betrifft nur die Anzeige rechts, nicht die Rechnung.")

        if st.button("Zeiträume speichern", type="primary",
                     key="fenster_speichern"):
            einstellung_setzen("nachhol_fenster_tage", int(nachhol))
            einstellung_setzen("ueberzaehlig_rueckblick_tage", int(rueckblick))
            cache_leeren()
            st.toast("Gespeichert.")
            st.rerun()

        if nachhol >= 21:
            box("👀 Bei einem so weiten Fenster kann ein Check-in einem "
                "Spieltag zugeordnet werden, der Wochen zurückliegt. Prüfe "
                "die Vorschläge dann besonders genau — die Zeitnähe fällt "
                "als Beleg weg.", "warn")

        st.markdown("---")
        vorschau = auto_kandidaten(schwelle=float(wert))
        if not vorschau:
            box(f"Bei {wert} % gibt es aktuell nichts zu übernehmen.", "info")
        else:
            box(f"Bei {wert} % würde die App aktuell <b>{len(vorschau)} "
                "Fälle</b> selbst zuordnen.", "ok")
            st.dataframe(pd.DataFrame([{
                "Spieltag": datum_kurz(k["datum"]),
                "Playtomic": k["name"], "Wellpass": k["checkin"],
                "Sicherheit": f"{k['score']:.0f} %", "Belege": k["grund"],
            } for k in vorschau]), use_container_width=True, hide_index=True,
                height=min(320, 60 + 35 * len(vorschau)))

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
            st.toast("Gespeichert.")
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
                    st.toast("Gespeichert.")
                    st.rerun()
            with c2:
                if st.button("Auf Standard zurücksetzen", use_container_width=True):
                    einstellung_setzen(f"monatsziel_{m}", None)
                    st.toast("Zurückgesetzt.")
                    st.rerun()

    # ── Suche ───────────────────────────────────────────────────────────
    with t3:
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
    with t4:
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
        st.markdown("##### Zugang")
        box("Nach dem Login steht ein Token in der Adresszeile — damit bleibst "
            "du 30 Tage angemeldet, auch ohne Passwort. Wenn du das Passwort "
            "wieder abgefragt bekommen möchtest oder ein Gerät verloren hast, "
            "melde hier alle Geräte ab.", "info")
        z1, z2 = st.columns(2)
        with z1:
            alle_ab = st.checkbox("Ja, alle Geräte abmelden", key="logout_all")
        with z2:
            if st.button("🔒 Alle Geräte abmelden", disabled=not alle_ab,
                         use_container_width=True):
                token_widerrufen()
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()

        st.markdown("---")
        st.markdown("##### Wartung")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Alle Caches leeren", use_container_width=True):
                cache_leeren()
                st.toast("Geleert.")
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
     "de": "Wirkung, Wiederkehr, Teilnehmer", "an": True,
     "fn": lambda: modul_events()},
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

        # ── Was heute ansteht ───────────────────────────────────────────
        try:
            mit_nachricht = faelle_mit_nachricht(tage[:14])
            nachgeholt = 0
            frist_laeuft = 0
            if not mit_nachricht.empty:
                ang = mit_nachricht[mit_nachricht["_tage_seit"] >= 0]
                for _, r in ang.iterrows():
                    k = [x for x in nachhol_kandidaten(str(r["Name"]),
                                                       str(r["Datum"]))
                         if x[4] > 0]
                    if k:
                        nachgeholt += 1
                frist_laeuft = int(
                    (ang["_tage_seit"] > fenster_nachhol()).sum())
            nicht_angeschrieben = (len(mit_nachricht[mit_nachricht["_tage_seit"] < 0])
                                   if not mit_nachricht.empty else 0)
        except Exception:
            nachgeholt = frist_laeuft = nicht_angeschrieben = 0

        if nachgeholt or nicht_angeschrieben or frist_laeuft:
            st.markdown("")
            st.markdown("##### Was heute ansteht")
            a1, a2, a3 = st.columns(3)
            with a1:
                if nicht_angeschrieben:
                    box(f"📬 <b>{nicht_angeschrieben}</b> Spieler noch nicht "
                        "angeschrieben", "warn")
                else:
                    box("📬 Alle angeschrieben", "ok")
            with a2:
                if nachgeholt:
                    box(f"🔄 <b>{nachgeholt}</b> haben nachgeholt — "
                        "abhaken", "ok")
                else:
                    box("🔄 Keine neuen Nachholungen", "info")
            with a3:
                if frist_laeuft:
                    box(f"⏰ <b>{frist_laeuft}</b> Fristen abgelaufen", "err")
                else:
                    box("⏰ Alle Fristen im Rahmen", "ok")

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
                       initial_sidebar_state="expanded")
    css_laden()

    if not login():
        st.stop()

    st.session_state.setdefault("modul", None)
    st.session_state.setdefault("name_mapping_cache", None)

    # Die Google-Limit-Warnung soll nur einmal PRO SEITENAUFBAU
    # unterdrückt werden (siehe loadsheet()), nicht für den Rest der
    # ganzen Sitzung — sonst verschluckt ein einziger kurzer Ausrutscher
    # jede spätere Fehlermeldung, und leere Daten sehen dann wie "gibt's
    # nicht" statt wie "Google gerade nicht erreichbar" aus.
    st.session_state["_limit_gemeldet"] = False

    # ── Seitenleiste ────────────────────────────────────────────────────
    aktiv = st.session_state.modul

    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:1rem 0 1.4rem;">
          <div style="width:72px;margin:0 auto;color:{C['volt']};">{LOGO_SVG}</div>
          <div style="margin-top:.7rem;font-size:.62rem;letter-spacing:.2em;
                      color:{C['dim']};font-weight:600;">COMMAND CENTER</div>
        </div>""", unsafe_allow_html=True)

        if st.button("🏠  Übersicht", use_container_width=True,
                     key="nav_home",
                     type="primary" if aktiv is None else "secondary"):
            st.session_state.modul = None
            st.rerun()

        st.markdown("---")

        # Offene Fälle als Zahl direkt am Menüpunkt — ein Blick genügt
        try:
            offen_gesamt = int(sum(offene_je_tag().values()))
        except Exception:
            offen_gesamt = 0
        try:
            hat_daten = bool(verfuegbare_tage())
        except Exception:
            hat_daten = True

        for modul in MODULE:
            beschriftung = f"{modul['ic']}  {modul['ti']}"

            if not modul["an"]:
                st.button(f"{beschriftung}   ·  bald", key=f"nav_{modul['id']}",
                          use_container_width=True, disabled=True)
                continue

            if modul["id"] == "whatsapp" and offen_gesamt:
                beschriftung += f"   ·  {offen_gesamt}"
            elif modul["id"] == "daten" and not hat_daten:
                beschriftung += "   ·  Start hier"

            if st.button(beschriftung, key=f"nav_{modul['id']}",
                         use_container_width=True,
                         type="primary" if aktiv == modul["id"] else "secondary"):
                st.session_state.modul = modul["id"]
                st.rerun()

        st.markdown("---")
        if st.button("🚪  Abmelden", use_container_width=True, key="nav_logout"):
            token_widerrufen(st.query_params.get("auth"))
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

        st.caption(CONFIG["firma"])
        st.caption(f"{COURTS_GESAMT} Courts · {CONFIG['stadt']}")

    # ── Inhalt ──────────────────────────────────────────────────────────
    if aktiv is None:
        command_center()
    else:
        modul = next((m for m in MODULE if m["id"] == aktiv), None)
        if modul and modul["fn"]:
            modul["fn"]()
        else:
            st.session_state.modul = None
            st.rerun()

    claim_line()


if __name__ == "__main__":
    main()
