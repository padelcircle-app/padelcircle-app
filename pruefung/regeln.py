"""
Die harten Regeln prüfen — ohne Dateien, in zwei Sekunden.

    python3 pruefung/regeln.py

Diese Regeln kosten Geld, wenn sie brechen. Jede stammt aus einem
Fehler, der schon einmal passiert ist.
"""
import umgebung
import pandas as pd
import PadelCircle as PC

fehler = []


def pruefe(bedingung, text):
    print(("  ✓ " if bedingung else "  ✗ ") + text)
    if not bedingung:
        fehler.append(text)


print("\nNAMEN")
# Kevin und Lina Schafran sind Geschwister. Ein Check-in von ihm darf
# ihren Fall nie schliessen.
for a, b in (("lina schafran", "kevin schafran"),
             ("marie weber", "gunter weber"),
             ("anna bentele", "peter bentele")):
    pruefe(PC.namen_sind_verschiedene_personen(a, b)
           and PC.namen_sind_verschiedene_personen(b, a),
           f"{a} und {b} gelten als zwei Menschen")
for a, b in (("kartal", "necmettin kartal"),
             ("fridtjof spohler", "ole fridtjof spohler"),
             ("jens b", "jens bilinsky"),
             ("ka he", "katharina hell"),
             ("michael muller", "michael mueller")):
    pruefe(not PC.namen_sind_verschiedene_personen(a, b),
           f"{a} → {b} bleibt erlaubt")

print("\nGELD")
pruefe(PC.WELLPASS_RABATT == 12.0,
       "Playtomic-Rabatt 12,00 € — nur für den Abgleich")
pruefe(PC.wellpass_wert_am("2026-08-27") == 12.35,
       "EGYM-Vergütung 12,35 € — unabhängig davon, ohne Datumslogik")
pruefe(13.0 in PC.abzug_kandidaten("2026-08-27"),
       "13,00 € bleibt möglich (zwei Wochen Vorlauf beim Buchen)")

print("\nPREISE")
from datetime import datetime
for start, dauer, single, erwartet in (
        (datetime(2026, 8, 26, 11, 0), 120, False, 60.0),   # 28 + 32
        (datetime(2026, 8, 26, 11, 30), 60, False, 30.0),   # 14 + 16
        (datetime(2026, 8, 28, 15, 0), 60, False, 32.0),
        (datetime(2026, 8, 28, 15, 0), 90, False, 50.0),    # 32 + 18
        (datetime(2026, 8, 29, 11, 0), 60, False, 36.0),    # Samstag
        (datetime(2026, 8, 26, 15, 0), 90, True, 29.0)):    # 18 + 11
    ist = PC.listenpreis(start, dauer, single)
    pruefe(abs(ist - erwartet) < 0.005,
           f"{start:%a %H:%M} {dauer} Min "
           f"{'Single' if single else 'Double'} = {erwartet:.2f} €")
pruefe(PC.ist_single_court("Padel 6") and PC.ist_single_court("Single Court Padel 6"),
       "Padel 6 zählt als Single Court (hiess früher nur so)")
pruefe(not PC.ist_single_court("Padel 4"), "Padel 4 bleibt Double")

BLATT = {}
PC.loadsheet = lambda n, cols=None: (BLATT[n].copy() if n in BLATT
                                     else pd.DataFrame(columns=cols or []))


def leeren():
    """Zwischenspeicher weg — die Attrappe merkt sich sonst alte Stände."""
    for name in dir(PC):
        fn = getattr(PC, name)
        if callable(getattr(fn, "clear", None)) and hasattr(fn, "__wrapped__"):
            fn.clear()


def zuordnung(ci_datum, fall_datum, name):
    return {"checkin_key": f"{ci_datum}|{name}", "fall_key": f"{fall_datum}|{name}",
            "checkin_datum": ci_datum, "checkin_name": name,
            "fall_datum": fall_datum, "fall_name": name, "timestamp": ""}


print("\nNACHHOLUNGEN")
# Linas Fall vom 27.08. hing an ihrem Check-in vom 30.08. Den braucht sie
# selbst — sie spielte am 30.08. mit Rabatt. Holt sie am 02.09. nach und
# klickt man „Nachgeholt", muss der Fall zugehen. Vorher hielt die alte
# Zeile ihn offen, und der Klick bewirkte sichtbar nichts.
BLATT["buchungen"] = pd.DataFrame([{
    "analysis_date": "2026-08-30", "Name": "Lina Schafran",
    "Name_norm": "lina schafran", "Relevant": "Ja"}])
BLATT["checkin_zuordnung"] = pd.DataFrame(
    [zuordnung("2026-08-30", "2026-08-27", "lina schafran")])
leeren()
pruefe("2026-08-27|lina schafran" in PC.hinfaellige_fall_keys(),
       "eine ungültige Nachholung öffnet den Fall wieder")
BLATT["checkin_zuordnung"] = pd.DataFrame(
    [zuordnung("2026-08-30", "2026-08-27", "lina schafran"),
     zuordnung("2026-09-02", "2026-08-27", "lina schafran")])
leeren()
pruefe("2026-08-27|lina schafran" not in PC.hinfaellige_fall_keys(),
       "eine neue, gültige Nachholung schliesst ihn trotz der alten Zeile")
v = PC.verbrauchte_checkins()
pruefe("2026-09-02|lina schafran" in v and "2026-08-30|lina schafran" not in v,
       "der neue Check-in ist verbraucht, der alte wieder frei")

print("\nDOPPELTE CHECK-INS")
# Berkay Kürekci scannte am 29.08. zweimal; der zweite deckte sein Spiel.
BLATT["checkin_zuordnung"] = pd.DataFrame(columns=PC.SHEET_SPALTEN["checkin_zuordnung"])
BLATT["checkins"] = pd.DataFrame([
    {"analysis_date": "2026-08-29", "Name": "Berkay Kürekci",
     "Name_norm": "berkay kurekci", "Gespielt": "Ja", "Checkin_Zeit": "18:56"},
    {"analysis_date": "2026-08-29", "Name": "Berkay Kürekci",
     "Name_norm": "berkay kurekci", "Gespielt": "Nein", "Checkin_Zeit": "15:20"},
    {"analysis_date": "2026-08-29", "Name": "Stefanie Egerer",
     "Name_norm": "stefanie egerer", "Gespielt": "Nein", "Checkin_Zeit": "18:22"}])
leeren()
namen = set(PC.offene_checkins("2026-08-29")["Name_norm"])
pruefe("berkay kurekci" not in namen,
       "ein zweiter Scan am selben Tag gilt nicht als überzählig")
pruefe("stefanie egerer" in namen,
       "wer ohne Rabatt spielte und eincheckte, bleibt sichtbar")

print("\nSTORNIERT")
# Steffi Gengenbach, 31.08. 17:30: 0 € bezahlt, 0 € erstattet, 11 €
# verfallen. Die Buchung war storniert — kein Fall.
from datetime import date
g = {"name": "Steffi Gengenbach", "name_norm": "steffi gengenbach",
     "datum": date(2026, 8, 31), "zeit": "17:30", "minute": 17 * 60 + 30,
     "netto": 0.0, "verfallen": 11.0, "zeilen": 3, "erstattet": True,
     "frei": True, "bezahlt_zeilen": 2, "turnier": False, "plaetze": [],
     "erstattungen": [0.0], "preis": 0.0}
volle = {None: {22.0, 23.0, 24.0, 24.5}}
pruefe(PC.slot_bewerten(g, volle, {}, {})[0] == "storniert",
       "ganz erstattet + verfallener Rest = storniert, kein offener Fall")

print("\nCHECK-INS")
CI = pd.DataFrame([
    {"Name_norm": "kevin schafran", "Gespielt": "Ja",
     "analysis_date": "2026-08-27"},
    {"Name_norm": "jens bilinsky", "Gespielt": "Nein",
     "analysis_date": "2026-08-27"}])
PC.loadsheet = lambda n, cols=None: CI.copy() if n == "checkins" else pd.DataFrame()
PC.verbrauchte_checkins = lambda: set()
PC.mapping_roh = lambda: {"lina schafran": "kevin schafran",
                          "jens b": "jens bilinsky"}
PC.mapping_gedeckt_je_tag.clear()
g = PC.mapping_gedeckt_je_tag().get("2026-08-27", set())
pruefe("lina schafran" not in g,
       "ein verbrauchter Check-in deckt keinen zweiten Fall")
pruefe("jens b" in g,
       "ein freier Check-in deckt weiter über die Verknüpfung")

print()
if fehler:
    print(f"❌ {len(fehler)} Regel(n) gebrochen")
    raise SystemExit(1)
print("✅ alle Regeln halten")
