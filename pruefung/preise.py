"""
Die Preisliste gegen jede einzelne Buchung prüfen.

    python3 pruefung/preise.py buchungen.csv

Für jede bezahlte Buchung wird der Listenpreis aus der hinterlegten
Preisliste gerechnet und mit dem verglichen, was Playtomic kassiert
hat. Die Differenz muss eine Summe aus Wellpass-Rabatten sein — sonst
stimmt etwas nicht: der Preis, die Court-Zuordnung oder der Abzug.

So kam heraus, dass im Juli 13,00 € abgezogen wurden statt 12,00 €
(255 von 907 Buchungen gingen nicht auf) und dass „Padel 6" damals
der Single Court war (55 von 66).
"""
import umgebung
import sys, csv, collections
from datetime import datetime
import PadelCircle as PC


def pruefen(pfad):
    zeilen = list(csv.DictReader(open(pfad, encoding="utf-8-sig")))
    je_court = collections.defaultdict(lambda: [0, 0])
    schief = []
    for x in zeilen:
        if x.get("status") == "CANCELED" or x.get("booking_type") == "OPEN_PLAY":
            continue
        if x.get("payment_status") not in ("PAID", "PARTIAL_PAID"):
            continue
        start = datetime.fromisoformat(x["booking_start_date"])
        single = PC.ist_single_court(x["resource_name"])
        spieler = 2 if single else 4
        liste = PC.listenpreis(start, int(float(x["duration (Minuten)"])), single)
        kassiert = PC.parse_betrag(x["price"])
        anteil = round(liste / spieler, 2)
        if anteil <= 0:
            continue
        anzahl, _ = PC._rabatte_zerlegen(round(liste - kassiert, 2), anteil,
                                         spieler, start.date())
        passt = anzahl is not None
        je_court[x["resource_name"]][0 if passt else 1] += 1
        if not passt:
            schief.append((start, x["resource_name"], liste, kassiert, anteil,
                           x["payment_status"]))

    ok = sum(v[0] for v in je_court.values())
    bad = sum(v[1] for v in je_court.values())
    print(f"\n{ok + bad} bezahlte Buchungen · {ok} gehen auf · {bad} nicht")
    print(f"\n{'Court':<24}{'passt':>8}{'passt nicht':>13}")
    for c, (o, b) in sorted(je_court.items()):
        print(f"{c[:23]:<24}{o:>8}{b:>13}")
    if schief:
        print("\nDie Ausreisser:")
        for st, c, l, k, a, ps in schief[:20]:
            print(f"   {st:%d.%m. %H:%M} {c[:22]:<23} Liste {l:>7.2f} · "
                  f"kassiert {k:>7.2f} · Differenz {l - k:>7.2f} · "
                  f"Anteil {a:>6.2f} · {ps}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pruefen(sys.argv[1])
