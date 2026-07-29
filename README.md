# Padel Circle · Command Center

Zentrale Business-App für Padel Circle GmbH, Memmingen.
6 Indoor-Courts · Wasserwerkweg 59 · 87700 Memmingen

## Module

| Modul | Zweck |
|---|---|
| Daten-Zentrale | Playtomic- und Wellpass-Exporte einlesen und abgleichen |
| Business Dashboard | Umsatz, Zielfortschritt, Prognose, Auslastungs-Heatmap |
| WhatsApp Reminder | Wellpass-Vergesser anschreiben, einzeln oder als Sammelversand |
| Spieler & Community | Rangliste, Vielspieler, Rückholung inaktiver Spieler |
| Wellpass-Nachmeldung | CSV-Export für den EGYM-Nachmeldungs-Bot |
| Name-Abgleich | Playtomic ↔ Wellpass Namensvarianten zusammenführen |
| Einstellungen | Monatsziele, Spielersuche, Systemcheck |

## Dateien

```
PadelCircle.py        Die App
requirements.txt      Python-Pakete
secrets_vorlage.toml  Vorlage für Zugangsdaten (NICHT hochladen)
Setup-Anleitung.docx  Schritt-für-Schritt-Anleitung
.gitignore            Schutz vor versehentlichem Upload von Passwörtern
```

## Start

Lokal:
```bash
pip install -r requirements.txt
streamlit run PadelCircle.py
```

Streamlit Cloud: Repo verbinden, `PadelCircle.py` als Hauptdatei,
Secrets unter Settings eintragen.

## Konfiguration

Alles Anpassbare steht oben in `PadelCircle.py` im Block `CONFIG`.
Offene Punkte sind mit `← AUSFÜLLEN` markiert.

## Kennzahlen

- Wellpass: 13,00 € × 95 % = **12,35 €** pro Check-in
- Bearbeitungsgebühr bei vergessenem Check-in: **15,00 €**
- Double Court: 28 € (6–12) · 32 € (12–16) · 36 € (ab 16 / WE)
- Single Court: 18 € (bis 16) · 22 € (ab 16 / WE)

---

Once in. Never out.
