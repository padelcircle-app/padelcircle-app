"""
Wenn der Bucher für Mitspieler mitbezahlt — alle Spielarten.

    python3 pruefung/mitbezahlt.py

Zahlt der Bucher die Zuzahlung eines Wellpass-Mitspielers, steht der
Mitspieler in KEINER Zahlungszeile. Auf dem Konto des Buchers liegen dann
zwei verbilligte Plätze. Diese Fälle kosten Geld, wenn sie danebengehen:
ein vergessener Check-in wird nie sichtbar, oder ein echter Check-in gilt
als überzählig.

Gerechnet wird ohne Dateien, mit erfundenen Namen. Zwei Sekunden.
"""
import umgebung
import pandas as pd
import PadelCircle as PC

BLATT = {}
PC.loadsheet = lambda n, cols=None: (BLATT[n].copy() if n in BLATT
                                     else pd.DataFrame(columns=cols or []))
PC.savesheet = lambda df, n, v=3: BLATT.__setitem__(n, df.copy()) or True
PC.savesheet_append = lambda df, n, v=3: BLATT.__setitem__(
    n, pd.concat([BLATT.get(n, pd.DataFrame()), df], ignore_index=True)) or True
PC.cache_leeren = lambda *a, **k: None
PC.einstellung = lambda k, d=None: d

fehler = []


def pruefe(bedingung, text):
    print(("  ✓ " if bedingung else "  ✗ ") + text)
    if not bedingung:
        fehler.append(text)


def leeren():
    for name in dir(PC):
        fn = getattr(PC, name)
        if callable(getattr(fn, "clear", None)) and hasattr(fn, "__wrapped__"):
            fn.clear()
    PC.st.session_state["name_mapping_cache"] = None


def zahlung(name, betrag, pid):
    """Ein Platz auf dem Konto dieser Person. 6,00 € statt 18,00 € = Wellpass."""
    return {"User name": name, "Service date": "03/09/2026 21:00",
            "Total": betrag, "Payment status": "Paid",
            "Payment method": "Apple Pay",
            "Product SKU": "User booking registration", "Payment id": pid}


def buchung(*namen):
    r = {"booking_id": "B1", "booking_start_date": "2026-09-03T21:00",
         "booking_end_date": "2026-09-03T23:00", "duration (Minuten)": 120,
         "resource_name": "Padel 2", "price": "36.00 EUR",
         "booking_type": "REGULAR_BOOKING", "payment_status": "PAID",
         "status": "FINISHED"}
    for i, n in enumerate(namen, 1):
        r[f"participant_name_{i}"] = n
    return pd.DataFrame([r])


def checkins(*paare):
    return pd.DataFrame([{"Vor- & Nachname": n, "Datum": "2026-09-03",
                          "Zeit": z} for n, z in paare])


# Der Bucher zahlt seinen eigenen Platz (6 €) und den eines Mitspielers
# (6 €); ein Vierter zahlt voll (18 €).
ZAHLUNGEN = pd.DataFrame([zahlung("Bucher Berg", 6.0, "P1"),
                          zahlung("Bucher Berg", 6.0, "P2"),
                          zahlung("Eigen Zahler", 6.0, "P3"),
                          zahlung("Voll Zahler", 18.0, "P4")])


def lauf(cdf, bdf=None):
    BLATT.clear()
    PC.st.session_state.clear()
    leeren()
    PC._analysieren_zahlungen(ZAHLUNGEN.copy(), cdf, bdf)
    leeren()
    b = BLATT["buchungen"]
    return {str(r["Name"]): (str(r["Relevant"]), str(r["Check-in"]),
                             str(r["Fehler"])) for _, r in b.iterrows()}


print("\nOHNE BUCHUNGSDATEI")
# Der Platz des Mitspielers muss trotzdem entstehen — sonst verschwindet
# ein vergessener Check-in spurlos.
stand = lauf(checkins(("Bucher Berg", "20:52")))
pruefe("Mitspieler von Bucher Berg" in stand,
       "der mitbezahlte Platz entsteht auch ohne Namen")
pruefe(stand.get("Mitspieler von Bucher Berg", ("", "", ""))[2] == "Ja",
       "ohne Check-in bleibt er ein offener Fall")

stand = lauf(checkins(("Bucher Berg", "20:52"), ("Gast Gast", "21:04")))
pruefe(stand.get("Mitspieler von Bucher Berg", ("", "", ""))[1] == "Ja",
       "genau ein sonst unerklärter Check-in deckt ihn")
pruefe(not BLATT["checkins"][BLATT["checkins"]["Gespielt"] == "Nein"].shape[0],
       "und steht danach nicht mehr als überzählig da")

print("\nMIT BUCHUNGSDATEI")
stand = lauf(checkins(("Bucher Berg", "20:52"), ("Gast Gast", "21:04")),
             buchung("Bucher Berg", "Eigen Zahler", "Gast Gast", "Voll Zahler"))
pruefe("Gast Gast" in stand and "Mitspieler von Bucher Berg" not in stand,
       "die Buchungsdatei nennt den Mitspieler beim Namen")

print("\nAUSSCHLUSSVERFAHREN")
# Zwei Teilnehmer ohne eigene Zahlung, aber nur einer hat eingecheckt.
stand = lauf(checkins(("Bucher Berg", "20:52"), ("Gast Gast", "21:04")),
             buchung("Bucher Berg", "Eigen Zahler", "Gast Gast", "Anderer Gast"))
pruefe("Gast Gast" in stand,
       "wer eingecheckt hat, bekommt den Platz — der andere nicht")
pruefe("Anderer Gast" not in stand,
       "der Teilnehmer ohne Check-in wird nicht erfunden")

# Beide eingecheckt: dann darf die App nicht raten, sondern muss fragen.
stand = lauf(checkins(("Gast Gast", "21:04"), ("Anderer Gast", "21:05")),
             buchung("Bucher Berg", "Eigen Zahler", "Gast Gast", "Anderer Gast"))
offen = BLATT.get("buchungs_luecken", pd.DataFrame())
pruefe("Gast Gast" not in stand and "Anderer Gast" not in stand,
       "bei zwei möglichen Personen wird nicht geraten")
pruefe(not offen.empty and "Gast Gast" in str(offen.iloc[0]["kandidaten"]),
       "stattdessen steht die Frage mit beiden Namen offen")

print()
if fehler:
    print(f"❌ {len(fehler)} Regel(n) gebrochen")
    raise SystemExit(1)
print("✅ alle Regeln halten")
