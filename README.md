# 🎧 Hörbuch Batch-Merger PRO V49

Ein kompaktes, praktisches Python-Tool für alle, die viele Hörspiel- und Hörbuch-CDs digitalisiert haben und daraus **saubere, gut sortierte MP3-Dateien** machen möchten.

> **Hinweis:** Dieses Projekt wurde mit Unterstützung von KI erstellt.

---

## 🎯 Warum gibt es dieses Tool?

Ich habe sehr viele Hörspiel-CDs importiert. Dabei entstehen typischerweise viele einzelne MP3-Dateien pro CD — oft mit unvollständigen oder uneinheitlichen ID3-Tags.

Das führt im Alltag zu zwei Problemen:

1. **Unübersichtliche Mediathek** — viele kleine Dateien pro Hörspiel machen die Sammlung schwerer zu pflegen.
2. **Falsche Reihenfolge im Audioplayer** — nicht jeder Player sortiert zuverlässig nach Tracknummer. Dadurch können Teile eines Hörspiels in der falschen Reihenfolge abgespielt werden.

Deshalb ist es für mich angenehmer, ein Hörspiel als **eine zusammengeführte MP3-Datei** zu haben. So bleibt die Reihenfolge garantiert korrekt.

Zusätzlich kann optional eine **CUE-Datei** erstellt werden. Damit können:

- geeignete Audioplayer die einzelnen Tracks bzw. Kapitel weiterhin erkennen,
- Tracks bei Bedarf übersprungen werden,
- die gemergte MP3 später bei Bedarf wieder in einzelne Tracks aufgeteilt werden.

Besonders praktisch ist das bei Serien wie **Die drei ???**, **Die drei ??? Kids** oder anderen Hörspielreihen mit vielen CDs und Folgen.

---

## ✨ Funktionen

- Mehrere MP3-Dateien zu einer Datei zusammenführen
- ID3-Tags direkt nach dem Merge schreiben
- Alben, CDs und Geschichten automatisch erkennen
- Tracknummern aus ID3-Tags oder Dateinamen lesen
- Vollständigkeitsprüfung der Tracknummern
- Warnung bei fehlenden oder springenden Tracks
- Unterstützung für mehrere Geschichten in einem Album
- Optionale CUE-Datei für Track-Navigation
- Verbesserte Adventskalender-Erkennung mit korrektem Intro und Outro
- Auswahl zwischen täglichen Advents-MP3s ohne CUE und einer gemeinsamen Album-MP3 mit CUE
- Coverbild übernehmen oder manuell setzen
- Originaldateien optional löschen
- Automatische Installation fehlender Python-Module beim Start
- Eigenständige GUI ohne ältere Merger-Version als Modul
- Asynchroner ID3-Batch mit Fortschrittsbalken, Statusanzeige und Abbrechen
- Verschiebbare und interaktiv veränderbare Tabellenspalten
- Drag & Drop für MP3s und Ordner in Hauptansicht und ID3-Batch
- Auswahlbeschränkung: Batch-Aktionen betreffen nur markierte Hörbücher
- Änderungen und Bereinigungen zunächst vormerken, erst mit Speichern schreiben
- Rückgängig für Vorschauen und gespeicherte Batch-Vorgänge
- Dateiname-zu-Tag und Tag-zu-Dateiname mit auswählbaren Mustern
- Gemeinsamer Artist und gemeinsames Genre für mehrere markierte Hörbücher
- Gründliche ID3-Bereinigung einschließlich Comment, Albumartist, APEv2-Extras und ID3v1
- CUE-Dateien beim Umbenennen berücksichtigen
- Einfache, übersichtliche GUI für Linux Mint

---

## 🖥️ GUI

![GUI](docs/gui.png)

*Die grafische Oberfläche bietet Drag & Drop, Albumgruppierung, Trackprüfung, asynchrone Batch-ID3-Bearbeitung und alle wichtigen Merge-Optionen auf einen Blick.*

> **Hinweis:** Wenn noch kein Screenshot unter `docs/gui.png` vorhanden ist, kannst du dort einfach einen Screenshot der GUI ablegen. Die README zeigt ihn dann automatisch an.

---

## 🎅 Adventskalender

Die Advents-/Weihnachts-Erkennung erkennt Hörspiele mit Begriffen wie **Advent**, **Weihnacht** oder **Bescherung**. Anschließend werden Dateien anhand von Mustern wie `Tag 01`, `Türchen 03`, `05 von 24` oder `07. Dezember` den passenden Adventstagen zugeordnet.

Vor dem ersten erkannten Tag liegende Dateien werden als **Intro** behandelt. Dateien nach dem letzten Tag werden als **Outro** behandelt.

Für deine Dateien bedeutet das beispielsweise:

```text
Track 1: O Geisterbaum Inhaltsangabe -> Intro
Track 2: O Geisterbaum Titelmusik -> Intro
Track 3 bis 117: Tag 01 bis Tag 24
Track 118: O Geisterbaum -> Outro
```

Intro und Outro werden nicht fälschlich auf eine lückenlose Tracknummerierung ab 1 geprüft. Dadurch erscheint keine irreführende Warnung über angeblich fehlende Tracknummern.

### Advents-Ausgabe wählen

Im Tab **Optionen** kannst du unter **„Adventskalender-Ausgabe“** wählen:

| Option | Ergebnis |
|---|---|
| **Täglich getrennte MP3s — ohne CUE** | Es entstehen separate MP3s für Intro, Tag 01 bis Tag 24 und Outro. Es wird keine CUE-Datei erstellt. |
| **Eine gemeinsame Album-MP3 mit einer CUE** | Es entsteht eine vollständige Album-MP3 mit einer CUE, die alle Tracks als Kapitel enthält. |

**Standard:** Täglich getrennte MP3s ohne CUE.

### Täglich getrennte MP3s

Bei dieser Einstellung werden beispielsweise folgende Dateien erstellt:

```text
Adventskalender - O Geisterbaum - Intro.mp3
Adventskalender - O Geisterbaum - Tag 01.mp3
Adventskalender - O Geisterbaum - Tag 02.mp3
...
Adventskalender - O Geisterbaum - Tag 24.mp3
Adventskalender - O Geisterbaum - Outro.mp3
```

Es entstehen **keine CUE-Dateien**. Das ist praktisch, wenn du die einzelnen Tage als eigene MP3s behalten möchtest, aber keine 24 zusätzlichen CUE-Dateien brauchst.

### Gemeinsame Album-MP3 mit CUE

Bei dieser Einstellung wird die komplette Adventsfolge zu einer MP3 zusammengeführt:

```text
Adventskalender - O Geisterbaum.mp3
Adventskalender - O Geisterbaum.cue
```

Die CUE enthält alle Kapitel in der richtigen Reihenfolge:

```text
Intro — O Geisterbaum Inhaltsangabe
Intro — O Geisterbaum Titelmusik
Tag 01 — Ein spezialgelagertes Wochenende
...
Tag 24 — Vier Zwei Vier
Outro — O Geisterbaum
```

Diese Option ist sinnvoll, wenn du im Audioplayer direkt zu einem bestimmten Adventstag springen möchtest.

---

## ⚙️ Optionen im Detail

| Option | Was macht sie? | Warum ist sie sinnvoll? |
|---|---|---|
| **Nach Album gruppieren** | Gruppiert geladene MP3s anhand ihres Albums. | Praktisch, wenn mehrere CDs oder Folgen gleichzeitig geladen werden. So erkennt das Tool, welche Dateien zusammengehören. |
| **Advent-/Weihnachts-Erkennung aktivieren** | Erkennt Advents- und Weihnachtshörspiele sowie die zugehörigen Tage. | Hilft bei Adventskalendern, saisonalen Folgen und Hörspielen mit Intro und Outro. |
| **Adventskalender-Ausgabe** | Wählt zwischen täglich getrennten MP3s ohne CUE und einer gemeinsamen Album-MP3 mit CUE. | Du kannst selbst entscheiden, ob du einzelne Tages-MP3s oder eine komplette Album-MP3 mit Kapiteln möchtest. |
| **MULTI-CD automatisch erkennen** | Erkennt Hörspiele, die aus mehr als einer CD bestehen, und führt die CDs zusammen — aber nur, wenn die Option aktiviert ist. | Perfekt, wenn ein Hörspiel über mehrere CDs verteilt ist und du am Ende **eine einzige MP3 pro Hörspiel** möchtest. |
| **Mehrere Geschichten pro Album trennen** | Erkennt zusammenhängende Blöcke mit demselben Geschichte-Titel innerhalb eines Albums. | Ideal bei CDs wie **Conni** oder **Bibi erzählt**, auf denen mehrere eigenständige Geschichten enthalten sind. Jede Geschichte erhält eine eigene MP3. |
| **CUE-Datei automatisch erstellen** | Erstellt optional eine CUE-Datei zur besseren Navigation. | Geeignete Audioplayer können damit Tracks oder Kapitel erkennen und gezielt anspringen. Bei täglich getrennten Advents-MP3s wird keine CUE erstellt. |

---

## 📚 Mehrere Geschichten trennen

Viele Hörspiel-Alben enthalten mehrere Geschichten auf einer CD. Beispiel:

```text
01 - Intro
02–13 - Conni kann nicht einschlafen
14–25 - Conni macht das Seepferdchen
26 - Outro
```

Mit der Option **„Mehrere Geschichten pro Album trennen“** erkennt das Programm zwei Geschichten und erstellt:

```text
Conni kann nicht einschlafen.mp3
Conni macht das Seepferdchen.mp3
```

Auch Formate wie diese werden erkannt:

```text
Das Baumhaus - Kapitel 1_Das Baumhaus
Ein verrücktes Picknick - Kapitel 2_Harmloser Beginn
Kapitel 06_Die verrückte Radwanderung
```

**Warum ist das wichtig?**  
Ohne diese Option würden alle Teile zu einer einzigen Datei gemerged. Mit der Option bleibt jede Geschichte eigenständig und sauber benannt.

---

## 🔍 Trackprüfung

Das Programm prüft automatisch, ob die Tracknummern innerhalb eines Albums oder einer Geschichte lückenlos sind.

Beispiel:

```text
Track 1 bis 13 vorhanden
Track 14 bis 25 vorhanden
```

Wenn eine Geschichte nicht bei Track 1 beginnt, aber innerhalb ihrer eigenen Nummerierung lückenlos ist, wird das **nicht** als Fehler gewertet. Fehlt hingegen mitten in einer Geschichte ein Track, wird das erkannt und gemeldet.

Intro und Outro bei Adventskalendern werden separat behandelt und nicht fälschlich auf eine lückenlose Tracknummerierung ab 1 geprüft.

---

## 🧹 ID3-Batch

Im Tab **„ID3-Batch“** kannst du einzelne MP3s oder komplette Ordner per Drag & Drop hinzufügen. Unterordner werden ebenfalls durchsucht; doppelte Dateien werden nicht erneut hinzugefügt.

Alle Dateien erscheinen in einer editierbaren Tabelle mit:

- Datei / Umbenennungsvorschau
- Artist
- Titel
- Album
- Track
- Disc
- Jahr
- Genre
- Cover
- Anzahl der Rest-Tags
- Status

Die Spalten können per Maus verschoben und in der Breite verändert werden. Die Dateispalte ist groß genug, um den Dateinamen lesbar zu halten; der vollständige Pfad ist als Tooltip verfügbar.

### Auswahl und Vormerken

Alle Batch-Aktionen betreffen ausschließlich die markierten Hörbücher. Mit **Strg** oder **Shift** können mehrere Hörbücher ausgewählt werden.

Änderungen und Bereinigungen werden zunächst nur vorgemerkt. Erst **„Änderungen speichern“** schreibt die ausgewählten Dateien.

Bei großen Sammlungen läuft das Einlesen, Speichern und Rückgängigmachen im Hintergrund. Fortschrittsbalken und Statuszeile zeigen beispielsweise:

```text
Tags lesen: 327 / 2.148 — Datei.mp3
Speichern: 18 / 42 — Album.mp3
```

Ein laufender Vorgang kann über **„Vorgang abbrechen“** sicher abgebrochen werden.

### Gemeinsame Felder

Wenn du mehrere Hörbücher markierst, kannst du mit **„Gemeinsamer Artist“** und **„Gemeinsames Genre“** allen ausgewählten Hörbüchern denselben Artist bzw. dasselbe Genre zuweisen.

- Leere Felder werden nicht geändert.
- Artist und Genre können unabhängig voneinander gesetzt werden.
- Die Änderung wird zunächst vorgemerkt und erst mit **„Änderungen speichern“** geschrieben.

---

## 🧹 Unnötige ID3-Tags löschen

Mit **„Unnötige ID3-Tags löschen“** wird die Bereinigung für die markierten Hörbücher vorgemerkt. Erst **„Änderungen speichern“** wendet sie an.

Behalten werden:

- Artist
- Titel
- Album
- Track
- Disc
- Jahr
- Genre
- Cover

Entfernt werden unter anderem:

- `COMM` / Comment
- `TPE2` / Albumartist
- weitere unnötige ID3v2-Frames
- unbekannte ID3-Frames
- unnötige APEv2-Tags
- ID3v1-Tags

Nach der Bereinigung prüft das Programm die Datei erneut. Bleiben unerwünschte Tags übrig, wird die Bereinigung als unvollständig gemeldet.

**Zusätzlich dauerhafte Backups (.id3backup)** ist standardmäßig deaktiviert. Du kannst die Option bei Bedarf vor dem Speichern aktivieren.

---

## 🔁 Dateiname zu Tag

Im Tab **„ID3-Batch“** wählst du ein Muster, um Dateinamen in ID3-Tags zu verwandeln.

Verfügbare Muster:

```text
%artist% - %album% - $num(%track%,2) - %title%
%track% %title%
%album%
%track%.%artist% - %title%
$num(%track%,3) %title%
```

Beispiel: Mit dem Standardmuster kann aus einem passend benannten Dateinamen die ID3-Tag-Struktur gelesen werden.

---

## ✏️ Tag zu Dateiname

Du kannst auch aus den vorhandenen ID3-Tags neue Dateinamen erzeugen. Dabei wird das aktuell gewählte Muster verwendet.

Wenn **„CUE-Datei berücksichtigen“** aktiv ist und eine passende CUE-Datei existiert, wird diese ebenfalls umbenannt und die `FILE`-Zeile in der CUE-Datei automatisch korrigiert.

**Wichtig:** Damit CUE und MP3 zusammenbleiben, müssen beide denselben Basisnamen haben, zum Beispiel:

```text
Adventskalender - O Geisterbaum.mp3
Adventskalender - O Geisterbaum.cue
```

Bei täglich getrennten Advents-MP3s wird keine CUE erstellt. Daher kann beim Umbenennen auch keine CUE-Datei beschädigt werden.

---

## 🧰 Installation

### Voraussetzungen

- Python 3
- ffmpeg

### Unter Linux Mint

```bash
sudo apt update
sudo apt install python3-pyqt5 python3-mutagen ffmpeg
```

### Starten

```bash
python3 hoerbuch_merger_V49.py
```

Die V49 ist eigenständig. Es wird keine ältere Merger-Pythondatei im selben Ordner benötigt.

---

## 📖 Nutzung

1. Programm starten.
2. MP3-Dateien per Drag & Drop oder Dateiauswahl laden.
3. Gewünschte Optionen aktivieren.
4. Bei Adventskalendern die gewünschte Ausgabe wählen: tägliche MP3s ohne CUE oder eine gemeinsame Album-MP3 mit CUE.
5. Merge starten.
6. Ergebnis prüfen.
7. Bei Bedarf ID3-Tags oder Cover anpassen.
8. Für viele bereits gemergte MP3s den Tab **„ID3-Batch“** verwenden.
9. Gewünschte Hörbücher markieren, Änderungen vornehmen und anschließend speichern.

---

## 🗂️ Projektstruktur

```text
hoerbuch_merger_V26.py
hoerbuch_merger_V37.py
hoerbuch_merger_V38.py
hoerbuch_merger_V40.py
hoerbuch_merger_V43.py
hoerbuch_merger_V46.py
hoerbuch_merger_V47.py
hoerbuch_merger_V49.py
README.md
LICENSE
requirements.txt
docs/gui.png
```

> **Hinweis:** `hoerbuch_merger_V49.py` ist die aktuelle empfohlene Version.

---

## 📄 Lizenz

MIT-Lizenz.

---

## 🤝 Beitrag

Pull Requests und Verbesserungen sind willkommen. Ziel ist ein möglichst einfaches, übersichtliches Tool für Hörspiel- und Hörbuchsammlungen.
