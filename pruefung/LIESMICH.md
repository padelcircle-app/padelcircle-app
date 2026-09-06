# Prüfung

Drei kleine Programme, die den Abgleich gegen **echte Exporte**
nachrechnen. Sie ändern nichts — sie rechnen und drucken.

Gedacht als Sicherheitsnetz: **vor** einer Änderung laufen lassen,
**danach** noch einmal. Verschiebt sich eine Zahl, hat die Änderung
mehr getan als beabsichtigt.

## Voraussetzungen

```bash
pip install -r requirements.txt
```

Kein Google-Zugang nötig, keine Zugangsdaten. `umgebung.py` ersetzt
Streamlit und Google Sheets durch Attrappen; die Rechenlogik aus
`PadelCircle.py` läuft unverändert.

## Die drei Programme

### `regeln.py` — zwei Sekunden, keine Dateien

```bash
python3 pruefung/regeln.py
```

Prüft die Regeln, die Geld kosten, wenn sie brechen: Geschwister
werden nie verknüpft, ein Check-in schliesst genau einen Fall, die
Preisliste rechnet die Zeitfenster richtig, und die 12,00 € Rabatt
bleiben von den 12,35 € Vergütung getrennt. **Nach jeder Änderung.**

### `abgleich.py` — der ganze Durchlauf

```bash
python3 pruefung/abgleich.py \
    ~/Downloads/zahlungen.csv \
    ~/Downloads/offene_posten.csv \
    ~/Downloads/checkins.csv \
    ~/Downloads/bookings-download.csv      # freiwillig
```

Druckt Tag für Tag: Ansprüche, wie viele einen Check-in haben, wie
viele offen bleiben. Die Spalte **Probe** prüft, ob die Zahlen in sich
aufgehen.

### `preise.py` — die Preisliste gegen jede Buchung

```bash
python3 pruefung/preise.py ~/Downloads/bookings-download.csv
```

Rechnet für jede bezahlte Buchung den Listenpreis und vergleicht ihn
mit dem, was Playtomic kassiert hat. Die Differenz muss eine Summe aus
Wellpass-Rabatten sein. Geht das bei vielen Buchungen nicht auf,
stimmt die Preisliste, die Court-Zuordnung oder der Abzug nicht.

## Die CSV-Dateien gehören NICHT ins Repo

Da stehen Namen, Telefonnummern und E-Mail-Adressen drin. Sie bleiben
lokal; `.gitignore` hält sie draussen. Die Programme lesen sie aus dem
Ordner, den man ihnen nennt.

## Was diese Programme schon gefunden haben

| | |
|---|---|
| **28.08.** | Drei Vollzahler standen als offene Fälle da. 8,00 € galt als Rabatt auf 20,00 € — 20,00 € kam im ganzen Bestand genau **einmal** vor. |
| **Zeitfenster-Versuch** | Eine Lösung dafür hätte **21 echte Ansprüche gelöscht**. Fiel im Vergleich vorher/nachher auf, bevor sie ausgeliefert wurde. |
| **Falscher Zeitraum** | Ein Buchungsexport aus einem anderen Monat erfand **67 Ansprüche**. Seitdem zählen nur Tage, für die auch Zahlungen da sind. |
| **Juli** | 255 von 907 Buchungen gingen nicht auf → der Abzug war damals 13,00 €, nicht 12,00 €. |
| **Padel 6** | 55 von 66 Buchungen dieses Platzes gingen nicht auf → er war früher der Single Court. |
