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
