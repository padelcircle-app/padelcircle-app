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
#   🎨  BRANDING
# ══════════════════════════════════════════════════════════════════════════════

C = {
    "navy":       "#0A1628",
    "navy_2":     "#14243D",
    "navy_3":     "#1E3354",
    "lime":       "#B8E000",
    "lime_dark":  "#93B300",
    "lime_glow":  "rgba(184,224,0,.35)",
    "blue":       "#4A7FC1",
    "ok":         "#43A047",
    "warn":       "#F39C12",
    "err":        "#E74C3C",
    "bg":         "#F6F8FB",
    "card":       "#FFFFFF",
    "text":       "#0A1628",
    "text_soft":  "#64748B",
    "border":     "#E4E9F0",
}

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


_DATE_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                 "%d.%m.%Y %H:%M", "%d.%m.%Y", "%m/%d/%Y", "%Y/%m/%d")


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
                for col in out.columns:
                    if out[col].dtype.kind in "fc":
                        out[col] = out[col].map(lambda x: "" if pd.isna(x) else str(x))
                    else:
                        out[col] = out[col].astype(str)
                out = out.replace(["nan", "NaT", "None", "<NA>"], "")
                ws.update([out.columns.tolist()] + out.values.tolist(),
                          value_input_option="RAW")
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


def append_rows(neu: pd.DataFrame, sheet_name: str, key_cols: list) -> int:
    """Neue Zeilen anhängen, Duplikate anhand key_cols überspringen."""
    if neu.empty:
        return 0
    key_cols = [c for c in key_cols if c in neu.columns]
    if not key_cols:
        savesheet(neu, sheet_name)
        return len(neu)

    alt = loadsheet(sheet_name)

    def schluessel(df):
        return df[key_cols].astype(str).agg("|".join, axis=1)

    if not alt.empty and all(c in alt.columns for c in key_cols):
        vorhanden = set(schluessel(alt))
        neu = neu[~schluessel(neu).isin(vorhanden)]
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

    st.markdown("""
    <div class="pc-login">
      <div class="pc-login-logo">
        <span>PC</span>
      </div>
      <h1>PADEL CIRCLE</h1>
      <div class="pc-login-sub">Command Center</div>
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

    st.markdown('<div class="pc-claim-line">ONCE IN &nbsp;·&nbsp; NEVER OUT</div>',
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
    """Kundenliste mit Name / Telefon / E-Mail / Geburtstag."""
    text = _text_lesen(datei)
    if not text:
        return pd.DataFrame()
    probe = text[:2000]
    trenner = ";" if probe.count(";") > probe.count(",") else ","
    try:
        datei.seek(0)
        df = pd.read_csv(datei, sep=trenner, engine="python",
                         on_bad_lines="skip", encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.replace("\ufeff", "").str.lower()
    except Exception as e:
        st.error(f"❌ Kunden-CSV: {str(e)[:150]}")
        return pd.DataFrame()

    um = {}
    for sp in df.columns:
        if sp in ("name", "full name", "vor- & nachname", "kunde", "spieler"):
            um[sp] = "name"
        elif any(k in sp for k in ("phone", "telefon", "mobil", "handy")):
            um[sp] = "phone_number"
        elif "mail" in sp:
            um[sp] = "email"
        elif any(k in sp for k in ("geburt", "birth", "geb")):
            um[sp] = "geburtstag"
    return df.rename(columns=um) if um else df


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

    wellpass = buchungen[(buchungen["_betrag"] == 0) & (~buchungen["_team"])]
    k["wellpass_anzahl"] = int(len(wellpass))
    k["wellpass_wert"] = round(len(wellpass) * WELLPASS_WERT, 2)
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
#   🎨  DESIGN-SYSTEM  +  ANIMATIONEN
# ══════════════════════════════════════════════════════════════════════════════

def css_laden():
    st.markdown(f"""
    <style>
      @keyframes pcFadeUp {{
        from {{ opacity:0; transform:translateY(10px); }}
        to   {{ opacity:1; transform:translateY(0); }}
      }}
      @keyframes pcPulse {{
        0%,100% {{ box-shadow:0 0 0 0 {C['lime_glow']}; }}
        50%     {{ box-shadow:0 0 0 7px rgba(184,224,0,0); }}
      }}
      @keyframes pcSweep {{
        0%   {{ background-position:-180% 0; }}
        100% {{ background-position:180% 0; }}
      }}
      @keyframes pcRing {{
        from {{ stroke-dashoffset: 314; }}
      }}
      @keyframes pcPop {{
        0%   {{ transform:scale(.9); opacity:0; }}
        60%  {{ transform:scale(1.03); }}
        100% {{ transform:scale(1); opacity:1; }}
      }}
      @keyframes pcGlow {{
        0%,100% {{ opacity:.5; }}
        50%     {{ opacity:1; }}
      }}

      .stApp {{ background:{C['bg']}; }}
      #MainMenu, footer, header {{ visibility:hidden; }}
      .block-container {{ padding-top:2rem; }}

      /* ── Login ───────────────────────────────────────────────── */
      .pc-login {{ text-align:center; margin:3.5rem 0 1.5rem;
                   animation:pcFadeUp .5s ease both; }}
      .pc-login-logo {{
        display:inline-flex; align-items:center; justify-content:center;
        width:92px; height:92px; border-radius:50%;
        background:{C['navy']}; border:3px solid {C['lime']};
        animation:pcPulse 2.6s ease-in-out infinite;
      }}
      .pc-login-logo span {{ color:#fff; font-size:31px; font-weight:700;
                            letter-spacing:1px; }}
      .pc-login h1 {{ color:{C['navy']}; margin:1.1rem 0 .15rem;
                      font-size:2rem; letter-spacing:4px; font-weight:600; }}
      .pc-login-sub {{ color:{C['text_soft']}; font-size:.85rem;
                       letter-spacing:2px; text-transform:uppercase; }}

      .pc-claim-line {{
        text-align:center; margin:2.5rem 0 1rem;
        font-size:10px; letter-spacing:4px; color:{C['text_soft']};
        animation:pcGlow 3.5s ease-in-out infinite;
      }}

      /* ── Header ──────────────────────────────────────────────── */
      .pc-head {{
        background:{C['navy']}; border-radius:16px;
        padding:1.5rem 1.8rem; margin-bottom:1.3rem;
        position:relative; overflow:hidden;
        animation:pcFadeUp .45s ease both;
      }}
      .pc-head::after {{
        content:''; position:absolute; left:0; right:0; bottom:0; height:3px;
        background:linear-gradient(90deg,{C['lime']} 0%,{C['lime']} 35%,
                   rgba(184,224,0,.15) 60%,{C['lime']} 100%);
        background-size:200% 100%;
        animation:pcSweep 5s linear infinite;
      }}
      .pc-head h1 {{ color:#fff; margin:0; font-size:1.55rem;
                     font-weight:600; letter-spacing:.5px; }}
      .pc-head .sub {{ color:{C['lime']}; font-size:.75rem;
                       letter-spacing:2.5px; margin-top:.35rem;
                       text-transform:uppercase; }}

      /* ── Karten & Kennzahlen ────────────────────────────────── */
      .pc-card {{
        background:{C['card']}; border:1px solid {C['border']};
        border-radius:12px; padding:1rem 1.2rem; margin-bottom:.75rem;
        animation:pcFadeUp .4s ease both;
      }}

      .pc-kpi {{
        background:{C['card']}; border:1px solid {C['border']};
        border-left:3px solid {C['lime']}; border-radius:11px;
        padding:.9rem 1.1rem; height:100%;
        transition:transform .16s ease, box-shadow .16s ease;
        animation:pcPop .4s ease both;
      }}
      .pc-kpi:hover {{ transform:translateY(-2px);
                       box-shadow:0 6px 18px rgba(10,22,40,.09); }}
      .pc-kpi .l {{ color:{C['text_soft']}; font-size:.7rem;
                    text-transform:uppercase; letter-spacing:1.1px; }}
      .pc-kpi .v {{ color:{C['navy']}; font-size:1.5rem;
                    font-weight:650; margin-top:.2rem; line-height:1.15; }}
      .pc-kpi .h {{ color:{C['text_soft']}; font-size:.73rem; margin-top:.15rem; }}
      .pc-kpi .d {{ font-size:.73rem; margin-top:.2rem; font-weight:600; }}
      .pc-kpi .d.up   {{ color:{C['ok']}; }}
      .pc-kpi .d.down {{ color:{C['err']}; }}

      /* ── Hinweisboxen ───────────────────────────────────────── */
      .pc-box {{ border-radius:10px; padding:.8rem 1.05rem; margin:.55rem 0;
                 font-size:.88rem; line-height:1.55;
                 animation:pcFadeUp .35s ease both; }}
      .pc-box.info  {{ background:#EFF5FF; border-left:3px solid {C['blue']}; color:#1B3A5F; }}
      .pc-box.ok    {{ background:#F0F9EA; border-left:3px solid {C['ok']};   color:#1B5E20; }}
      .pc-box.warn  {{ background:#FFF7E6; border-left:3px solid {C['warn']}; color:#7A4A00; }}
      .pc-box.err   {{ background:#FDEFEE; border-left:3px solid {C['err']};  color:#8B1F1F; }}

      /* ── Modul-Kacheln ──────────────────────────────────────── */
      .pc-tile {{
        background:{C['navy']}; border:1px solid rgba(184,224,0,.28);
        border-radius:14px; padding:1.1rem 1.2rem 1.25rem;
        min-height:132px; position:relative;
        transition:transform .18s ease, border-color .18s ease,
                   box-shadow .18s ease;
        animation:pcPop .45s ease both;
      }}
      .pc-tile:hover {{ transform:translateY(-3px);
                        border-color:{C['lime']};
                        box-shadow:0 10px 26px rgba(10,22,40,.22); }}
      .pc-tile.soon {{ border-style:dashed; border-color:rgba(255,255,255,.18);
                       opacity:.5; }}
      .pc-tile.soon:hover {{ transform:none; box-shadow:none; }}
      .pc-tile .ic {{ font-size:1.45rem; }}
      .pc-tile .ti {{ color:#fff; font-size:.98rem; font-weight:600;
                      margin-top:.6rem; }}
      .pc-tile .de {{ color:rgba(255,255,255,.52); font-size:.78rem;
                      margin-top:.2rem; line-height:1.45; }}
      .pc-tile .bg {{
        position:absolute; top:1rem; right:1.1rem;
        background:{C['lime']}; color:{C['navy']};
        font-size:.63rem; font-weight:700; padding:.16rem .52rem;
        border-radius:10px; letter-spacing:.4px;
      }}
      .pc-tile .bg.alert {{ animation:pcPulse 2s ease-in-out infinite; }}
      .pc-tile .bg.muted {{ background:rgba(255,255,255,.11);
                            color:rgba(255,255,255,.55); }}

      /* ── Fortschrittsring ───────────────────────────────────── */
      .pc-ring-wrap {{ display:flex; align-items:center; gap:1.2rem;
                       background:{C['card']}; border:1px solid {C['border']};
                       border-radius:12px; padding:1.1rem 1.3rem;
                       animation:pcFadeUp .4s ease both; }}
      .pc-ring circle.bar {{ animation:pcRing 1.1s ease-out both; }}

      /* ── Streak-Banner ──────────────────────────────────────── */
      .pc-streak {{
        background:linear-gradient(100deg,{C['navy']} 0%,{C['navy_3']} 100%);
        border-radius:12px; padding:1rem 1.3rem; color:#fff;
        display:flex; align-items:center; justify-content:space-between;
        animation:pcFadeUp .4s ease both;
      }}
      .pc-streak .n {{ font-size:2rem; font-weight:700; color:{C['lime']};
                       line-height:1; }}
      .pc-streak .t {{ font-size:.8rem; color:rgba(255,255,255,.65);
                       letter-spacing:.4px; }}

      /* ── Spieler-Zeile ──────────────────────────────────────── */
      .pc-row {{
        background:{C['card']}; border:1px solid {C['border']};
        border-radius:10px; padding:.7rem 1rem; margin-bottom:.45rem;
        display:flex; align-items:center; justify-content:space-between;
        transition:border-color .15s ease;
      }}
      .pc-row:hover {{ border-color:{C['lime']}; }}
      .pc-row .nm {{ font-weight:600; color:{C['navy']}; }}
      .pc-row .mt {{ color:{C['text_soft']}; font-size:.8rem; }}

      .pc-medal {{ font-size:1.05rem; margin-right:.4rem; }}

      /* ── Rang-Abzeichen ─────────────────────────────────────── */
      .pc-chip {{
        display:inline-block; padding:.14rem .55rem; border-radius:20px;
        font-size:.68rem; font-weight:600; letter-spacing:.3px;
      }}
      .pc-chip.lime {{ background:{C['lime']}; color:{C['navy']}; }}
      .pc-chip.soft {{ background:#EEF2F7; color:{C['text_soft']}; }}
      .pc-chip.warn {{ background:#FFF0D6; color:#7A4A00; }}
      .pc-chip.err  {{ background:#FDE2E0; color:#8B1F1F; }}

      /* ── Buttons ────────────────────────────────────────────── */
      div.stButton > button {{ border-radius:8px; font-weight:500;
                               transition:transform .12s ease; }}
      div.stButton > button:active {{ transform:scale(.98); }}
      div.stButton > button[kind="primary"] {{
        background:{C['navy']}; border:1px solid {C['navy']};
      }}
      div.stButton > button[kind="primary"]:hover {{
        background:{C['navy_2']}; border-color:{C['lime']};
      }}

      /* ── Tabs ───────────────────────────────────────────────── */
      .stTabs [data-baseweb="tab-list"] {{ gap:.25rem; }}
      .stTabs [data-baseweb="tab"] {{ border-radius:8px 8px 0 0;
                                      padding:.4rem 1rem; }}
      .stTabs [aria-selected="true"] {{
        background:{C['navy']} !important; color:#fff !important;
      }}

      /* ── Sidebar ────────────────────────────────────────────── */
      section[data-testid="stSidebar"] {{ background:{C['card']}; }}
    </style>
    """, unsafe_allow_html=True)


def head(titel: str, unter: str = ""):
    st.markdown(f"""
    <div class="pc-head">
      <h1>{titel}</h1>
      <div class="sub">{unter or CONFIG['claim']}</div>
    </div>""", unsafe_allow_html=True)


def kpi(label: str, wert: str, hinweis: str = "", delta: float = None,
        delta_text: str = ""):
    """Kennzahl-Kachel. delta = Veränderung in % gegenüber Vorperiode."""
    d_html = ""
    if delta is not None:
        richtung = "up" if delta >= 0 else "down"
        pfeil = "▲" if delta >= 0 else "▼"
        d_html = (f'<div class="d {richtung}">{pfeil} {abs(delta):.0f}% '
                  f'{delta_text}</div>')
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
    """Animierter SVG-Ring — z.B. für den Monatsziel-Fortschritt."""
    p = max(0.0, min(float(prozent_wert), 100.0))
    umfang = 314.0
    offset = umfang - (p / 100.0 * umfang)
    farbe = C["lime"] if p >= 100 else (C["blue"] if p >= 60 else C["warn"])

    st.markdown(f"""
    <div class="pc-ring-wrap">
      <svg class="pc-ring" width="108" height="108" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="50" fill="none"
                stroke="{C['border']}" stroke-width="10"/>
        <circle class="bar" cx="60" cy="60" r="50" fill="none"
                stroke="{farbe}" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="{umfang}" stroke-dashoffset="{offset}"
                transform="rotate(-90 60 60)"/>
        <text x="60" y="66" text-anchor="middle"
              font-size="21" font-weight="650" fill="{C['navy']}">{mitte_text}</text>
      </svg>
      <div>
        <div style="font-weight:600;color:{C['navy']};font-size:1.02rem;">{titel}</div>
        <div style="color:{C['text_soft']};font-size:.83rem;margin-top:.25rem;
                    line-height:1.5;">{unter}</div>
      </div>
    </div>""", unsafe_allow_html=True)


def streak_banner(tage: int):
    if tage <= 0:
        return
    wort = "Tag" if tage == 1 else "Tage"
    st.markdown(f"""
    <div class="pc-streak">
      <div>
        <div class="t">SAUBERE SERIE</div>
        <div style="font-size:.92rem;margin-top:.2rem;">
          {tage} {wort} in Folge ohne vergessenen Check-in
        </div>
      </div>
      <div class="n">{tage}</div>
    </div>""", unsafe_allow_html=True)


def chip(text: str, art: str = "soft") -> str:
    return f'<span class="pc-chip {art}">{text}</span>'


def claim_line():
    st.markdown('<div class="pc-claim-line">ONCE IN &nbsp;·&nbsp; NEVER OUT</div>',
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
        margin=dict(l=8, r=8, t=28, b=8),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=1.14, x=0,
                    bgcolor="rgba(0,0,0,0)"),
        yaxis_title=titel_y,
        font=dict(color=C["text"], size=12),
        hoverlabel=dict(bgcolor=C["navy"], font_color="white"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=C["border"], zerolinecolor=C["border"])
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#   📦  MODUL · DATEN-ZENTRALE
# ══════════════════════════════════════════════════════════════════════════════

def _verarbeiten(p_datei, c_datei) -> bool:
    """Playtomic-Buchungen und Wellpass-Check-ins abgleichen."""
    pdf = parse_playtomic(p_datei)
    if pdf.empty:
        return False
    cdf = parse_checkins(c_datei)
    if cdf.empty:
        st.error("❌ Check-in-Datei konnte nicht gelesen werden.")
        return False

    st.caption(f"Playtomic {len(pdf)} Zeilen · Check-ins {len(cdf)} Zeilen")

    # ── Rohdaten sichern ────────────────────────────────────────────────
    key_raw = [c for c in ("Payment id", "User name", "Service date")
               if c in pdf.columns] or ["User name", "Service date"]
    neu_raw = append_rows(pdf, "playtomic_raw", key_raw)

    # ── Playtomic aufbereiten ───────────────────────────────────────────
    p = pdf.copy()
    p["Name"] = p["User name"].astype(str)
    p["Name_norm"] = p["Name"].map(normalize_name)
    p["_dt"] = p["Service date"].map(parse_datetime_safe)
    p = p[p["_dt"].notna()].copy()
    if p.empty:
        st.error("❌ Keine lesbaren Datumsangaben in der Playtomic-Datei.")
        return False

    p["Servicedatum"] = p["_dt"].map(lambda d: d.date())
    p["Service_Zeit"] = p["_dt"].map(lambda d: d.strftime("%H:%M"))
    p["Betrag_num"] = p["Total"].map(parse_betrag)

    if "Payment id" in p.columns:
        p = p.drop_duplicates(subset=["Payment id"])

    leer = pd.Series(False, index=p.index)

    wallet = (p["Payment method"].astype(str).str.lower()
              .str.contains("wallet", na=False)
              if "Payment method" in p.columns else leer)
    frei = (p["Payment method"].astype(str).str.lower()
            .str.contains("free", na=False)
            if "Payment method" in p.columns else leer)
    einzelzahler = (p["Payment type"].astype(str).str.lower()
                    .str.contains("single", na=False)
                    if "Payment type" in p.columns else leer)

    hat_rabatt = frei | ((p["Betrag_num"] < CONFIG["wellpass_zuzahlung_max"]) &
                         (p["Betrag_num"] > 0))

    p["Relevant"] = (hat_rabatt & (~wallet) &
                     (~(einzelzahler & (p["Betrag_num"] >= CONFIG["single_payer_min"]))))

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

    # ── Tagesweiser Abgleich ────────────────────────────────────────────
    alle_tage = sorted(set(p["Servicedatum"]) | set(c["Checkin_Datum"]))
    if not alle_tage:
        st.error("❌ Keine gültigen Tage gefunden.")
        return False

    balken = st.progress(0.0)
    status = st.empty()

    mapping = mapping_laden()
    p_nach_tag = dict(tuple(p.groupby("Servicedatum")))
    c_nach_tag = dict(tuple(c.groupby("Checkin_Datum")))

    buchungen_out, checkins_out = [], []

    for i, tag in enumerate(alle_tage):
        balken.progress((i + 1) / len(alle_tage))
        status.caption(f"{tag.strftime('%d.%m.%Y')}  ·  {i+1}/{len(alle_tage)}")

        p_tag = p_nach_tag.get(tag, pd.DataFrame())
        c_tag = c_nach_tag.get(tag, pd.DataFrame())
        checkin_namen = (set(c_tag["Name_norm"]) if not c_tag.empty else set())
        zeit_je_name = (dict(zip(c_tag["Name_norm"], c_tag["Checkin_Zeit"]))
                        if not c_tag.empty else {})

        for row in p_tag.itertuples(index=False):
            nn = row.Name_norm
            team = nn in TEAM_NORM

            hat_checkin = nn in checkin_namen
            checkin_zeit = zeit_je_name.get(nn, "")

            if not hat_checkin and nn in mapping:
                gelernt = mapping[nn]
                gname = gelernt["checkin_name"] if isinstance(gelernt, dict) else gelernt
                if gname in checkin_namen:
                    hat_checkin = True
                    checkin_zeit = zeit_je_name.get(gname, "")

            fehler = bool(row.Relevant) and not hat_checkin and not team

            buchungen_out.append({
                "Datum": str(tag), "Name": row.Name, "Name_norm": nn,
                "Betrag": row.Betrag_num, "Service_Zeit": row.Service_Zeit,
                "Checkin_Zeit": checkin_zeit,
                "Relevant": "Ja" if row.Relevant else "Nein",
                "Check-in": "Ja" if hat_checkin else "Nein",
                "Team": "Ja" if team else "Nein",
                "Fehler": "Ja" if fehler else "Nein",
                "analysis_date": tag.strftime("%Y-%m-%d"),
            })

        if not c_tag.empty:
            spiel_namen = set(p_tag["Name_norm"]) if not p_tag.empty else set()
            gesehen = set()
            for row in c_tag.itertuples(index=False):
                if row.Name_norm in gesehen:
                    continue
                gesehen.add(row.Name_norm)
                checkins_out.append({
                    "Datum": str(tag), "Name": row.Name,
                    "Name_norm": row.Name_norm,
                    "Checkin_Zeit": row.Checkin_Zeit,
                    "Gespielt": "Ja" if row.Name_norm in spiel_namen else "Nein",
                    "analysis_date": tag.strftime("%Y-%m-%d"),
                })

    balken.progress(1.0)
    status.empty()

    neu_b = append_rows(pd.DataFrame(buchungen_out), "buchungen",
                        ["analysis_date", "Name_norm", "Service_Zeit"])
    neu_c = append_rows(pd.DataFrame(checkins_out), "checkins",
                        ["analysis_date", "Name_norm", "Checkin_Zeit"])

    cache_leeren()

    st.success(f"✅ {neu_b} neue Buchungen · {neu_c} neue Check-ins · "
               f"{neu_raw} Rohdaten-Zeilen")
    if neu_b or neu_c:
        st.balloons()
    else:
        box("Alle Daten waren bereits im System — nichts doppelt gespeichert.", "info")
    return True


def modul_daten():
    head("Daten-Zentrale", "Playtomic · Wellpass · Kunden")

    t1, t2, t3 = st.tabs(["📊 Buchungen + Check-ins", "👥 Kundenliste", "🗂 Bestand"])

    # ── Haupt-Upload ────────────────────────────────────────────────────
    with t1:
        box("Beide Dateien gehören zusammen: Playtomic sagt wer gespielt hat, "
            "Wellpass wer eingecheckt hat. Die App findet die Lücke dazwischen. "
            "Dieselbe Datei mehrfach hochladen ist unproblematisch — "
            "Duplikate werden erkannt.", "info")

        c1, c2 = st.columns(2)
        with c1:
            p_datei = st.file_uploader("Playtomic-Export (.csv)", type=["csv"],
                                       key="up_p")
            if p_datei:
                st.caption(f"✓ {p_datei.name}")
        with c2:
            c_datei = st.file_uploader("Wellpass Check-ins (.csv)", type=["csv"],
                                       key="up_c")
            if c_datei:
                st.caption(f"✓ {c_datei.name}")

        st.markdown("")
        if st.button("🔄 Daten verarbeiten", type="primary",
                     use_container_width=True,
                     disabled=not (p_datei and c_datei)):
            with st.spinner(lade_text("verarbeite")):
                if _verarbeiten(p_datei, c_datei):
                    time.sleep(1.1)
                    st.rerun()

        if not (p_datei and c_datei):
            st.caption("Beide Dateien werden für den Abgleich gebraucht.")

        with st.expander("Wo finde ich die Exporte?"):
            st.markdown(f"""
**Playtomic**
1. Einloggen → Bereich *Payments* / *Zahlungen*
2. Zeitraum wählen
3. CSV exportieren

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
                if savesheet(df, "customers"):
                    cache_leeren()
                    st.success(f"✅ {len(df)} Kunden gespeichert.")
                    time.sleep(.9)
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
                    f"font-weight:600;color:{C['navy']};'>{datum_lang(datum)}</div>",
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
                marker_color=[C["lime"] if v == max(werte) and v > 0
                              else C["navy"] for v in werte],
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
                         marker_color=C["navy"]))
    fig.add_trace(go.Bar(x=df["tag"], y=df["Wellpass"], name="Wellpass",
                         marker_color=C["lime"]))
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

    box("Je dunkler das Feld, desto mehr Buchungen. Helle Felder in der Prime-Time "
        "sind bares Geld — dort lohnen sich Events, Kurse oder Aktionen.", "info")

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
        colorscale=[[0, "#F2F6FA"], [0.35, "#A8D400"], [1, C["navy"]]],
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


def modul_dashboard():
    head("Business Dashboard", "Umsatz · Auslastung · Prognose")
    t1, t2, t3 = st.tabs(["📅 Tag", "📈 Monat", "🔥 Auslastung"])
    with t1:
        _dash_tag()
    with t2:
        _dash_monat()
    with t3:
        _dash_auslastung()


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
        for i, (_, r) in enumerate(offen.iterrows()):
            name = str(r["Name"])
            nn = str(r["Name_norm"])
            datum = str(r["Datum"])
            betrag = r.get("Betrag", 0)
            zeit = str(r.get("Service_Zeit", "")).strip()
            nummer = str(r["_nummer"])
            gesendet = schon_gesendet(nn, datum, betrag)

            st.markdown(f"""
            <div class="pc-card">
              <div style="display:flex;justify-content:space-between;
                          align-items:baseline;">
                <div>
                  <span style="font-weight:600;color:{C['navy']};">{name}</span>
                  <span style="color:{C['text_soft']};font-size:.85rem;">
                    &nbsp;· {datum_kurz(datum)}{' · ' + zeit + ' Uhr' if zeit else ''}
                  </span>
                </div>
                <div style="color:{C['text_soft']};font-size:.78rem;">
                  {'📤 ' + gesendet.strftime('%d.%m. %H:%M') if gesendet else ''}
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns([1.8, 1.1, 1.1, 1])
            with c1:
                st.caption(f"📱 {nummer}" if len(nummer) > 5
                           else "⚠️ keine Nummer")
            with c2:
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
            with c3:
                if gesendet and st.button("Nachfassen", key=f"wa_n_{i}",
                                          use_container_width=True,
                                          disabled=not (len(nummer) > 5
                                                        and twilio_bereit())):
                    txt = zweiter_reminder(name, datum_kurz(datum))
                    with st.spinner("Sende…"):
                        if whatsapp_senden(f"whatsapp:{nummer}", txt):
                            whatsapp_loggen(name, nn, datum, betrag, nummer,
                                            art="nachfassen")
                            st.success("✅")
                            time.sleep(.9)
                            st.rerun()
            with c4:
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
                  <span style="color:{C['text_soft']};font-size:.78rem;">
                    Playtomic</span><br>
                  <span style="font-weight:600;color:{C['navy']};">
                    {v['buchung']}</span>
                </div>
                <div style="font-size:1.3rem;color:{C['lime']};">↔</div>
                <div style="text-align:right;">
                  <span style="color:{C['text_soft']};font-size:.78rem;">
                    Wellpass</span><br>
                  <span style="font-weight:600;color:{C['navy']};">
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
        <div style="text-align:center;padding:.8rem 0 1.3rem;">
          <div style="display:inline-flex;align-items:center;
                      justify-content:center;width:52px;height:52px;
                      border-radius:50%;background:{C['navy']};
                      border:2px solid {C['lime']};">
            <span style="color:#fff;font-size:17px;font-weight:700;">PC</span>
          </div>
          <div style="margin-top:.55rem;font-size:.7rem;letter-spacing:2px;
                      color:{C['text_soft']};">COMMAND CENTER</div>
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
