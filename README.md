# Hörbuch Batch-Merger PRO V26

Ein kompaktes, praktisches Werkzeug für alle, die viele MP3s zu einer gemergten Datei zusammenführen und die passenden ID3-Tags direkt setzen möchten.

Ich habe dieses Tool gebaut, weil ich meine **Die drei ???**-CDs eingelesen habe und sie danach als sauber gemergte MP3s haben wollte, ohne jedes Mal alles manuell nacharbeiten zu müssen. Genau dafür ist das Programm sehr übersichtlich, schnell zu bedienen und im Alltag sehr praktisch.

## Funktionen

- Mehrere MP3-Dateien zu einer Datei zusammenführen.
- ID3-Tags direkt nach dem Merge schreiben.
- Vorschlagslogik für **Die drei ???** / **Die Drei Fragezeichen** / **DDF**.
- Automatische Erkennung von `Folge xxx` als Track und Discnumber.
- Vorschläge für Artist, Title, Album, Track, Discnumber, Year und Genre.
- Coverbild übernehmen oder manuell setzen.
- CUE-Datei optional erzeugen.
- Originaldateien auf Wunsch löschen.
- Einfache GUI für Linux Mint.

## Warum dieses Tool praktisch ist

Wer viele Hörspiele digitalisiert oder archiviert, kennt das Problem: Dateien müssen sortiert, zusammengeführt und mit sauberen Metadaten versehen werden. Genau hier nimmt dir das Tool viel Handarbeit ab. Besonders bei Serien wie **Die drei ???** hilft die Vorschlagslogik, weil Folgennummern, Titel und Albumname direkt sinnvoll vorbelegt werden.

## Beispiele

### Beispiel 1

**Datei:** `Folge 240 und die schwarze Rose.mp3`

- Artist: `Die Drei Fragezeichen`
- Title: `und die schwarze Rose`
- Album: `240 und die schwarze Rose`
- Track: `240`
- Discnumber: `240`
- Genre: `Audiobook`

### Beispiel 2

**Datei:** `166 Und Die Brennende Stadt.mp3`

- Artist: `Die Drei Fragezeichen`
- Title: `Und Die Brennende Stadt`
- Album: `166 Und Die Brennende Stadt`
- Track: `166`
- Discnumber: `166`
- Genre: `Audiobook`

### Beispiel 3

**Datei:** `238 Falsche Schuld.mp3`

- Artist: `Die Drei Fragezeichen`
- Title: `Falsche Schuld`
- Album: `238 Falsche Schuld`
- Track: `238`
- Discnumber: `238`
- Genre: `Audiobook`

## Installation

### Voraussetzungen

- Python 3
- `ffmpeg`
- `PyQt5`
- `mutagen`

### Unter Linux Mint

```bash
sudo apt update
sudo apt install ffmpeg python3-pyqt5 python3-mutagen
```

## Starten

```bash
python3 hoerbuch_merger_V26.py
```

## Nutzung

1. MP3-Dateien per Drag & Drop oder Dateiauswahl laden.
2. Optional nach Album gruppieren lassen.
3. Merge starten.
4. Ergebnisdatei im ID3-Editor prüfen.
5. Bei Bedarf Titel, Album, Track und Cover anpassen.
6. ID3-Tags speichern.

## Projektstruktur

- `hoerbuch_merger_V26.py` – Hauptprogramm.
- `README.md` – Projektdokumentation.
- `LICENSE` – Lizenz.
- `requirements.txt` – Python-Abhängigkeiten.
- `.gitignore` – Nicht versionierte Dateien.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.

## Beitrag

Pull Requests und Verbesserungen sind willkommen. Ziel ist ein möglichst einfaches, übersichtliches Tool für Hörspiel- und Hörbuchsammlungen.
