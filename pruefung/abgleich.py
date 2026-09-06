"""
Den Wellpass-Abgleich gegen echte Exporte durchrechnen.

    python3 pruefung/abgleich.py zahlungen.csv offen.csv checkins.csv [buchungen.csv]

Druckt Tag für Tag, wie viele Ansprüche entstehen, wie viele davon
einen Check-in haben und wie viele offen bleiben. Vor und nach einer
Änderung laufen lassen — verschiebt sich eine Zahl, weiss man sofort,
dass die Änderung mehr getan hat als gedacht.

Genau das hat den Fehler vom 28.08. gefunden: 8,00 € galten als Rabatt
auf 20,00 €, weil 20,00 € im ganzen Bestand genau einmal vorkam. Drei
Vollzahler standen als offene Fälle da.
"""
import umgebung
import sys, io, os
import pandas as pd
import PadelCircle as PC

BLAETTER = {}


def _sheets_ersetzen():
    """Google Sheets durch ein Wörterbuch im Arbeitsspeicher ersetzen."""
    PC.loadsheet = lambda n, cols=None: (
        (pd.DataFrame(columns=cols) if cols else pd.DataFrame())
        if BLAETTER.get(n) is None else BLAETTER[n].copy())
    PC.savesheet = lambda df, n, v=3: BLAETTER.__setitem__(n, df.copy()) or True
    PC.savesheet_append = lambda neu, n, v=3: BLAETTER.__setitem__(
        n, pd.concat([BLAETTER.get(n, pd.DataFrame()), neu],
                     ignore_index=True)) or True
    PC.cache_leeren = lambda *a, **k: None
    PC._blaetter_verwerfen = lambda *a, **k: None
    PC.einstellung = lambda k, d=None: d


def datei(pfad):
    return io.BytesIO(open(pfad, "rb").read())


def lauf(zahlungen, offen, checkins, buchungen=None):
    _sheets_ersetzen()
    PC._verarbeiten_zahlungen(datei(zahlungen), datei(checkins),
                              datei(offen),
                              datei(buchungen) if buchungen else None)
    b, c = BLAETTER["buchungen"], BLAETTER["checkins"]

    wp = int((b["Relevant"] == "Ja").sum())
    mit = int(((b["Relevant"] == "Ja") & (b["Check-in"] == "Ja")).sum())
    erg = int((b["Quelle"] == "buchung").sum())
    rabatt = round(b.loc[b["Relevant"] == "Ja", "Listenpreis"]
                   .map(PC.parse_betrag).sum()
                   - b.loc[b["Relevant"] == "Ja", "Betrag"]
                   .map(PC.parse_betrag).sum(), 2)
    verguetet = len(c.drop_duplicates(subset=["analysis_date", "Name_norm"]))

    print(f"\n{b['analysis_date'].nunique()} Tage · {len(b)} Personenzeilen "
          f"· {len(c)} Check-ins")
    print(f"Ansprüche {wp} · mit Check-in {mit} · OFFEN {wp - mit}"
          + (f" · {erg} aus der Buchungsdatei ergänzt" if erg else ""))
    print(f"Rabatt gewährt {rabatt:.2f} € · Vergütung {verguetet} × "
          f"{PC.WELLPASS_WERT:.2f} € = {verguetet * PC.WELLPASS_WERT:.2f} €")

    print(f"\n{'Tag':<12}{'Ansprüche':>10}{'mit CI':>8}{'offen':>7}"
          f"{'Check-ins':>11}{'überzählig':>12}  Probe")
    for t in sorted(b["analysis_date"].unique()):
        bt = b[b["analysis_date"] == t]
        ct = c[c["analysis_date"] == t]
        w = int((bt["Relevant"] == "Ja").sum())
        m = int(((bt["Relevant"] == "Ja") & (bt["Check-in"] == "Ja")).sum())
        zu = int((ct["Gespielt"] == "Ja").sum())
        ue = len(ct) - zu
        # Probe: gehen die Zahlen in sich auf?
        ok = "✓" if (m + (w - m) == w and zu + ue == len(ct)) else "✗"
        print(f"{t:<12}{w:>10}{m:>8}{w - m:>7}{len(ct):>11}{ue:>12}  {ok}")

    if umgebung.MELDUNGEN:
        print(f"\n{len(umgebung.MELDUNGEN)} Meldungen:")
        for art, text in umgebung.MELDUNGEN[:10]:
            print(f"   [{art}] {text[:120]}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    lauf(*sys.argv[1:5])
