# 🎧 Hörbuch Batch-Merger PRO V43

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
- Coverbild übernehmen oder manuell setzen
- Originaldateien optional löschen
- Automatische Installation fehlender Python-Module beim Start
- Batch-ID3-Bereinigung für bereits gemergte MP3s
- Editierbare ID3-Tag-Tabelle
- Dateiname-zu-Tag und Tag-zu-Dateiname per Muster
- CUE-Dateien beim Umbenennen berücksichtigen
- Einfache, übersichtliche GUI für Linux Mint

---

## 🖥️ GUI

![GUI](docs/gui.png)

*Die grafische Oberfläche bietet Drag & Drop, Albumgruppierung, Trackprüfung, Batch-ID3-Bereinigung und alle wichtigen Merge-Optionen auf einen Blick.*

> **Hinweis:** Wenn noch kein Screenshot unter `docs/gui.png` vorhanden ist, kannst du dort einfach einen Screenshot der GUI ablegen. Die README zeigt ihn dann automatisch an.

---

## ⚙️ Optionen im Detail

| Option | Was macht sie? | Warum ist sie sinnvoll? |
|---|---|---|
| **Nach Album gruppieren** | Gruppiert geladene MP3s anhand ihres Albums. | Praktisch, wenn mehrere CDs oder Folgen gleichzeitig geladen werden. So erkennt das Tool, welche Dateien zusammengehören. |
| **Advent-/Weihnachts-Erkennung** | Erkennt spezielle Advents- und Weihnachtshörspiele, insbesondere bei **Die drei ???**. | Hilft bei saisonalen Folgen, die oft eine eigene Behandlung oder Kennzeichnung brauchen. |
| **MULTI-CD automatisch erkennen** | Erkennt Hörspiele, die aus mehr als einer CD bestehen, und führt die CDs zusammen — aber nur, wenn die Option aktiviert ist. | Perfekt, wenn ein Hörspiel über mehrere CDs verteilt ist und du am Ende **eine einzige MP3 pro Hörspiel** möchtest. So bleibt die Reihenfolge im Audioplayer immer korrekt. |
| **Mehrere Geschichten pro Album trennen** | Erkennt zusammenhängende Blöcke mit demselben Geschichte-Titel innerhalb eines Albums. | Ideal bei CDs wie **Conni** oder **Bibi erzählt**, auf denen mehrere eigenständige Geschichten enthalten sind. Jede Geschichte erhält eine eigene MP3. |
| **CUE-Datei automatisch erstellen** | Erstellt optional eine CUE-Datei zur besseren Navigation. | Geeignete Audioplayer können damit Tracks oder Kapitel erkennen und gezielt anspringen. |

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

---

## 🧹 Batch-ID3-Bereinigung

Im Tab **„ID3-Batch“** kannst du einen Ordner mit bereits gemergten MP3s laden.

Alle Dateien erscheinen in einer editierbaren Tabelle mit:

- Datei
- Artist
- Titel
- Album
- Track
- Disc
- Jahr
- Genre
- Cover
- Anzahl der Rest-Tags

Du kannst Felder direkt in der Tabelle ändern und mit **„Änderungen speichern“** schreiben.

Mit **„Unnötige ID3-Tags löschen“** werden bei allen geladenen MP3s die Rest-Tags entfernt. Behalten werden:

- Artist
- Titel
- Album
- Track
- Disc
- Jahr
- Genre
- Cover

Optional kannst du vorher ein Backup der MP3s als `.id3backup` erstellen.

---

## 🔁 Dateiname zu Tag

Im Tab **„ID3-Batch“** kannst du ein Muster verwenden, um Dateinamen in ID3-Tags zu verwandeln.

Beispiel:

```text
%artist% - %album% - $num(%track%,2) - %title%
```

Damit kann aus einem Dateinamen wie:

```text
Die Drei Fragezeichen - 001 Hexen gibt es doch - 01 - Hexen gibt es doch.mp3
```

die ID3-Tag-Struktur gelesen werden.

---

## ✏️ Tag zu Dateiname

Du kannst auch aus den vorhandenen ID3-Tags neue Dateinamen erzeugen.

Beispiel-Muster:

```text
%artist% - %album% - $num(%track%,2) - %title%
```

Das Programm erstellt dann einen sauberen, einheitlichen Dateinamen aus den Tags.

Wenn die Option **„CUE-Datei berücksichtigen“** aktiv ist und eine gleichnamige CUE-Datei existiert, wird diese ebenfalls umbenannt und die `FILE`-Zeile in der CUE-Datei automatisch korrigiert.

**Wichtig:** Damit CUE und MP3 zusammenbleiben, müssen beide denselben Basisnamen haben, zum Beispiel:

```text
001 Hexen gibt es doch.mp3
001 Hexen gibt es doch.cue
```

---

## 🧰 Installation

### Voraussetzungen

- Python 3
- ffmpeg

### Unter Linux Mint

```bash
sudo apt update
sudo apt install ffmpeg
```

### Python-Module

Die Datei `hoerbuch_merger_V43.py` prüft beim Start automatisch, ob `PyQt5` und `mutagen` vorhanden sind. Fehlende Pakete werden automatisch installiert.

---

## ▶️ Starten

```bash
python3 hoerbuch_merger_V43.py
```

---

## 📖 Nutzung

1. Programm starten.
2. MP3-Dateien per Drag & Drop oder Dateiauswahl laden.
3. Gewünschte Optionen aktivieren.
4. Merge starten.
5. Ergebnis prüfen.
6. Bei Bedarf ID3-Tags oder Cover anpassen.
7. Für viele bereits gemergte MP3s den Tab **„ID3-Batch“** verwenden.

---

## 🗂️ Projektstruktur

```text
hoerbuch_merger_V26.py
hoerbuch_merger_V37.py
hoerbuch_merger_V38.py
hoerbuch_merger_V40.py
hoerbuch_merger_V43.py
README.md
LICENSE
requirements.txt
docs/gui.png
```

> **Hinweis:** Die Datei `hoerbuch_merger_V43.py` wird manuell in das Repository hochgeladen.

---

## 📄 Lizenz

MIT-Lizenz.

---

## 🤝 Beitrag

Pull Requests und Verbesserungen sind willkommen. Ziel ist ein möglichst einfaches, übersichtliches Tool für Hörspiel- und Hörbuchsammlungen.