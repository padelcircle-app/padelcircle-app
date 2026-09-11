# Was man über dieses System wissen muss

Notizen für den nächsten, der hier arbeitet — egal ob Mensch oder
Assistent, egal auf welchem Rechner. Alles hier ist an echten Daten
belegt, nicht vermutet. Wer es ändert, sollte vorher
`pruefung/regeln.py` laufen lassen.

## Der Aufbau

Eine einzige Datei, `PadelCircle.py`, läuft als Streamlit-App in der
Cloud. Die Daten liegen in Google Sheets, nicht im Repo.

**Zehn Module, keins ruft ein anderes auf.** Die Daten-Zentrale
schreibt, alle anderen lesen nur. Ein neues Modul kann man daneben
stellen, ohne Bestehendes anzufassen — diese Trennung sollte bleiben.

Blätter: `buchungen`, `checkins`, `playtomic_raw` (aus dem Import),
dazu die Handarbeit: `corrections` (erledigte Fälle), `name_mapping`,
`checkin_zuordnung` (Nachholungen), `freigaben`, `geschenke`,
`buchungs_luecken`, `rejected_matches`, `settings`, `customers`.

## Drei Geldbeträge, die nichts miteinander zu tun haben

| | | |
|---|---|---|
| `WELLPASS_RABATT` | **12,00 €** | was Playtomic dem Spieler abzieht. **Nur** dafür ist der Check-in-Abgleich da. |
| `WELLPASS_WERT` | **12,35 €** | 13,00 € brutto × 95 %, was EGYM dem Club zahlt. Monatsumsatz = gezählte Check-ins × 12,35 €. |
| Court-Preise | 28/32/36 · 18/22 | woraus sich der volle Personenanteil ergibt. |

Die ersten beiden waren einmal vermischt — dadurch war jeder
Euro-Betrag der App zu klein. **Nie wieder zusammenführen.**

## Der Abzug ist nicht über die Zeit konstant

Bis **03.08.2026** zog Playtomic **13,00 €** ab, seither **12,00 €**.

Massgeblich ist der Tag der **Buchung**, nicht der Spieltag. Man kann
zwei Wochen im Voraus reservieren — nach der Umstellung liefen also
noch Wochen lang Buchungen mit dem alten Abzug ein. In einer einzigen
Buchung am 30.07. stehen beide nebeneinander: 54,00 € Platzpreis,
29,00 € kassiert, das sind 13,00 € plus 12,00 €.

Deshalb probiert `abzug_kandidaten()` mehrere Werte, den des Spieltags
zuerst. Ein fester Wert wäre falsch.

## Die Preisliste

Ganzer Court je Stunde, angefangene Zeit anteilig:

| | 06–12 Uhr | 12–16 Uhr | ab 16 Uhr **und Wochenende ganztags** |
|---|---|---|---|
| Double (4 Spieler) | 28 € | 32 € | 36 € |
| Single (2 Spieler) | 18 € | 18 € | 22 € |

11:00–13:00 auf dem Double = 28 € + 32 € = 60 €.

Buchbar sind **nur 60 / 90 / 120 Minuten**. Das ist wichtig: mit
40 Minuten im Modell wäre Double abends 24 € ÷ 4 = 6,00 €, und vier
echte Wellpass-Spieler sähen aus wie Vollzahler. Je mehr Dauern
erlaubt sind, desto mehr Rabattpreise lassen sich als voller Anteil
"erklären".

**„Padel 6" ist der Single Court**, der heute „Single Court Padel 6"
heisst. Steht in `CONFIG["single_courts"]`.

Belege, dass die Liste stimmt: 142 von 142 Ganzplatz-Zahlungen treffen
exakt; 2143 von 2147 bezahlten Buchungen aus Juli und August gehen auf;
Christopher Gordys 8,00 € entsprechen dem, was Playtomic anzeigt.

## Was die Zahlungsdatei nicht hergibt

**Wer für einen anderen zahlt, verschluckt dessen Zeile.** Zahlt jemand
den 0-€-Wellpass-Platz eines Mitspielers, legt Playtomic für den
Begünstigten **keine** Zahlungszeile an. Lisa Schmiema spielte am
28.08. mit Wellpass, bezahlt von Aileen Täuber — in der Zahlungsdatei
kommt sie nicht vor. Nur der **Buchungsexport** nennt sie.

**Eine Zahlung kann mehrere Anteile abdecken.** Jonas.valentino zahlte
1,00 € — das sind zwei Anteile zu je 0,50 €, seiner und Katja Heros.

**Manches bleibt zweideutig.** Der Zahler hat zwei Gastplätze bezahlt,
einen voll und einen mit Rabatt: welcher Name zu welchem Platz gehört,
steht nirgends. Dafür gibt es in der Daten-Zentrale den Auswahlknopf
„Deine Entscheidung". **Nie raten** — drei solche Fälle in zwei
Monaten, das ist zumutbar.

## Regeln, die nie brechen dürfen

1. **Gleicher Nachname, anderer Vorname = zwei Menschen.** Kevin und
   Lina Schafran. Gilt beim Abgleich, beim Speichern einer Verknüpfung
   und beim Anwenden gespeicherter Verknüpfungen.
2. **Ein Check-in schliesst genau einen Fall.** EGYM vergütet einmal.
3. **Nachgeholt wird nach dem Spiel, nie davor.** Und eine Nachholung
   verfällt, sobald ihr Check-in am eigenen Spieltag gebraucht wird.
4. **Nie eine Zahl raten.** Lieber ein Hinweis mit Namen als ein
   erfundener Anspruch — der führt zu einer falschen WhatsApp.

## Fallen

- **Court leer lassen** bei Zeilen aus der Buchungsdatei.
  `_tage_nach_methode()` erkennt am gefüllten Court den alten
  Rechenweg; eine einzige solche Zeile schickt den ganzen Tag beim
  „Neu berechnen" über den alten Pfad, wo Spieler verloren gehen.
- **Nur Tage prüfen, für die auch Zahlungen da sind.** Ein
  Buchungsexport aus einem anderen Zeitraum erfand sonst 67 Ansprüche.
- **Neu berechnen nur mit abgelegter Buchungsdatei.** Die Tage werden
  ersetzt; ohne Buchungsdatei fielen fremdbezahlte Plätze und Korrekturen
  lautlos weg. Solche Tage werden deshalb übersprungen. Nachreichen geht
  mit „Nur Buchungsdatei ablegen". Alles, was vor `3f990a4` hochgeladen
  wurde, hat keine abgelegte Buchungsdatei.
- **Wer hat verknüpft, steht in `confirmed_by`.** „manuell" = Marcel,
  alles andere = die App. Die Anzeige muss das unterscheiden — „bestätigte
  Verknüpfung" für beides las sich, als hätte Marcel zugeordnet.
- **Summen sagen nichts.** Zwei Fehler haben sich hinter einer
  unveränderten Gesamtzahl versteckt. Immer alt gegen neu diffen und
  die geänderten **Zeilen** lesen.

## Was zuletzt offen war (Stand 11.09.2026)

In dieser Reihenfolge:

1. ✅ **„Nachgeholt — Fall schliessen" tut nichts.** Ursache: Hinfällig
   wurde je FALL entschieden. Hing an einem Fall noch eine alte,
   ungültige Zuordnung (Check-in am eigenen Tag gebraucht), hielt sie
   ihn offen — auch nachdem eine neue, gültige gespeichert war. Jetzt je
   Zuordnung; beim Nachholen fliegt die alte Zeile mit raus; Spinner.
2. **Drei von Hand geprüfte Tage** (Excel-Tage 29., 30., 31.08.,
   `Checkins_2026-08-2x-….xlsx` in `~/Downloads`). Links stimmte die App
   bis auf zwei Fälle. Erledigt:
   - ✅ Zweiter Scan derselben Person am selben Tag stand als überzählig
     (Berkay Kürekci; im Juli/August 22 solche).
   - ✅ Steffi Gengenbach 31.08.: ganz erstattet + verfallener Rest galt
     als „noch offen" — war storniert.
   - ✅ Maximilian Birk / Danja Mayer 31.08.: Birk bezahlte Danjas
     0-€-Wellpass-Platz mit, der Fall stand bei ihm. `wellpass_platz_beim_gast()`.
   - offen: Barbara Gekeler 30.08. spielte in Nico Brunos Buchung ohne
     Rabatt, steht aber als „keine passende Buchung". Braucht die
     Teilnehmer aus dem Buchungsexport → Punkt 4.
   - nicht lösbar: Maya Bitzer 30.08. war vermutlich der namenlose
     vierte Platz bei Lina/Kevin/Simon um 13:00. Aus den Daten nicht
     belegbar. Nico Bruno fehlte bei Marcel rechts — im frischen Lauf
     steht er korrekt da; live vermutlich schon zugeordnet.
3. ✅ **Name-Abgleich nur ab 95 % automatisch** (`3f990a4`).
   `AUTO_SCHWELLE_MIN = 95` — Tagesarbeit, Einstellungen und
   Sammelbestätigung gehen nie darunter. Beim Import werden die
   eindeutigen gleich übernommen, und gemerkte Verknüpfungen greifen
   direkt nach dem exakten Namen (`_checkin_ueber_verknuepfung`), also
   entsteht für sie kein offener Fall mehr. Unverändert bleibt die
   Schreibweisen-Erkennung im Import selbst (z. B. „Mika" ↔ „Mika
   Strele") — die hat Marcels Handprüfung bestätigt.
4. ✅ **„Neu berechnen"** (`3f990a4`). Geprüft: August importiert, veraltete
   Zeile eingeschleust, neu gerechnet → Zeile weg, Anzeige identisch. War für Zahlungstage kaputt:
   ohne Buchungsexport gerechnet, und weggefallene Zeilen blieben
   stehen. Jetzt: Blatt `buchungsexport` (lazy, ohne E-Mails) wird beim
   Import abgelegt, beim Neu-Rechnen mitgegeben, und die Tage werden per
   `tage_ersetzen_im_blatt()` in einem Schreibvorgang ersetzt — mit
   Schutz: lässt sich das Blatt nicht lesen, wird nichts geschrieben.
   Liegt der Export erst ab dem nächsten Upload vor: Juli/August einmal
   mit allen vier Dateien neu hochladen.
5. ✅ **Alte Tage sammelweise erledigen** (`3f990a4`). Daten-Zentrale
   → Bestand → „Alte Tage als erledigt markieren": bis zu einem Tag
   alle offenen Fälle mit Grund „Altbestand" schliessen, nur angehängt,
   jederzeit zurücknehmbar.
6. **Dashboard** (gebaut, in Prüfung). **Tag**: nur noch die Kennzahlen.
   **Auslastung** liest aus dem Blatt `buchungsexport` (ältere Tage
   weiter aus `buchungen` mit Court): Ø Double, Ø Single, 17–22 Uhr und
   eine Grafik je Uhrzeit. Juli + August gemessen: **Double Ø 42 %,
   Single Ø 72 %**; Double vormittags werktags 4–11 %, Single abends
   96–98 %. **Handlungsvorschläge** jetzt in Court-Minuten statt
   Zahlungszeilen, höchstens fünf: Rückgang (≥ 20 Punkte), Leerlauf
   (Vormittag < 15 %), schwächster Abend (< 60 %), Preis (Tagespreis
   trotz ≥ 75 %). Mit „Handlungsvorschläge" meinte Marcel diese Liste,
   nicht „Was als Nächstes dran ist" auf der Startseite — die bleibt.
7. Marcel schickt noch weitere Punkte.

Länger offen: Die Datei ist mit 13.700 Zeilen zu gross; beim nächsten
grösseren Modul in ein Modul je Datei plus Fundament schneiden.
