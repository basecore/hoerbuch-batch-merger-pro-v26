#!/usr/bin/env python3
"""Hörbuch Batch-Merger PRO V46, Standalone.
Complete merger/options/editor interface plus asynchronous ID3 batch editing.
All merger code is included in this file; no V43/V44/V45 module is loaded.
Back up your audio files and test on copies before processing a collection.
Python 3 + PyQt5 + mutagen + ffmpeg. License: MIT (same project).
"""
import sys

import os

import shutil

import subprocess

import re

import tempfile

import pwd

import grp

import stat

from collections import defaultdict

def install_dependencies():
    missing_packages = []
    if not shutil.which("ffmpeg"):
        missing_packages.append("ffmpeg")
    try:
        import PyQt5  # noqa: F401
    except ImportError:
        missing_packages.append("python3-pyqt5")
    try:
        import mutagen  # noqa: F401
    except ImportError:
        missing_packages.append("python3-mutagen")
    if missing_packages:
        print("Installiere fehlende Abhängigkeiten für Linux Mint...")
        try:
            cmd = ["pkexec", "apt-get", "install", "-y"] + missing_packages
            subprocess.run(cmd, check=True)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError:
            print("Fehler bei der Installation.")
            sys.exit(1)

install_dependencies()

runtime_dir = os.environ.get('XDG_RUNTIME_DIR')

if not runtime_dir:
    runtime_dir = f'/tmp/runtime-{os.getuid()}'
    os.environ['XDG_RUNTIME_DIR'] = runtime_dir
    try:
        os.makedirs(runtime_dir, mode=0o700, exist_ok=True)
        os.chmod(runtime_dir, 0o700)
    except Exception:
        pass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QProgressBar, QTextEdit, QFileDialog,
    QLabel, QCheckBox, QRadioButton, QButtonGroup, QGroupBox,
    QAbstractItemView, QMessageBox, QMenu, QTabWidget,
    QFormLayout, QLineEdit, QListWidget, QListWidgetItem
)

from PyQt5.QtCore import Qt, QThread, pyqtSignal

from PyQt5.QtGui import QColor, QPixmap

from mutagen.easyid3 import EasyID3

from mutagen.mp3 import MP3

from mutagen.id3 import ID3, APIC, ID3NoHeaderError

EDITABLE_ID3_FIELDS = {
    'artist': 'Artist',
    'title': 'Title',
    'album': 'Album',
    'discnumber': 'Discnumber',
    'tracknumber': 'Track',
    'date': 'Year',
    'genre': 'Genre',
    'APIC': 'Coverbild',
}

def extract_advent_day_helper(filename, title):
    text_to_search = f"{filename} {title}".lower()
    match_dez = re.search(r'(\d{1,2})[\._\s]*dez(?:ember|\.|_|\b)', text_to_search)
    if match_dez:
        return f"Tag {match_dez.group(1).zfill(2)}"
    match_tag = re.search(r'(?:tag|türchen|tuerchen)[\s_]*(\d{1,2})', text_to_search)
    if match_tag:
        return f"Tag {match_tag.group(1).zfill(2)}"
    match_von24 = re.search(r'(\d{1,2})[\s_]*von[\s_]*24', text_to_search)
    if match_von24:
        return f"Tag {match_von24.group(1).zfill(2)}"
    match_under = re.search(r'_(0[1-9]|1[0-9]|2[0-4])_', text_to_search)
    if match_under:
        return f"Tag {match_under.group(1).zfill(2)}"
    match_dash = re.search(r'\s-\s(0[1-9]|1[0-9]|2[0-4])(?:[^\d]|$)', text_to_search)
    if match_dash:
        return f"Tag {match_dash.group(1).zfill(2)}"
    return None

def get_short_story_keyword(album_name):
    name_lower = album_name.lower()
    keywords = ["kurzgeschichten", "dreitag", "geisterlampe", "schwarze tag", "zeitgeist"]
    for k in keywords:
        if k in name_lower:
            return k
    return None

def suggest_ddf_metadata(path):
    filename = os.path.basename(path)
    stem = os.path.splitext(filename)[0]
    raw = stem.replace('_', ' ').replace('.', ' ').replace('-', ' ')
    artist = 'Die Drei Fragezeichen'
    genre = 'Audiobook'
    track = ''
    disc = '1'
    title = stem.strip()
    patterns = [
        r'^(?:folge\s*)?(\d{1,4})\s+(.*)$',
        r'^(?:ddf\s*)?(?:folge\s*)?(\d{1,4})\s*[-_. ]\s*(.*)$',
        r'^(\d{1,4})\s+(.*)$',
    ]
    for pattern in patterns:
        m = re.match(pattern, raw, re.IGNORECASE)
        if m:
            track = m.group(1).strip()
            title = m.group(2).strip()
            disc = track
            break
    if not track:
        m = re.search(r'(?:folge|fol\.|track|cd)\s*(\d{1,4})', raw, re.IGNORECASE)
        if m:
            track = m.group(1).strip()
            disc = track
    year = ''
    y = re.search(r'(19|20)\d{2}', raw)
    if y:
        year = y.group(0)
    album = f'{track} {title}'.strip() if track else title
    return {'artist': artist, 'title': title, 'album': album, 'disc': disc, 'track': track, 'year': year, 'genre': genre}

def ddf_examples_text():
    return (
        'Beispiele: 166 Und Die Brennende Stadt.mp3 -> Artist: Die Drei Fragezeichen, Title: Und Die Brennende Stadt, Album: 166 Und Die Brennende Stadt, Track/Disc: 166 | '
        '238 Falsche Schuld.mp3 -> Artist: Die Drei Fragezeichen, Title: Falsche Schuld, Album: 238 Falsche Schuld, Track/Disc: 238'
    )

def extract_short_story_name(title, filename):
    fn_clean = filename.replace('_', ' ')
    title_clean = title.replace('_', ' ')
    match_teil = re.search(r'(?:Die drei\s*-\s*)?(?:(\d{2})\s*-\s*)?(.+?)\s*\(?Teil\s*\d+\)?', fn_clean, re.IGNORECASE)
    res = ""
    if match_teil:
        res = match_teil.group(2).strip()
        num_prefix = match_teil.group(1)
        if num_prefix:
            res = f"{num_prefix} - {res}"
    else:
        match_teil_title = re.search(r'(?:(\d{2})\s*-\s*)?(.+?)(?:\s*\(?Teil\s*\d+\)?)?$', title_clean, re.IGNORECASE)
        if match_teil_title:
            res = match_teil_title.group(2).strip()
            num_prefix = match_teil_title.group(1)
            if num_prefix:
                res = f"{num_prefix} - {res}"
    if res:
        res = re.sub(r'^Die drei.*?\s+-\s+', '', res, flags=re.IGNORECASE)
        return res.strip()
    match_colon = re.search(r':\s*(.+?)\s*\(Teil', fn_clean, re.IGNORECASE)
    if match_colon:
        return match_colon.group(1).strip()
    match_number_dash = re.search(r'^(\d{2}\s*-\s*[^(]+)', fn_clean)
    if match_number_dash:
        res = match_number_dash.group(1).strip()
        res = re.sub(r'^Die drei.*?\s+-\s+', '', res, flags=re.IGNORECASE)
        return res.strip()
    return "Unbekannte Kurzgeschichte"

def detect_missing_discs(file_dicts):
    valid_tracks = [pf['track'] for pf in file_dicts if pf['track'] != 999]
    if len(valid_tracks) > 1 and len(valid_tracks) == len(set(valid_tracks)):
        def track_sort_key(pf):
            return (pf['track'] if pf['track'] != 999 else 9999, pf['filename'])
        file_dicts.sort(key=track_sort_key)
        for pf in file_dicts:
            pf['disc'] = 1
        return False

    def natural_sort_key(pf):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', pf['path'])]

    file_dicts.sort(key=natural_sort_key)
    auto_disc = 1
    prev_track = -1
    prev_teil = -1
    triggered = False
    for pf in file_dicts:
        curr_track = pf['track']
        match = re.search(r'(?:Teil|Folge|Track|Pt|Part)[\s_.-]*(\d+)', pf['filename'], re.IGNORECASE)
        if not match:
            match = re.search(r'(\d+)', pf['filename'])
        curr_teil = int(match.group(1)) if match else -1
        track_drop = (prev_track != -1 and curr_track != 999 and prev_track != 999 and curr_track < prev_track)
        teil_drop = (prev_teil != -1 and curr_teil != -1 and curr_teil < prev_teil)
        if (track_drop and curr_track <= 3) or (teil_drop and curr_teil <= 3):
            auto_disc += 1
            triggered = True
        pf['disc'] = auto_disc
        if curr_track != 999:
            prev_track = curr_track
        if curr_teil != -1:
            prev_teil = curr_teil
    return triggered

def sanitize_cue_value(value):
    value = (value or '').replace('\r', ' ').replace('\n', ' ').strip()
    return value.replace('"', "'")

def format_cue_timestamp(seconds):
    total_frames = max(0, int(round(seconds * 75)))
    minutes = total_frames // (75 * 60)
    remainder = total_frames % (75 * 60)
    secs = remainder // 75
    frames = remainder % 75
    return f"{minutes:02d}:{secs:02d}:{frames:02d}"

def extract_cover_bytes(path):
    try:
        tags = ID3(path)
        for tag in tags.values():
            if isinstance(tag, APIC):
                return {'mime': tag.mime, 'data': tag.data, 'type': tag.type, 'desc': tag.desc}
    except Exception:
        pass
    return None

def collect_group_defaults(items):
    sorted_items = sorted(items, key=lambda x: (x['track'] if x['track'] != 999 else 9999, x['filename'].lower()))
    first = sorted_items[0]
    return {
        'artist': first.get('artist', ''),
        'title': first.get('album', '') or first.get('title', ''),
        'album': first.get('album', ''),
        'discnumber': str(first.get('disc', 1) or 1),
        'tracknumber': '1',
        'date': first.get('year', ''),
        'genre': first.get('genre', ''),
        'cover': extract_cover_bytes(first['path'])
    }

def build_cue_track_title(file_path, fallback_title, index):
    title = sanitize_cue_value(fallback_title)
    if title:
        return title
    stem = os.path.splitext(os.path.basename(file_path))[0]
    stem = re.sub(r'[_]+', ' ', stem).strip()
    return sanitize_cue_value(stem or f'Track {index:02d}')

def build_cue_content(output_file, album_title, performer, file_items, sequential=True, include_track_performer=True):
    cue_lines = [
        f'PERFORMER "{sanitize_cue_value(performer or "Unbekannter Interpret")}"',
        f'TITLE "{sanitize_cue_value(album_title)}"',
        f'FILE "{os.path.basename(output_file)}" MP3'
    ]
    running_seconds = 0.0
    for idx, item in enumerate(file_items, start=1):
        track_no = idx if sequential else (item['track'] if item['track'] != 999 else idx)
        track_title = build_cue_track_title(item['path'], item['title'], idx)
        performer_line = sanitize_cue_value(item['artist'] or performer or 'Unbekannter Interpret')
        try:
            duration = MP3(item['path']).info.length
        except Exception:
            duration = 0.0
        cue_lines.append(f'  TRACK {track_no:02d} AUDIO')
        cue_lines.append(f'    TITLE "{track_title}"')
        if include_track_performer:
            cue_lines.append(f'    PERFORMER "{performer_line}"')
        cue_lines.append(f'    INDEX 01 {format_cue_timestamp(running_seconds)}')
        running_seconds += duration
    return '\n'.join(cue_lines) + '\n'

def get_id3_tag_lines(path):
    lines = []
    try:
        tags = ID3(path)
        for key in sorted(tags.keys()):
            frame = tags[key]
            prefix = key[:4]
            if prefix == 'APIC':
                size = len(getattr(frame, 'data', b''))
                mime = getattr(frame, 'mime', '?')
                desc = getattr(frame, 'desc', '')
                lines.append(f"{key}: Coverbild ({mime}, {size} Bytes, desc='{desc}')")
            else:
                value = str(frame)
                if len(value) > 180:
                    value = value[:180] + ' ...'
                lines.append(f"{key}: {value}")
    except Exception as e:
        lines.append(f"Keine ID3-Tags lesbar: {e}")
    return lines

def build_track_check_summary(data_structure, limit=3):
    entries = []
    for base_key, items in data_structure.items():
        ok, msg = check_track_completeness(items)
        name = os.path.basename(base_key) if os.path.isabs(base_key) else str(base_key)
        short_msg = msg.replace('Tracks vollständig: ', '').replace('Tracks unvollständig: ', '')
        entries.append(f"{name}: {short_msg}")
    if not entries:
        return 'Track-Check: Noch keine Daten geladen'
    if len(entries) <= limit:
        return 'Track-Check: ' + ' | '.join(entries)
    return f"Track-Check: {len(entries)} Hörbücher geladen. Details siehe Log oder Baumansicht."

def ensure_id3(path):
    try:
        audio = MP3(path)
        if audio.tags is None:
            audio.add_tags()
            audio.save()
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()
        audio.save()

def write_selected_id3_tags(path, values, enabled_fields, cover_mode='none', cover_bytes=None, cover_path=''):
    ensure_id3(path)
    easy = EasyID3(path)
    for key in ['artist', 'title', 'album', 'discnumber', 'tracknumber', 'date', 'genre']:
        try:
            if key in easy:
                del easy[key]
        except Exception:
            pass
    for key in ['artist', 'title', 'album', 'discnumber', 'tracknumber', 'date', 'genre']:
        if key in enabled_fields and values.get(key, '').strip():
            easy[key] = [values[key].strip()]
    easy.save(v1=0)

    id3 = ID3(path)
    if 'APIC' in enabled_fields:
        if cover_mode == 'file' and cover_path and os.path.exists(cover_path):
            id3.delall('APIC')
            with open(cover_path, 'rb') as fh:
                data = fh.read()
            mime = 'image/jpeg' if cover_path.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
            id3.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=data))
        elif cover_mode == 'bytes' and cover_bytes:
            id3.delall('APIC')
            id3.add(APIC(encoding=3, mime=cover_bytes['mime'], type=cover_bytes['type'], desc=cover_bytes['desc'], data=cover_bytes['data']))
        else:
            pass
    else:
        id3.delall('APIC')
    id3.save(v1=0,v2_version=3)

def ensure_normal_permissions(path):
    try:
        current_uid = os.getuid()
        current_gid = os.getgid()
        for root, dirs, files in os.walk(path):
            try:
                os.chown(root, current_uid, current_gid)
            except Exception:
                pass
            try:
                os.chmod(root, 0o755)
            except Exception:
                pass
            for d in dirs:
                full = os.path.join(root, d)
                try:
                    os.chown(full, current_uid, current_gid)
                except Exception:
                    pass
                try:
                    os.chmod(full, 0o755)
                except Exception:
                    pass
            for f in files:
                full = os.path.join(root, f)
                try:
                    os.chown(full, current_uid, current_gid)
                except Exception:
                    pass
                try:
                    os.chmod(full, 0o644)
                except Exception:
                    pass
    except Exception:
        pass

def format_owner_group_mode(path):
    try:
        st = os.stat(path)
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        mode = stat.S_IMODE(st.st_mode)
        return owner, group, oct(mode)
    except Exception:
        return '?', '?', '?'

def collect_permission_issues(target_dir, input_files):
    issues = []
    checked = set()

    def check_path(path, need_write=False, need_read=False):
        if not path or path in checked or not os.path.exists(path):
            return
        checked.add(path)
        owner, group, mode = format_owner_group_mode(path)
        problems = []
        if need_write and not os.access(path, os.W_OK):
            problems.append('nicht schreibbar')
        if need_read and not os.access(path, os.R_OK):
            problems.append('nicht lesbar')
        if owner == 'root' and os.getuid() != 0:
            problems.append('Besitzer=root')
        if problems:
            issues.append(f"{path} -> {', '.join(problems)} | owner={owner}:{group} mode={mode}")

    probe_dir = target_dir
    while probe_dir and not os.path.exists(probe_dir):
        parent = os.path.dirname(probe_dir)
        if parent == probe_dir:
            break
        probe_dir = parent
    if probe_dir:
        check_path(probe_dir, need_write=True, need_read=True)

    for f in input_files:
        check_path(f, need_read=True)
        parent = os.path.dirname(f)
        check_path(parent, need_read=True)

    return issues

def export_cover_file(output_base_no_ext, cover_mode='none', cover_bytes=None, cover_path=''):
    try:
        if cover_mode == 'file' and cover_path and os.path.exists(cover_path):
            ext = os.path.splitext(cover_path)[1].lower() or '.jpg'
            target = output_base_no_ext + ext
            shutil.copy2(cover_path, target)
            return target
        if cover_mode == 'bytes' and cover_bytes and cover_bytes.get('data'):
            data = cover_bytes['data']
            ext = '.jpg'
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                ext = '.png'
            target = output_base_no_ext + ext
            with open(target, 'wb') as f:
                f.write(data)
            return target
    except Exception:
        return None
    return None

class BatchDragDropTree(QTreeWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels(["Hörbuch / Datei", "Track", "Kategorie/Status"])
        self.setColumnWidth(0, 560)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 240)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
        self.setStyleSheet("QTreeWidget { background-color:#2b2b2b; color:#e0e0e0; font-size:14px; border:1px solid #555; } QTreeWidget::item:selected { background-color:#3d70b2; }")

    def open_menu(self, position):
        item = self.itemAt(position)
        if not item or item.parent() is not None:
            return
        base_key = item.data(0, Qt.UserRole)
        menu = QMenu()
        a_adv = menu.addAction("🎅 Als Adventskalender sortieren")
        a_adv.triggered.connect(lambda: self.parent_window.force_advent_mode(base_key))
        a_short = menu.addAction("📚 Als Kurzgeschichten sortieren")
        a_short.triggered.connect(lambda: self.parent_window.force_short_story_mode(base_key))
        a_cd = menu.addAction("💿 Als Mehrteilige CD-Folge sortieren")
        a_cd.triggered.connect(lambda: self.parent_window.force_multicd_mode(base_key))
        menu.addSeparator()
        a_norm = menu.addAction("🎧 Als normales Hörspiel sortieren")
        a_norm.triggered.connect(lambda: self.parent_window.force_normal_mode(base_key))
        menu.exec_(self.viewport().mapToGlobal(position))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.parent_window.process_dropped_urls(event.mimeData().urls())
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

from pathlib import Path
import copy
import hashlib
import uuid
import time
from mutagen import File as MutagenFile
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QSettings, QTimer
from PyQt5.QtWidgets import QTableView, QHeaderView


def first_tag_value(tags, key, default=''):
    values = tags.get(key, []) if tags else []
    if not values:
        return default
    value = values[0]
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else str(value)

def parse_track_number(value):
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''
    text = str(value or '').strip()
    match = re.search(r'(?:track|tracknr|tracknummer|titel|nr\.?|no\.?)[\s_.:-]*(\d{1,4})', text, re.I)
    if not match:
        match = re.search(r'(?<!\d)(\d{1,4})(?:\s*/\s*\d{1,4})?(?!\d)', text)
    number = int(match.group(1)) if match else 999
    return number if number > 0 else 999

def track_number_from_filename(path):
    return parse_track_number(os.path.splitext(os.path.basename(path))[0])

def normalize_story_title(title, filename):
    text = (title or os.path.splitext(os.path.basename(filename))[0]).strip()
    text = re.sub(r'^\s*\d{1,4}\s*[.\-_)]?\s*', '', text)
    match = re.match(r'^(.*?)\s*[-–]\s*Kapitel\s*\d+\s*[_:]?\s*.*$', text, re.I)
    if match:
        text = match.group(1)
    text = re.sub(r'^\s*(?:kapitel|track|titel|teil)\s*\d{1,4}\s*[_:.]?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*[-–:]\s*(?:teil|kapitel|track|titel)\s*\d{1,4}\s*$', '', text, flags=re.I)
    text = re.sub(r'\s+(?:teil|kapitel|track|titel)\s*\d{1,4}\s*$', '', text, flags=re.I)
    text = re.sub(r'\s*\(\s*folge\s*\d{1,4}\s*\)\s*$', '', text, flags=re.I)
    text = re.sub(r'\s*\[\s*bonus\s*\]\s*$', '', text, flags=re.I)
    return re.sub(r'\s+', ' ', text).strip(' -_:')

def detect_story_segments(items):
    if len(items) < 4:
        return False
    runs = []
    for item in items:
        story = normalize_story_title(item.get('title', ''), item.get('filename', '')) or 'Unbenannte Geschichte'
        if runs and runs[-1][0] == story:
            runs[-1][1].append(item)
        else:
            runs.append([story, [item]])
    story_runs = [run for run in runs if len(run[1]) >= 2]
    if len(story_runs) < 2:
        return False
    assigned = 0
    for story, story_items in runs:
        if len(story_items) >= 2:
            assigned += 1
            target_story = story
        else:
            target_story = story_runs[0][0] if assigned == 0 else story_runs[-1][0]
        for item in story_items:
            item['category'] = target_story.replace('/', '-').replace(':', ' -')
            item['story_split'] = True
    return True

def safe_meta_from_file(path):
    meta = dict(album='Unbekanntes_Album', title='', artist='', track=999, disc=1,
                year='', genre='', filename=os.path.basename(path), path=path,
                category='-', story_split=False, tag_error='', cd_in_path=False)
    try:
        audio = MutagenFile(path, easy=True)
        tags = audio.tags if audio else None
        if tags:
            for field, key in [('album','album'),('title','title'),('artist','artist'),('year','date'),('genre','genre')]:
                meta[field] = first_tag_value(tags, key, meta[field])
            meta['track'] = parse_track_number(tags.get('tracknumber'))
            disc = parse_track_number(tags.get('discnumber'))
            meta['disc'] = disc if disc != 999 else 1
    except Exception as error:
        meta['tag_error'] = str(error)
    if meta['track'] == 999 or meta['disc'] == 1:
        try:
            tags = ID3(path)
            if meta['track'] == 999 and tags.get('TRCK'):
                meta['track'] = parse_track_number(tags['TRCK'].text)
            if meta['disc'] == 1 and tags.get('TPOS'):
                disc = parse_track_number(tags['TPOS'].text)
                meta['disc'] = disc if disc != 999 else 1
        except Exception:
            pass
    if meta['track'] == 999:
        meta['track'] = track_number_from_filename(path)
    if meta['disc'] == 1:
        match = re.search(r'CD[\s_.-]*(\d+)', path, re.I)
        if match:
            meta['disc'], meta['cd_in_path'] = int(match.group(1)), True
    return meta

def check_track_completeness(items, require_start_from_one=True):
    numbers = sorted({item['track'] for item in items if isinstance(item['track'], int) and 0 < item['track'] != 999})
    if not numbers:
        return False, 'Keine brauchbaren Tracknummern vorhanden.'
    start = 1 if require_start_from_one else numbers[0]
    missing = [n for n in range(start, numbers[-1]+1) if n not in numbers]
    if missing:
        return False, 'Tracks unvollständig: Fehlende Tracknummern ' + str(missing)
    return True, 'Tracks vollständig: %s bis %s vorhanden.' % (numbers[0], numbers[-1])

def repair_cue_file(cue_path):
    mp3 = os.path.splitext(cue_path)[0]+'.mp3'
    if not os.path.isfile(mp3):
        return False, 'Keine passende MP3 gefunden'
    data = Path(cue_path).read_bytes()
    encoding = 'utf-8'
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        encoding, text = 'cp1252', data.decode('cp1252')
    matches = list(re.finditer(r'(?im)^[ \t]*FILE\s+"([^"]+)"\s+MP3[ \t]*\r?$', text))
    if len(matches) != 1:
        raise ValueError('CUE benötigt genau eine FILE-Zeile: '+cue_path)
    match = matches[0]
    name = os.path.basename(mp3)
    if match.group(1) == name:
        return False, name
    backup = unique_backup_path(cue_path+'.backup')
    shutil.copy2(cue_path, backup)
    Path(cue_path).write_bytes((text[:match.start(1)]+name+text[match.end(1):]).encode(encoding))
    return True, name

def repair_cue_files_in_folder(folder):
    repaired, skipped, logs = 0, 0, []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith('.cue'):
            continue
        try:
            changed, info = repair_cue_file(os.path.join(folder,name))
            repaired += int(changed)
            skipped += int(not changed)
            logs.append(('Repariert: ' if changed else 'Unverändert: ')+name+' ('+info+')')
        except Exception as error:
            skipped += 1
            logs.append('Fehler: '+name+': '+str(error))
    return repaired, skipped, logs


# V46: cached batch records and transactional, selection-only file operations.
BATCH_FIELDS = ('artist','title','album','track','disc','year','genre')
BATCH_KEYS = ('artist','title','album','tracknumber','discnumber','date','genre')
BATCH_FRAMES = ('TPE1','TIT2','TALB','TRCK','TPOS','TDRC','TCON')
BATCH_KEEP = {'TPE1','TIT2','TALB','TRCK','TPOS','TDRC','TYER','TDAT','TIME','TCON','APIC'}
APE_KEEP = {'artist','title','album','track','tracknumber','disc','discnumber','year','date','genre'}
PATTERN_TOKEN = re.compile(r'\$num\(\s*%(\w+)%\s*,\s*(\d+)\s*\)|%(\w+)%')

class BatchCancelled(Exception):
    pass

def unique_backup_path(path):
    candidate, counter = path, 1
    while os.path.lexists(candidate):
        candidate = path+'.'+str(counter)
        counter += 1
    return candidate

def batch_pattern_parts(pattern):
    position, found = 0, False
    for match in PATTERN_TOKEN.finditer(pattern):
        literal = pattern[position:match.start()]
        if '%' in literal or '$' in literal:
            raise ValueError('Ungültiges Muster vor '+match.group())
        yield literal, None, None
        field = match.group(1) or match.group(3)
        width = int(match.group(2)) if match.group(2) else None
        if field not in BATCH_FIELDS or (width is not None and not 1<=width<=12):
            raise ValueError('Unbekanntes Feld oder ungültige Zahlenbreite: '+match.group())
        yield '', field, width
        found, position = True, match.end()
    literal = pattern[position:]
    if not found or '%' in literal or '$' in literal:
        raise ValueError('Bitte ein gültiges Muster mit Platzhaltern eingeben.')
    yield literal, None, None

def batch_parse_filename(path, pattern):
    fields, pieces = [], []
    for literal, field, width in batch_pattern_parts(pattern):
        if field is None:
            pieces.append(re.escape(literal))
        else:
            fields.append(field)
            pieces.append(r'(\d+)' if width or field in ('track','disc','year') else r'(.*?)')
    match = re.fullmatch(''.join(pieces), Path(path).stem, re.I)
    if not match:
        raise ValueError('Dateiname passt nicht zum Muster: '+Path(path).name)
    result = {}
    for field, value in zip(fields,match.groups()):
        value = value.strip()
        if field in result and result[field]!=value:
            raise ValueError('Widersprüchliche Werte für '+field)
        result[field] = value
    return result

def batch_render_filename(row, pattern):
    result = ''
    for literal, field, width in batch_pattern_parts(pattern):
        value = str(row.get(field,'')).strip() if field else literal
        if width:
            value = value.split('/',1)[0]
            if not value.isdigit():
                raise ValueError('$num benötigt eine Zahl für '+field)
            value = str(int(value)).zfill(width)
        result += value
    result = re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',result).strip(' .')
    if not result:
        raise ValueError('Leerer Dateiname.')
    return result+'.mp3'

def batch_ape_extras(path):
    from mutagen.apev2 import APEv2, APENoHeaderError
    try:
        ape = APEv2(path)
    except APENoHeaderError:
        return []
    return [key for key in ape.keys() if key.lower() not in APE_KEEP and not key.lower().startswith('cover art (')]

def batch_read_record(path, uid=None):
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    row = dict(uid=uid or uuid.uuid4().hex,path=os.path.abspath(path),pending_name='',
               cleanup=False,cover_path='',dirty=False,enabled=None)
    for field,frame in zip(BATCH_FIELDS,BATCH_FRAMES):
        value = tags.get(frame)
        row[field] = str(value.text[0]) if value is not None and getattr(value,'text',None) else ''
    row['realpath'] = os.path.realpath(path)
    row['has_cover'] = bool(tags.getall('APIC'))
    row['extras'] = [key for key in tags.keys() if key[:4] not in BATCH_KEEP]
    row['extras'] += ['Unbekannter ID3-Frame']*len(tags.unknown_frames)
    row['ape_extras'] = batch_ape_extras(path)
    with open(path,'rb') as stream:
        stream.seek(0,os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0,size-128))
        row['id3v1'] = size>=128 and stream.read(3)==b'TAG'
    row['extra_count'] = len(row['extras'])+len(row['ape_extras'])+int(row['id3v1'])
    return row

def batch_hash(path, cancelled=lambda:False):
    value = hashlib.sha256()
    with open(path,'rb') as stream:
        while True:
            if cancelled():
                raise BatchCancelled()
            data = stream.read(1024*1024)
            if not data:
                break
            value.update(data)
    return value.hexdigest()

def batch_copy(source,target,cancelled=lambda:False):
    created=False
    try:
        with open(source,'rb') as inp, open(target,'xb') as out:
            created=True
            while True:
                if cancelled(): raise BatchCancelled()
                data=inp.read(1024*1024)
                if not data: break
                out.write(data)
        shutil.copystat(source,target)
    except Exception:
        if created:
            try: os.unlink(target)
            except OSError: pass
        raise

def batch_move(source,target):
    if source==target:
        return
    os.link(source,target)
    try:
        os.unlink(source)
    except Exception:
        os.unlink(target)
        raise

def batch_cue_content(data, old_name, new_name):
    encoding='utf-8'
    try:
        text=data.decode(encoding)
    except UnicodeDecodeError:
        encoding,text='cp1252',data.decode('cp1252')
    matches=list(re.finditer(r'(?im)^[ \t]*(?:\ufeff)?FILE\s+"([^"]+)"\s+MP3[ \t]*\r?$',text))
    if len(matches)!=1 or matches[0].group(1) not in (old_name,new_name):
        raise ValueError('CUE benötigt genau eine zur MP3 passende FILE-Zeile.')
    match=matches[0]
    return (text[:match.start(1)]+new_name+text[match.end(1):]).encode(encoding)

def batch_cleanup_file(path, keep_apic=True):
    from mutagen.apev2 import APEv2, APENoHeaderError, delete as delete_ape
    try:
        tags=ID3(path)
    except ID3NoHeaderError:
        tags=ID3()
    keep=set(BATCH_KEEP)
    if not keep_apic:
        keep.discard('APIC')
    removed=[]
    for key in list(tags.keys()):
        if key[:4] not in keep:
            removed.append(key)
            del tags[key]
    if tags.unknown_frames:
        removed.append('unbekannte ID3-Frames')
        tags.unknown_frames=[]
    tags.save(path,v1=0,v2_version=3)
    try:
        ape=APEv2(path)
    except APENoHeaderError:
        ape=None
    if ape is not None:
        for key in list(ape.keys()):
            keep_cover=keep_apic and key.lower().startswith('cover art (')
            if key.lower() not in APE_KEEP and not keep_cover:
                removed.append('APEv2:'+key)
                del ape[key]
        if len(ape):
            ape.save(path)
        else:
            delete_ape(path)
    verified=batch_read_record(path)
    if verified['extra_count']:
        raise RuntimeError('Bereinigung unvollständig: '+str(verified['extras']+verified['ape_extras']))
    return removed

def delete_unwanted_id3_frames(path, keep_apic=True):
    return batch_cleanup_file(path,keep_apic)

def batch_restore(transaction, verify=False, progress=lambda *args:None):
    records=transaction['records']
    if verify:
        for record in records:
            if batch_hash(record['current'])!=record['after_hash']:
                raise ValueError('Datei wurde nach dem Speichern verändert: '+record['current'])
            if record['current']!=record['source'] and os.path.lexists(record['source']):
                raise FileExistsError('Alter Dateiname ist inzwischen belegt: '+record['source'])
    errors=[]
    for index,record in enumerate(reversed(records),1):
        try:
            progress(index,len(records),'Wiederherstellen: '+Path(record['source']).name)
            shutil.copy2(record['backup'],record['current'])
            batch_move(record['current'],record['source'])
        except Exception as error:
            errors.append(record['source']+': '+str(error))
    if errors:
        raise RuntimeError('Wiederherstellung prüfen: '+'; '.join(errors)+'\nSicherungen: '+transaction['directory'])
    return transaction['before']

def batch_save_records(rows, with_cue=True, persistent=True, cancelled=lambda:False, progress=lambda *args:None):
    plans,targets=[],set()
    for row in rows:
        if not row['dirty']:
            continue
        source=row['path']
        name=row['pending_name']
        if name and (os.path.basename(name)!=name or not name.lower().endswith('.mp3')):
            raise ValueError('Ungültiger Zieldateiname.')
        target=str(Path(source).with_name(name)) if name else source
        pairs=[(source,target)]
        cue=str(Path(source).with_suffix('.cue'))
        if with_cue and source!=target and os.path.isfile(cue):
            pairs.append((cue,str(Path(target).with_suffix('.cue'))))
        for old,new in pairs:
            if os.path.islink(old) or not os.path.isfile(old):
                raise ValueError('Keine reguläre Datei: '+old)
            if new in targets or (new!=old and os.path.lexists(new)):
                raise FileExistsError('Ziel existiert bereits: '+new)
            targets.add(new)
        if len(pairs)==2:
            batch_cue_content(Path(cue).read_bytes(),Path(source).name,Path(target).name)
        if row['cover_path'] and not Path(row['cover_path']).is_file():
            raise FileNotFoundError(row['cover_path'])
        plans.append((row,pairs))
    if not plans:
        return {'rows':[],'transaction':None}
    directory=tempfile.mkdtemp(prefix='hoerbuch-v46-undo-')
    transaction=dict(directory=directory,records=[],before=[])
    updates=[]
    try:
        for index,(row,pairs) in enumerate(plans,1):
            if cancelled():
                raise BatchCancelled()
            progress(index-1,len(plans),'Sicherung: '+Path(row['path']).name)
            transaction['before'].append(batch_read_record(row['path'],row['uid']))
            for source,target in pairs:
                backup=str(Path(directory)/str(len(transaction['records'])))
                batch_copy(source,backup,cancelled)
                transaction['records'].append(dict(source=source,target=target,current=source,backup=backup))
                if persistent:
                    batch_copy(source,unique_backup_path(source+'.id3backup'),cancelled)
        for index,(row,pairs) in enumerate(plans,1):
            if cancelled():
                raise BatchCancelled()
            path=row['path']
            progress(index-1,len(plans),'Speichern: '+Path(path).name)
            try:
                easy=EasyID3(path)
            except ID3NoHeaderError:
                easy=EasyID3()
            enabled=row['enabled']
            for field,key in zip(BATCH_FIELDS,BATCH_KEYS):
                if row[field].strip() and (enabled is None or key in enabled):
                    easy[key]=[row[field].strip()]
                elif key in easy:
                    del easy[key]
            easy.save(path,v1=0,v2_version=3)
            tags=ID3(path)
            if enabled is not None and 'APIC' not in enabled:
                tags.delall('APIC')
            elif row['cover_path']:
                cover=Path(row['cover_path'])
                data=cover.read_bytes()
                if not data:
                    raise ValueError('Leere Cover-Datei.')
                tags.delall('APIC')
                tags.add(APIC(encoding=3,mime='image/png' if cover.suffix.lower()=='.png' else 'image/jpeg',type=3,desc='Cover',data=data))
            tags.save(path,v1=0,v2_version=3)
            if row['cleanup']:
                batch_cleanup_file(path, enabled is None or 'APIC' in enabled)
            for source,target in pairs:
                record=next(r for r in transaction['records'] if r['source']==source)
                batch_move(source,target)
                record['current']=target
                if target.lower().endswith('.cue'):
                    Path(target).write_bytes(batch_cue_content(Path(target).read_bytes(),Path(pairs[0][0]).name,Path(pairs[0][1]).name))
            updates.append(batch_read_record(pairs[0][1],row['uid']))
            progress(index,len(plans),'Gespeichert: '+Path(pairs[0][1]).name)
        for record in transaction['records']:
            record['after_hash']=batch_hash(record['current'],cancelled)
        return dict(rows=updates,transaction=transaction)
    except Exception as error:
        try:
            batch_restore(transaction,progress=progress)
        except Exception as restore_error:
            raise RuntimeError(str(error)+'\n'+str(restore_error)) from error
        shutil.rmtree(directory,ignore_errors=True)
        raise


class LoadWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(object)
    diagnostics_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal()
    def __init__(self, file_paths, group_by_album, adv_mode, auto_multicd=True, split_stories=False):
        super().__init__()
        self.file_paths, self.group_by_album, self.adv_mode = file_paths, group_by_album, adv_mode
        self.auto_multicd, self.split_stories, self._is_cancelled = auto_multicd, split_stories, False
    def cancel(self):
        self._is_cancelled = True
    def run(self):
        parsed_files = []
        for index,path in enumerate(self.file_paths):
            if self._is_cancelled:
                self.cancelled_signal.emit(); return
            meta = safe_meta_from_file(path)
            parsed_files.append(meta)
            self.progress_signal.emit(index+1, len(self.file_paths))
            self.diagnostics_signal.emit('Track=%s | Disc=%s | %s' % (meta['track'],meta['disc'],meta['filename']))
        groups, result, reasons = defaultdict(list), defaultdict(list), {}
        for item in parsed_files:
            key = item['album'] if self.group_by_album and item['album'] else os.path.dirname(item['path'])
            groups[key].append(item)
        for key,items in groups.items():
            if self._is_cancelled:
                self.cancelled_signal.emit(); return
            is_advent = self.adv_mode and any(word in (str(key)+' '+items[0]['filename']+' '+items[0]['title']).lower()
                                                  for word in ('advent','weihnacht','bescherung'))
            keyword = get_short_story_keyword(key)
            initial = max(item['disc'] for item in items)
            detected = False
            if self.auto_multicd and initial==1 and len(items)>1 and not keyword and not is_advent:
                detected = detect_missing_discs(items)
            if is_advent:
                days = [extract_advent_day_helper(item['filename'],item['title']) for item in items]
                marked = [index for index,day in enumerate(days) if day]
                if marked:
                    for index,item in enumerate(items):
                        item['category'] = days[index] or ('Intro' if index<marked[0] else 'Outro')
                    reasons[key] = '🎅 ADVENT erkannt'; result[key].extend(items); continue
            if keyword:
                for item in items:
                    item['category'] = extract_short_story_name(item['title'],item['filename']).replace('/','-').replace(':',' -')
                reasons[key] = '📚 KURZGESCHICHTEN erkannt ('+keyword+')'; result[key].extend(items); continue
            maximum = max(item['disc'] for item in items)
            if self.split_stories and maximum<=1 and detect_story_segments(items):
                reasons[key] = '📖 MEHRERE GESCHICHTEN erkannt'; result[key].extend(items); continue
            if self.auto_multicd and maximum>1:
                reasons[key] = '💿 MULTI-CD automatisch erkannt' if detected else '💿 MULTI-CD erkannt'
                for item in items: item['category'] = 'CD '+str(item['disc'])
            else:
                reasons[key] = '🎧 NORMALES HÖRSPIEL'
                for item in items: item['category'] = '-'
            result[key].extend(items)
        self.finished_signal.emit((result,reasons))

class BatchMergeWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    merged_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, data_structure, target_mode, custom_target_dir, options, editor_values, enabled_fields):
        super().__init__()
        self.data_structure = data_structure
        self.target_mode = target_mode
        self.custom_target_dir = custom_target_dir
        self.options = options
        self.editor_values = editor_values
        self.enabled_fields = enabled_fields
        self._is_cancelled = False
        self.current_process = None

    def cancel(self):
        self._is_cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass

    def run(self):
        total_jobs = sum(len(set([item['category'] for item in items])) for items in self.data_structure.values())
        current = 0
        fd, list_file_path = tempfile.mkstemp(prefix='merger-concat-', suffix='.txt')
        os.close(fd)

        for base_key, items in self.data_structure.items():
            categories = defaultdict(list)
            for item in items:
                categories[item['category']].append(item)

            if self._is_cancelled: break
            for category, cat_items in categories.items():
                if self._is_cancelled: break
                current += 1
                self.progress_signal.emit(current, total_jobs)
                try:
                    display_base = os.path.basename(base_key) if os.path.isabs(base_key) else base_key
                    is_story = any(item.get('story_split',False) for item in cat_items)
                    display_name = display_base if category == '-' else (str(category) if is_story else (f"{display_base} {category}" if str(category).startswith(('CD ','Tag ')) or category in ['Intro','Outro'] else f"{display_base} - {category}"))

                    ok, msg = check_track_completeness(cat_items, require_start_from_one=not any(i.get('story_split') for i in cat_items))
                    self.log_signal.emit(f"📋 Track-Check [{display_name}]: {msg}")

                    if self.target_mode == 'SOURCE':
                        out_dir = os.path.dirname(cat_items[0]['path'])
                    elif self.target_mode == 'PARENT':
                        out_dir = os.path.dirname(os.path.dirname(cat_items[0]['path']))
                    elif self.target_mode == 'CUSTOM':
                        out_dir = self.custom_target_dir
                    else:
                        out_dir = os.path.join(os.path.dirname(cat_items[0]['path']), self.options['subfolder_name'])

                    safe_name = ''.join(c for c in display_name if c.isalnum() or c in (' ', '-', '_', '.')).strip() or 'Hoerbuch'
                    if self.options.get('create_subfolder_per_job'):
                        out_dir = os.path.join(out_dir, safe_name)
                    os.makedirs(out_dir, exist_ok=True)
                    output_file = os.path.join(out_dir, f"{safe_name}.mp3")

                    sorted_items = sorted(cat_items, key=lambda x: (x['track'] if x['track'] != 999 else 9999, x['filename'].lower()))
                    with open(list_file_path, 'w', encoding='utf-8') as f:
                        for item in sorted_items:
                            f.write("file '" + item['path'].replace("'", "'\\''") + "'\n")

                    if os.path.lexists(output_file) or (self.options.get('create_cue') and os.path.lexists(os.path.splitext(output_file)[0]+'.cue')):
                        raise FileExistsError('Ausgabe existiert bereits: '+output_file)
                    cmd = ['ffmpeg', '-nostdin', '-n', '-f', 'concat', '-safe', '0', '-i', list_file_path, '-c', 'copy', output_file]
                    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
                    self.current_process = process
                    for line in process.stderr:
                        if 'Error' in line:
                            self.log_signal.emit(line.strip())
                    process.wait()
                    self.current_process = None
                    if self._is_cancelled:
                        if os.path.isfile(output_file): os.remove(output_file)
                        break
                    if process.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                        raise Exception('FFmpeg Fehler oder leere Output-Datei')

                    defaults = collect_group_defaults(sorted_items)
                    final_values = {
                        'artist': defaults['artist'],
                        'title': defaults.get('title') or display_name,
                        'album': defaults['album'] or display_base,
                        'discnumber': defaults['discnumber'],
                        'tracknumber': defaults['tracknumber'],
                        'date': defaults['date'],
                        'genre': defaults['genre'],
                    }

                    cover_mode = 'none'
                    cover_bytes = None
                    cover_path = ''
                    if 'APIC' in self.enabled_fields:
                        if self.editor_values['cover_path'].strip():
                            cover_mode = 'file'
                            cover_path = self.editor_values['cover_path'].strip()
                        elif self.options['copy_cover_from_first'] and defaults['cover']:
                            cover_mode = 'bytes'
                            cover_bytes = defaults['cover']

                    write_selected_id3_tags(output_file, final_values, self.enabled_fields, cover_mode=cover_mode, cover_bytes=cover_bytes, cover_path=cover_path)

                    if self.options.get('export_cover_file') and 'APIC' in self.enabled_fields:
                        exported_cover = export_cover_file(os.path.splitext(output_file)[0], cover_mode=cover_mode, cover_bytes=cover_bytes, cover_path=cover_path)
                        if exported_cover:
                            self.log_signal.emit(f"🖼 Cover exportiert: {exported_cover}")

                    if self.options['create_cue']:
                        cue_path = os.path.splitext(output_file)[0] + '.cue'
                        cue_content = build_cue_content(output_file, final_values['album'] or display_name, final_values['artist'], sorted_items, sequential=self.options['cue_force_sequential'], include_track_performer=self.options['cue_include_track_performer'])
                        with open(cue_path, 'w', encoding='utf-8') as f:
                            f.write(cue_content)
                        self.log_signal.emit(f"✅ CUE erstellt: {cue_path}")

                    self.log_signal.emit("🧾 Verbleibende ID3-Tags der gemergten Datei:")
                    for line in get_id3_tag_lines(output_file):
                        self.log_signal.emit("   " + line)

                    if self.options.get('delete_originals'):
                        deleted = 0
                        for item in sorted_items:
                            try:
                                if os.path.abspath(item['path']) != os.path.abspath(output_file):
                                    os.remove(item['path'])
                                    deleted += 1
                            except Exception:
                                pass
                        self.log_signal.emit(f"🗑 {deleted} Originaldateien gelöscht.")

                    os.chmod(output_file,0o644)
                    self.merged_signal.emit(output_file)
                except Exception as e:
                    self.log_signal.emit(f"❌ FEHLER: {e}")

        if os.path.exists(list_file_path):
            os.remove(list_file_path)
        self.finished_signal.emit(not self._is_cancelled)

class MergerWindowV43(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux Mint Hörbuch Batch-Merger PRO V46 (inkl. Abbruch, User-Zielordner, Session-Navigation & kompakter Logs)")
        self.resize(1340, 980)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        self.data_structure = defaultdict(list)
        self.album_reasons = {}
        self.last_merged_output = ''
        self.session_merged_outputs = []
        self.current_editor_session_index = -1
        self.temp_cover_preview = ''

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        title = QLabel("🎧 Hörbuch Batch-Merger PRO V46")
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 6px 0;")
        outer.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { background:#2b2b2b; color:#ddd; padding:10px 16px; } QTabBar::tab:selected { background:#3d70b2; color:white; }")
        outer.addWidget(self.tabs)

        self.build_main_tab()
        self.build_options_tab()
        self.build_id3_tab()
        self.build_id3_batch_tab()

        self.batch_merge_running = False
        self.batch_merge_cancel_requested = False

    def build_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        btn_add = QPushButton("📂 Dateien/Ordner hinzufügen")
        btn_add.clicked.connect(self.select_files_dialog)
        row.addWidget(btn_add)
        btn_clear = QPushButton("🗑 Liste leeren")
        btn_clear.clicked.connect(self.clear_all)
        row.addWidget(btn_clear)
        layout.addLayout(row)

        self.tree = BatchDragDropTree(self)
        layout.addWidget(self.tree)

        self.reason_label = QLabel("Erkennung: Noch keine Daten geladen")
        self.reason_label.setStyleSheet("font-size: 13px; color: #b8d7ff;")
        layout.addWidget(self.reason_label)

        target_group = QGroupBox("Zielordner")
        target_layout = QVBoxLayout(target_group)
        self.radio_source = QRadioButton("Im Quellordner speichern")
        self.radio_merged = QRadioButton("Im Unterordner speichern")
        self.radio_parent = QRadioButton("Im übergeordneten Ordner speichern")
        self.radio_custom = QRadioButton("Benutzerdefinierten Ordner wählen")
        self.radio_merged.setChecked(True)
        self.target_group_buttons = QButtonGroup(self)
        for i, rb in enumerate([self.radio_source, self.radio_merged, self.radio_parent, self.radio_custom]):
            self.target_group_buttons.addButton(rb, i)
            target_layout.addWidget(rb)
        target_row = QHBoxLayout()
        self.custom_target_edit = QLineEdit()
        self.custom_target_edit.setPlaceholderText("Benutzerdefinierter Zielordner...")
        target_row.addWidget(self.custom_target_edit)
        btn_target = QPushButton("Ordner wählen")
        btn_target.clicked.connect(self.select_custom_target_dir)
        target_row.addWidget(btn_target)
        target_layout.addLayout(target_row)
        layout.addWidget(target_group)

        self.track_check_label = QLabel("Track-Check: Noch keine Daten geladen")
        self.track_check_label.setStyleSheet("font-size: 13px; color: #b8d7ff;")
        layout.addWidget(self.track_check_label)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.btn_merge = QPushButton("▶ Batch-Merge starten")
        self.btn_merge.clicked.connect(self.start_batch_merge)
        self.btn_merge.setStyleSheet("font-size: 15px; font-weight: bold; padding: 12px; background:#2e7d32;")
        btn_layout.addWidget(self.btn_merge)

        self.btn_stop = QPushButton("🛑 Abbrechen")
        self.btn_stop.clicked.connect(self.stop_current_work)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("QPushButton { font-size: 15px; font-weight: bold; padding: 12px; background:#c62828; color:white; } QPushButton:disabled { background:#555555; color:#aaaaaa; }")
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        btn_repair = QPushButton('CUE-Dateien reparieren')
        btn_repair.clicked.connect(self.repair_cue_files)
        layout.addWidget(btn_repair)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background:#111; color:#dcdcdc;")
        layout.addWidget(self.log_output)

        self.tabs.addTab(tab, "Hauptansicht")

    def build_options_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.opt_group_by_album = QCheckBox('Nach Album gruppieren')
        self.opt_group_by_album.setChecked(True)
        form.addRow('Gruppierung:',self.opt_group_by_album)
        self.opt_adv_mode = QCheckBox('Advent-/Weihnachts-Erkennung aktivieren')
        self.opt_adv_mode.setChecked(True)
        form.addRow('Advent-Erkennung:',self.opt_adv_mode)
        self.opt_auto_multicd = QCheckBox('MULTI-CD automatisch erkennen')
        self.opt_auto_multicd.setChecked(True)
        form.addRow('Multi-CD-Erkennung:',self.opt_auto_multicd)
        self.opt_split_stories = QCheckBox('Mehrere Geschichten pro Album trennen')
        self.opt_split_stories.setChecked(False)
        form.addRow('Geschichten trennen:',self.opt_split_stories)

        self.opt_create_cue = QCheckBox("CUE-Datei automatisch erstellen")
        self.opt_create_cue.setChecked(True)
        form.addRow("CUE:", self.opt_create_cue)

        self.opt_cue_force_sequential = QCheckBox("CUE-Tracknummern fortlaufend")
        self.opt_cue_force_sequential.setChecked(True)
        form.addRow("CUE Tracknummern:", self.opt_cue_force_sequential)

        self.opt_cue_include_track_performer = QCheckBox("PERFORMER pro Track in CUE")
        self.opt_cue_include_track_performer.setChecked(True)
        form.addRow("CUE PERFORMER:", self.opt_cue_include_track_performer)

        self.opt_copy_cover_from_first = QCheckBox("Cover aus erster Datei übernehmen")
        self.opt_copy_cover_from_first.setChecked(True)
        form.addRow("Coverquelle:", self.opt_copy_cover_from_first)

        self.opt_export_cover_file = QCheckBox("Cover zusätzlich als Bilddatei exportieren")
        self.opt_export_cover_file.setChecked(False)
        form.addRow("Cover exportieren:", self.opt_export_cover_file)

        self.opt_create_subfolder_per_job = QCheckBox("Für jeden Merge einen eigenen Unterordner erstellen")
        self.opt_create_subfolder_per_job.setChecked(False)
        form.addRow("Merge-Unterordner:", self.opt_create_subfolder_per_job)

        self.opt_delete_originals = QCheckBox("Originaldateien nach Merge löschen")
        self.opt_delete_originals.setChecked(False)
        form.addRow("Originale löschen:", self.opt_delete_originals)

        self.opt_subfolder_name = QLineEdit("Merged")
        form.addRow("Unterordnername:", self.opt_subfolder_name)
        layout.addLayout(form)

        layout.addWidget(QLabel("Nur diese ID3-Tags in der gemergten Datei speichern:"))
        self.tag_checkboxes = {}
        for key, label in EDITABLE_ID3_FIELDS.items():
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.tag_checkboxes[key] = cb
            layout.addWidget(cb)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Optionen")

    def build_id3_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        btn_last = QPushButton("Letzte gemergte Datei laden")
        btn_last.clicked.connect(self.load_last_merged_into_editor)
        row.addWidget(btn_last)
        btn_prev = QPushButton("⟵ Vorherige Session-MP3")
        btn_prev.clicked.connect(self.load_previous_session_merged_file)
        row.addWidget(btn_prev)
        btn_next = QPushButton("Nächste Session-MP3 ⟶")
        btn_next.clicked.connect(self.load_next_session_merged_file)
        row.addWidget(btn_next)
        btn_file = QPushButton("MP3 im ID3-Editor öffnen")
        btn_file.clicked.connect(self.select_mp3_for_editor)
        row.addWidget(btn_file)
        layout.addLayout(row)

        self.editor_current_file = QLabel("Keine Datei geladen")
        self.editor_current_file.setStyleSheet("color: #999; font-style: italic;")
        layout.addWidget(self.editor_current_file)

        self.id3_batch_status = QLabel("Batch-Merge-Status: nicht aktiv")
        self.id3_batch_status.setStyleSheet("padding:8px; border:1px solid #555; border-radius:6px; background:#2b2b2b; color:#ccc;")
        layout.addWidget(self.id3_batch_status)

        form = QFormLayout()
        self.edit_artist = QLineEdit()
        self.edit_title = QLineEdit()
        self.edit_album = QLineEdit()
        self.edit_discnumber = QLineEdit()
        self.edit_tracknumber = QLineEdit()
        self.edit_date = QLineEdit()
        self.edit_genre = QLineEdit()
        self.suggestion_hint = QLabel(ddf_examples_text())
        self.suggestion_hint.setWordWrap(True)
        self.suggestion_hint.setStyleSheet('color:#9fd3ff; font-size:12px; font-style:italic;')
        self.edit_cover_path = QLineEdit()
        form.addRow("Artist:", self.edit_artist)
        form.addRow("Title:", self.edit_title)
        form.addRow("Album:", self.edit_album)
        form.addRow("Discnumber:", self.edit_discnumber)
        form.addRow("Track:", self.edit_tracknumber)
        form.addRow("Year:", self.edit_date)
        form.addRow("Genre:", self.edit_genre)
        cover_row = QHBoxLayout()
        cover_row.addWidget(self.edit_cover_path)
        btn_cover = QPushButton("Cover wählen")
        btn_cover.clicked.connect(self.select_cover_for_editor)
        cover_row.addWidget(btn_cover)
        form.addRow("Neues Coverbild:", cover_row)
        layout.addLayout(form)

        self.cover_preview = QLabel("Kein Cover")
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setMinimumSize(260, 260)
        self.cover_preview.setStyleSheet("border:1px solid #555; background:#222;")
        layout.addWidget(QLabel("Cover-Vorschau (APIC):"))
        layout.addWidget(self.cover_preview)

        layout.addWidget(QLabel("Aktuell vorhandene ID3-Tags:"))
        self.id3_existing_list = QListWidget()
        layout.addWidget(self.id3_existing_list)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("ID3-Tags in geladene Datei speichern")
        btn_save.clicked.connect(self.save_editor_tags_to_loaded_file)
        btn_row.addWidget(btn_save)
        btn_cleanup = QPushButton("Restliche ID3-Tags löschen (alles außer Artist, Titel, Album, Disc, Track, Jahr, Genre, Cover)")
        btn_cleanup.setToolTip("Löscht alle übrigen ID3-Frames, z.B. TSSE, COMM, TXXX, USLT, PRIV usw.")
        btn_cleanup.clicked.connect(self.delete_remaining_tags_from_loaded_file)
        btn_row.addWidget(btn_cleanup)
        btn_clear = QPushButton("Editor-Felder leeren")
        btn_clear.clicked.connect(self.clear_editor_fields)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        self.tabs.addTab(tab, "ID3-Editor")

    def log(self, message):
        self.log_output.append(str(message))

    def clear_all(self):
        self.data_structure = defaultdict(list)
        self.album_reasons = {}
        self.tree.clear()
        self.log_output.clear()
        self.progress.setValue(0)
        self.reason_label.setText("Erkennung: Noch keine Daten geladen")
        self.track_check_label.setText("Track-Check: Noch keine Daten geladen")
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setEnabled(False)

    def process_dropped_urls(self, urls):
        found = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for name in files:
                        if name.lower().endswith('.mp3'):
                            found.append(os.path.join(root, name))
            elif path.lower().endswith('.mp3'):
                found.append(path)
        self.load_files(found)

    def select_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'MP3-Dateien auswählen', '', 'MP3-Dateien (*.mp3)')
        if not files:
            folder = QFileDialog.getExistingDirectory(self, 'Ordner auswählen')
            if folder:
                for root, _, names in os.walk(folder):
                    for name in names:
                        if name.lower().endswith('.mp3'):
                            files.append(os.path.join(root, name))
        self.load_files(files)

    def select_custom_target_dir(self):
        folder = QFileDialog.getExistingDirectory(self, 'Zielordner auswählen')
        if folder:
            self.custom_target_edit.setText(folder)
            self.radio_custom.setChecked(True)

    def load_files(self, files):
        if not files:
            return
        self.log(f"📥 Lade {len(files)} Dateien ...")
        self.load_worker = LoadWorker(files, self.opt_group_by_album.isChecked(), self.opt_adv_mode.isChecked(),
                                      self.opt_auto_multicd.isChecked(), self.opt_split_stories.isChecked())
        self.load_worker.diagnostics_signal.connect(self.log)
        self.load_worker.cancelled_signal.connect(self.on_load_cancelled)
        self.btn_stop.setEnabled(True)
        self.load_worker.progress_signal.connect(lambda c, t: self.progress.setMaximum(t) or self.progress.setValue(c))
        self.load_worker.finished_signal.connect(self.on_load_finished)
        self.load_worker.start()

    def on_load_finished(self, result):
        self.btn_stop.setEnabled(False)
        self.data_structure, self.album_reasons = result
        self.rebuild_tree()
        checks = []
        for base_key, items in self.data_structure.items():
            ok, msg = check_track_completeness(items)
            name = os.path.basename(base_key) if os.path.isabs(base_key) else base_key
            checks.append(f"{name}: {msg}")
        unique_reasons = sorted(set(self.album_reasons.values()))
        if not unique_reasons:
            self.reason_label.setText('Erkennung: keine')
        elif len(unique_reasons) <= 3:
            self.reason_label.setText('Erkennung: ' + ' | '.join(unique_reasons))
        else:
            self.reason_label.setText(f"Erkennung: {len(unique_reasons)} Typen erkannt. Details siehe Baumansicht.")
        self.track_check_label.setText(build_track_check_summary(self.data_structure, limit=2))
        self.log("✅ Dateien erfolgreich eingelesen.")
        for base_key, items in self.data_structure.items():
            ok, msg = check_track_completeness(items)
            name = os.path.basename(base_key) if os.path.isabs(base_key) else str(base_key)
            self.log(f"📚 {name}: {self.album_reasons.get(base_key, '-')}, {msg}")
        incomplete=[]
        for base_key, items in self.data_structure.items():
            ok, msg=check_track_completeness(items)
            if not ok: incomplete.append((str(base_key),msg))
        if incomplete:
            self.log('🚨 NICHT VOLLSTÄNDIGE ALBEN / FOLGEN:')
            for name,msg in incomplete: self.log(name+': '+msg)
        else:
            self.log('✅ Alle geladenen Alben bzw. Folgen sind trackmäßig vollständig.')
        first_group = next(iter(self.data_structure.values()), None)
        if first_group:
            defaults = collect_group_defaults(first_group)
            self.edit_artist.setText(defaults['artist'])
            self.edit_title.setText(defaults['album'])
            self.edit_album.setText(defaults['album'])
            self.edit_discnumber.setText(defaults['discnumber'])
            self.edit_tracknumber.setText(defaults['tracknumber'])
            self.edit_date.setText(defaults['date'])
            self.edit_genre.setText(defaults['genre'])
            if defaults['cover']:
                self.show_cover_from_bytes(defaults['cover']['data'])

    def _get_all_files_for_force(self, base_key):
        return self.data_structure.get(base_key, [])

    def force_advent_mode(self, base_key):
        items = self._get_all_files_for_force(base_key)
        if not items:
            return
        day_markers = []
        for idx, item in enumerate(items):
            day = extract_advent_day_helper(item['filename'], item['title'])
            item['day'] = day
            if day:
                day_markers.append(idx)
        if day_markers:
            min_day_idx = day_markers[0]
            for idx, item in enumerate(items):
                item['category'] = item['day'] if item['day'] else ('Intro' if idx < min_day_idx else 'Outro')
        self.album_reasons[base_key] = '🎅 Manuell als Advent gesetzt'
        self.rebuild_tree()

    def force_short_story_mode(self, base_key):
        items = self._get_all_files_for_force(base_key)
        for item in items:
            item['category'] = extract_short_story_name(item['title'], item['filename']).replace('/', '-').replace(':', ' -')
        self.album_reasons[base_key] = '📚 Manuell als Kurzgeschichten gesetzt'
        self.rebuild_tree()

    def force_multicd_mode(self, base_key):
        items = self._get_all_files_for_force(base_key)
        detect_missing_discs(items)
        for item in items:
            item['category'] = f"CD {item['disc']}"
        self.album_reasons[base_key] = '💿 Manuell als Multi-CD gesetzt'
        self.rebuild_tree()

    def force_normal_mode(self, base_key):
        items = self._get_all_files_for_force(base_key)
        for item in items:
            item['category'] = '-'
        self.album_reasons[base_key] = '🎧 Manuell als normales Hörspiel gesetzt'
        self.rebuild_tree()

    def rebuild_tree(self):
        self.tree.clear()
        missing_reports = []
        for base_key, items in sorted(self.data_structure.items(), key=lambda x: str(x[0]).lower()):
            name = os.path.basename(base_key) if os.path.isabs(base_key) else base_key
            root = QTreeWidgetItem([f"📁 {name}", '', self.album_reasons.get(base_key, '')])
            root.setData(0, Qt.UserRole, base_key)
            self.tree.addTopLevelItem(root)
            categories = defaultdict(list)
            for item in items:
                categories[item.get('category', '-')].append(item)
            for cat, cat_items in sorted(categories.items(), key=lambda x: str(x[0])):
                ok, msg = check_track_completeness(cat_items, require_start_from_one=(cat == '-' and not any(i.get('story_split') for i in cat_items)))
                parent = root if cat == '-' else QTreeWidgetItem(root, [f"   └─ 📁 {cat}", '', 'OK' if ok else 'FEHLT'])
                if cat != '-' and not ok:
                    parent.setForeground(2, QColor('#ff6666'))
                for item in sorted(cat_items, key=lambda x: (x['track'] if x['track'] != 999 else 9999, x['filename'].lower())):
                    track_display = str(item['track']).zfill(2) if item['track'] != 999 else '??'
                    title = item['title'] or item['filename']
                    child = QTreeWidgetItem([title, track_display, item.get('category', '-')])
                    parent.addChild(child)
                if cat != '-':
                    parent.addChild(QTreeWidgetItem([f"   ↳ {msg}", '', '']))
                else:
                    root.addChild(QTreeWidgetItem([f"   ↳ {msg}", '', '']))
                if not ok:
                    missing_reports.append(f"{name} [{cat}]: {msg}")
            root.setExpanded(True)
        if missing_reports:
            self.show_completeness_warning(missing_reports)

    def show_completeness_warning(self, messages):
        self.log("⚠ Vollständigkeitswarnung:")
        for msg in messages:
            self.log("   " + msg)

    def gather_options(self):
        return {
            'auto_multicd': self.opt_auto_multicd.isChecked(),
            'split_stories': self.opt_split_stories.isChecked(),
            'create_cue': self.opt_create_cue.isChecked(),
            'cue_force_sequential': self.opt_cue_force_sequential.isChecked(),
            'cue_include_track_performer': self.opt_cue_include_track_performer.isChecked(),
            'copy_cover_from_first': self.opt_copy_cover_from_first.isChecked(),
            'export_cover_file': self.opt_export_cover_file.isChecked(),
            'subfolder_name': self.opt_subfolder_name.text().strip() or 'Merged',
            'delete_originals': self.opt_delete_originals.isChecked(),
            'create_subfolder_per_job': self.opt_create_subfolder_per_job.isChecked(),
        }

    def gather_enabled_fields(self):
        return {key for key, cb in self.tag_checkboxes.items() if cb.isChecked()}

    def gather_editor_values(self):
        return {
            'artist': self.edit_artist.text().strip(),
            'title': self.edit_title.text().strip(),
            'album': self.edit_album.text().strip(),
            'discnumber': self.edit_discnumber.text().strip(),
            'tracknumber': self.edit_tracknumber.text().strip(),
            'date': self.edit_date.text().strip(),
            'genre': self.edit_genre.text().strip(),
            'cover_path': self.edit_cover_path.text().strip(),
        }

    def start_batch_merge(self):
        if not self.data_structure:
            QMessageBox.warning(self, 'Keine Daten', 'Bitte zuerst MP3-Dateien laden.')
            return
        if self.radio_source.isChecked():
            mode = 'SOURCE'
        elif self.radio_parent.isChecked():
            mode = 'PARENT'
        elif self.radio_custom.isChecked():
            mode = 'CUSTOM'
        else:
            mode = 'MERGED'
        target_dir = self.custom_target_edit.text().strip()
        if mode == 'CUSTOM' and not target_dir:
            QMessageBox.warning(self, 'Zielordner fehlt', 'Bitte einen Zielordner auswählen.')
            return
        self.worker = BatchMergeWorker(self.data_structure, mode, target_dir, self.gather_options(), self.gather_editor_values(), self.gather_enabled_fields())
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(lambda c, t: self.progress.setMaximum(t) or self.progress.setValue(c))
        self.worker.merged_signal.connect(self.on_merged_file_created)
        self.worker.finished_signal.connect(self.on_batch_merge_finished)
        self.btn_merge.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.update_batch_status(True, False)
        self.worker.start()

    def stop_batch_merge(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.log("🛑 Abbruch angefordert... Bitte warten, bis der aktuelle Vorgang stoppt.")
            self.btn_stop.setEnabled(False)
        self.update_batch_status(True, True)

    def on_batch_merge_finished(self, success):
        self.btn_merge.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.update_batch_status(False, False)
        self.log('✅ Batch-Merge-Prozess beendet oder abgebrochen.')

    def on_merged_file_created(self, path):
        self.last_merged_output = path
        if path not in self.session_merged_outputs:
            self.session_merged_outputs.append(path)
        self.current_editor_session_index = self.session_merged_outputs.index(path)
        self.log(f"🎵 Gemergte Datei: {path}")
        self.load_id3_file(path)

    def select_mp3_for_editor(self):
        path, _ = QFileDialog.getOpenFileName(self, 'MP3 auswählen', '', 'MP3-Dateien (*.mp3)')
        if path:
            self.load_id3_file(path)

    def load_last_merged_into_editor(self):
        if not self.last_merged_output or not os.path.exists(self.last_merged_output):
            QMessageBox.information(self, 'Keine Datei', 'Es gibt noch keine gemergte Datei in dieser Sitzung.')
            return
        if self.last_merged_output in self.session_merged_outputs:
            self.current_editor_session_index = self.session_merged_outputs.index(self.last_merged_output)
        self.load_id3_file(self.last_merged_output)

    def show_cover_from_bytes(self, data):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp.write(data)
        tmp.close()
        self.temp_cover_preview = tmp.name
        pix = QPixmap(tmp.name)
        if pix.isNull():
            self.cover_preview.setText('Kein Cover')
        else:
            self.cover_preview.setPixmap(pix.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_cover_from_path(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            self.cover_preview.setText('Kein Cover')
        else:
            self.cover_preview.setPixmap(pix.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_batch_status(self, running, cancel_requested=False):
        self.batch_merge_running = running
        self.batch_merge_cancel_requested = cancel_requested
        if cancel_requested:
            self.id3_batch_status.setText("Batch-Merge-Status: Abbruch angefordert ...")
            self.id3_batch_status.setStyleSheet("padding:8px; border:1px solid #8a6d3b; border-radius:6px; background:#5c4700; color:#ffd666;")
        elif running:
            self.id3_batch_status.setText("Batch-Merge-Status: läuft")
            self.id3_batch_status.setStyleSheet("padding:8px; border:1px solid #1f6f43; border-radius:6px; background:#123524; color:#7cfc98;")
        else:
            self.id3_batch_status.setText("Batch-Merge-Status: nicht aktiv")
            self.id3_batch_status.setStyleSheet("padding:8px; border:1px solid #555; border-radius:6px; background:#2b2b2b; color:#ccc;")

    def load_id3_file(self, path):
        suffix = ''
        if path in self.session_merged_outputs:
            idx = self.session_merged_outputs.index(path) + 1
            suffix = f'  [Session-Datei {idx}/{len(self.session_merged_outputs)}]'
            self.current_editor_session_index = idx - 1
        self.editor_current_file.setText(path + suffix)
        meta = safe_meta_from_file(path)
        suggested = suggest_ddf_metadata(path)
        self.edit_artist.setText(suggested['artist'] or meta['artist'])
        self.edit_title.setText(suggested['title'] or meta['title'])
        self.edit_album.setText(suggested['album'] or meta['album'])
        self.edit_discnumber.setText(suggested['disc'] or (str(meta['disc']) if meta['disc'] else ''))
        self.edit_tracknumber.setText(suggested['track'] or (str(meta['track']) if meta['track'] != 999 else ''))
        self.edit_date.setText(suggested['year'] or meta['year'])
        self.edit_genre.setText(suggested['genre'] or meta['genre'])
        self.edit_cover_path.clear()
        self.id3_existing_list.clear()
        for line in get_id3_tag_lines(path):
            self.id3_existing_list.addItem(QListWidgetItem(line))
        cover = extract_cover_bytes(path)
        if cover:
            self.show_cover_from_bytes(cover['data'])
        else:
            self.cover_preview.setText('Kein Cover')
            self.cover_preview.setPixmap(QPixmap())
        self.tabs.setCurrentIndex(2)

    def select_cover_for_editor(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Coverbild auswählen', '', 'Bilder (*.jpg *.jpeg *.png)')
        if path:
            self.edit_cover_path.setText(path)
            self.show_cover_from_path(path)

    def load_previous_session_merged_file(self):
        if not self.session_merged_outputs:
            QMessageBox.information(self, 'Keine Session-Dateien', 'In dieser Sitzung wurden noch keine MP3s gemergt.')
            return
        if self.current_editor_session_index == -1:
            self.current_editor_session_index = len(self.session_merged_outputs) - 1
        else:
            self.current_editor_session_index = max(0, self.current_editor_session_index - 1)
        self.load_id3_file(self.session_merged_outputs[self.current_editor_session_index])

    def load_next_session_merged_file(self):
        if not self.session_merged_outputs:
            QMessageBox.information(self, 'Keine Session-Dateien', 'In dieser Sitzung wurden noch keine MP3s gemergt.')
            return
        if self.current_editor_session_index == -1:
            self.current_editor_session_index = 0
        else:
            self.current_editor_session_index = min(len(self.session_merged_outputs) - 1, self.current_editor_session_index + 1)
        self.load_id3_file(self.session_merged_outputs[self.current_editor_session_index])

    def keyPressEvent(self, event):
        if self.tabs.currentIndex() == 2 and self.session_merged_outputs:
            if event.key() == Qt.Key_Left:
                self.load_previous_session_merged_file()
                return
            if event.key() == Qt.Key_Right:
                self.load_next_session_merged_file()
                return
        super().keyPressEvent(event)

    def clear_editor_fields(self):
        self.edit_artist.clear()
        self.edit_title.clear()
        self.edit_album.clear()
        self.edit_discnumber.clear()
        self.edit_tracknumber.clear()
        self.edit_date.clear()
        self.edit_genre.clear()
        self.edit_cover_path.clear()
        self.cover_preview.setText('Kein Cover')
        self.cover_preview.setPixmap(QPixmap())

    def delete_remaining_tags_from_loaded_file(self):
        path = self.editor_current_file.text().split('  [Session-Datei', 1)[0].strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, 'Keine Datei', 'Bitte zuerst eine MP3-Datei im ID3-Editor laden.')
            return
        removed = delete_unwanted_id3_frames(path, keep_apic=('APIC' in self.gather_enabled_fields()))
        self.log(f"🧹 Entfernte restliche ID3-Tags: {', '.join(removed) if removed else 'keine'}")
        self.load_id3_file(path)

    def save_editor_tags_to_loaded_file(self):
        path = self.editor_current_file.text().split('  [Session-Datei', 1)[0].strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, 'Keine Datei', 'Bitte zuerst eine MP3-Datei im ID3-Editor laden.')
            return
        values = self.gather_editor_values()
        enabled_fields = self.gather_enabled_fields()
        write_selected_id3_tags(path, values, enabled_fields, cover_mode='file' if values['cover_path'] else 'none', cover_path=values['cover_path'])
        self.log(f"💾 ID3-Tags gespeichert: {path}")
        self.load_id3_file(path)

class BatchTableModel(QAbstractTableModel):
    edited = pyqtSignal(object)
    HEADERS = ['Datei / Umbenennungsvorschau','Artist','Titel','Album','Track','Disc','Jahr','Genre','Cover','Rest-Tags','Status']
    def __init__(self,parent=None):
        super().__init__(parent)
        self.rows=[]
        self.by_uid={}
        self.by_path={}
    def rowCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole:
            return self.HEADERS[section] if orientation==Qt.Horizontal else str(section+1)
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or index.row()>=len(self.rows):
            return None
        row=self.rows[index.row()]
        if role==Qt.ToolTipRole:
            return row['path']+('\nVorgemerkt: '+row['pending_name'] if row['pending_name'] else '')
        if role==Qt.ForegroundRole and row['dirty']:
            return QColor('#ffd166')
        if role not in (Qt.DisplayRole,Qt.EditRole):
            return None
        column=index.column()
        if column==0:
            return row['pending_name'] or os.path.basename(row['path'])
        if 1<=column<=7:
            return row[BATCH_FIELDS[column-1]]
        if column==8:
            return 'neu vorgemerkt' if row['cover_path'] else ('ja' if row['has_cover'] else 'nein')
        if column==9:
            return str(row['extra_count'])+(' → 0 vorgemerkt' if row['cleanup'] else '')
        return ('Bereinigung; ' if row['cleanup'] else '')+('ungespeichert' if row['dirty'] else 'gespeichert')
    def flags(self,index):
        flags=Qt.ItemIsEnabled|Qt.ItemIsSelectable
        if index.isValid() and 1<=index.column()<=7:
            flags|=Qt.ItemIsEditable
        return flags
    def setData(self,index,value,role=Qt.EditRole):
        if role!=Qt.EditRole or not index.isValid() or not 1<=index.column()<=7:
            return False
        row=self.rows[index.row()]
        field=BATCH_FIELDS[index.column()-1]
        value=str(value).strip()
        if row[field]==value:
            return False
        self.edited.emit({'kind':'preview','rows':[copy.deepcopy(row)]})
        row[field],row['dirty']=value,True
        self.dataChanged.emit(self.index(index.row(),0),self.index(index.row(),10))
        return True
    def append(self,rows):
        rows=[row for row in rows if row['uid'] not in self.by_uid and row['realpath'] not in self.by_path]
        if not rows:
            return
        first=len(self.rows)
        self.beginInsertRows(QModelIndex(),first,first+len(rows)-1)
        for row in rows:
            self.by_uid[row['uid']]=len(self.rows)
            self.by_path[row['realpath']]=row['uid']
            self.rows.append(row)
        self.endInsertRows()
    def replace(self,rows):
        changed=[]
        for row in rows:
            index=self.by_uid.get(row['uid'])
            if index is None:
                self.append([row])
            else:
                self.by_path.pop(self.rows[index]['realpath'],None)
                self.rows[index]=row
                self.by_path[row['realpath']]=row['uid']
                changed.append(index)
        if changed:
            self.dataChanged.emit(self.index(min(changed),0),self.index(max(changed),10))
    def reset_rows(self,rows):
        self.beginResetModel()
        self.rows=list(rows)
        self.by_uid={row['uid']:index for index,row in enumerate(self.rows)}
        self.by_path={row['realpath']:row['uid'] for row in self.rows}
        self.endResetModel()

class BatchDropView(QTableView):
    paths_dropped=pyqtSignal(object)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setWordWrap(False)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and all(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragMoveEvent(self,event):
        self.dragEnterEvent(event)
    def dropEvent(self,event):
        if event.mimeData().hasUrls() and all(url.isLocalFile() for url in event.mimeData().urls()):
            self.paths_dropped.emit([url.toLocalFile() for url in event.mimeData().urls()])
            event.acceptProposedAction()
        else:
            event.ignore()

class BatchJob(QThread):
    progress=pyqtSignal(int,int,str)
    chunk=pyqtSignal(object)
    completed=pyqtSignal(object)
    failed=pyqtSignal(str)
    def __init__(self,kind,payload,parent=None):
        super().__init__(parent)
        self.kind,self.payload=kind,payload
        self.last_progress=0.0
    def report(self,current,total,text):
        now=time.monotonic()
        if now-self.last_progress>=0.07 or (total>0 and current==total):
            self.last_progress=now
            self.progress.emit(current,total,text)
    def run(self):
        try:
            if self.kind=='load':
                paths,known=self.payload
                found={}
                for value in paths:
                    if self.isInterruptionRequested():
                        raise BatchCancelled()
                    if os.path.isdir(value):
                        for root,_,names in os.walk(value):
                            if self.isInterruptionRequested():
                                raise BatchCancelled()
                            self.report(0,0,'Ordner durchsuchen: '+root)
                            for name in sorted(names):
                                path=os.path.abspath(os.path.join(root,name))
                                if name.lower().endswith('.mp3'):
                                    real=os.path.realpath(path)
                                    if real not in known: found.setdefault(real,path)
                    elif str(value).lower().endswith('.mp3'):
                        path=os.path.abspath(value)
                        real=os.path.realpath(path)
                        if real not in known: found.setdefault(real,path)
                pending,errors=[],[]
                for index,path in enumerate(found.values(),1):
                    if self.isInterruptionRequested():
                        raise BatchCancelled()
                    try:
                        pending.append(batch_read_record(path))
                    except Exception as error:
                        errors.append(path+': '+str(error))
                    self.report(index,len(found),'Tags lesen: '+Path(path).name)
                    if len(pending)>=32:
                        self.chunk.emit(pending); pending=[]
                if pending: self.chunk.emit(pending)
                self.completed.emit({'kind':'load','errors':errors,'count':len(found)})
            elif self.kind=='save':
                rows,with_cue,persistent=self.payload
                result=batch_save_records(rows,with_cue,persistent,self.isInterruptionRequested,self.report)
                result['kind']='save'
                self.completed.emit(result)
            elif self.kind=='undo':
                transaction=self.payload
                rows=batch_restore(transaction,verify=True,progress=self.report)
                self.completed.emit(dict(kind='undo',rows=rows,transaction=transaction))
            elif self.kind=='editor':
                path=self.payload
                record=batch_read_record(path)
                cover=extract_cover_bytes(path)
                self.completed.emit(dict(kind='editor',path=path,record=record,cover=cover,lines=get_id3_tag_lines(path)))
        except BatchCancelled:
            self.completed.emit({'kind':'cancelled'})
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(MergerWindowV43):
    def __init__(self):
        self._batch_busy=False
        self._batch_threads=[]
        self._batch_undo=[]
        self._transactions=[]
        self._load_queue=[]
        self._editor_requested=''
        self._editor_running=False
        self._editor_uid=None
        self._editor_dirty=False
        self._editor_pending=None
        self._settings=QSettings('HoerbuchMerger','V46')
        super().__init__()
        self.setWindowTitle('Hörbuch Batch-Merger PRO V46 — Merger + ID3-Batch Standalone')
        self.log_output.document().setMaximumBlockCount(4000)
        self.tree.header().setSectionsMovable(True)
        self._elapsed_timer=QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._batch_started=0
        self._last_batch_text='Bereit'
    def build_id3_tab(self):
        super().build_id3_tab()
        button=QPushButton('DDF-Vorschlag übernehmen (nur Vorschau)')
        button.clicked.connect(self.apply_ddf_suggestion)
        self.tabs.widget(2).layout().addWidget(button)
        for edit in [self.edit_artist,self.edit_title,self.edit_album,self.edit_tracknumber,
                     self.edit_discnumber,self.edit_date,self.edit_genre,self.edit_cover_path]:
            edit.textEdited.connect(self._mark_editor_dirty)
    def _mark_editor_dirty(self,*args):
        self._editor_dirty=True
    def build_id3_batch_tab(self):
        tab=QWidget()
        layout=QVBoxLayout(tab)
        bar=QHBoxLayout()
        self._batch_controls=[]
        for title,callback in [
            ('Dateien/Ordner hinzufügen',self.load_batch_folder),
            ('Liste leeren',self.clear_batch_list),
            ('Änderungen speichern',self.save_batch_changes),
            ('Unnötige ID3-Tags löschen',self.clean_batch_tags),
            ('Rückgängig',self.undo_batch)]:
            button=QPushButton(title)
            button.clicked.connect(callback)
            self._batch_controls.append(button)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.chk_batch_backup=QCheckBox('Zusätzlich dauerhafte Backups (.id3backup)')
        self.chk_batch_backup.setChecked(True)
        layout.addWidget(self.chk_batch_backup)
        self.batch_pattern_edit=QLineEdit('%artist% - %album% - $num(%track%,2) - %title%')
        layout.addWidget(self.batch_pattern_edit)
        tools=QHBoxLayout()
        self.chk_batch_cue=QCheckBox('CUE-Datei berücksichtigen')
        self.chk_batch_cue.setChecked(True)
        tools.addWidget(self.chk_batch_cue)
        for title,callback in [('Dateiname zu Tag',self.apply_filename_to_tags),('Tag zu Dateiname',self.apply_tag_to_filename)]:
            button=QPushButton(title)
            button.clicked.connect(callback)
            self._batch_controls.append(button)
            tools.addWidget(button)
        layout.addLayout(tools)
        info=QLabel('MP3s oder Ordner hierher ziehen. Strg/Shift: Mehrfachauswahl. '
                    'Alle Batch-Aktionen betreffen nur markierte Hörbücher. Änderungen und Bereinigung werden '
                    'erst bei „Änderungen speichern“ geschrieben. Spaltenüberschriften sind verschiebbar.')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.batch_model=BatchTableModel(self)
        self.batch_model.edited.connect(self._remember_preview)
        self.batch_table=BatchDropView(self)
        self.batch_table.setModel(self.batch_model)
        self.batch_table.paths_dropped.connect(self.add_batch_paths)
        self.batch_table.selectionModel().selectionChanged.connect(self._batch_selection_changed)
        self.batch_table.selectionModel().currentRowChanged.connect(self._batch_selection_changed)
        header=self.batch_table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(70)
        header.setDefaultSectionSize(135)
        self.batch_table.setColumnWidth(0,540)
        self.batch_table.setColumnWidth(10,210)
        state=self._settings.value('batch_header')
        if state is not None:
            header.restoreState(state)
        layout.addWidget(self.batch_table)
        self._batch_controls += [self.batch_table,self.batch_pattern_edit,self.chk_batch_backup,self.chk_batch_cue]
        status=QHBoxLayout()
        self.batch_progress=QProgressBar()
        self.batch_progress.setRange(0,1)
        self.batch_progress.setValue(0)
        status.addWidget(self.batch_progress)
        self.batch_cancel=QPushButton('Vorgang abbrechen')
        self.batch_cancel.setEnabled(False)
        self.batch_cancel.clicked.connect(self.cancel_batch_job)
        status.addWidget(self.batch_cancel)
        layout.addLayout(status)
        self.batch_status=QLabel('Bereit — noch keine MP3s geladen')
        self.batch_status.setWordWrap(True)
        layout.addWidget(self.batch_status)
        self.tabs.addTab(tab,'ID3-Batch')
    def selected_batch_rows(self):
        return [self.batch_model.rows[index.row()] for index in self.batch_table.selectionModel().selectedRows()]
    def _require_batch_rows(self):
        rows=self.selected_batch_rows()
        if not rows:
            QMessageBox.information(self,'Keine Auswahl','Bitte zuerst ein oder mehrere Hörbücher markieren.')
        return rows
    def _remember_preview(self,entry):
        self._batch_undo.append(entry)
    def load_batch_folder(self):
        files,_=QFileDialog.getOpenFileNames(self,'MP3-Dateien auswählen (Abbrechen: Ordner wählen)','','MP3 (*.mp3 *.MP3)')
        if not files:
            folder=QFileDialog.getExistingDirectory(self,'Ordner mit MP3s auswählen')
            files=[folder] if folder else []
        if files:
            self.add_batch_paths(files)
    def add_batch_paths(self,paths):
        if not paths:
            return
        if self._batch_busy:
            self._load_queue.extend(paths)
            return
        known={row['realpath'] for row in self.batch_model.rows}
        self._start_batch_job('load',(list(paths),known))
    def _start_batch_job(self,kind,payload):
        if self._batch_busy:
            return
        if kind in ('save','undo') and getattr(self,'worker',None) is not None and self.worker.isRunning():
            QMessageBox.warning(self,'Merge läuft','Bitte zuerst das Ende des Merge-Vorgangs abwarten.')
            return
        self._batch_busy=True
        self._batch_kind=kind
        self._batch_started=time.monotonic()
        self._last_batch_text='Vorgang gestartet'
        self.batch_progress.setRange(0,0)
        self.batch_cancel.setEnabled(kind!='undo')
        for widget in self._batch_controls:
            widget.setEnabled(False)
        self.tabs.widget(2).setEnabled(False)
        if kind in ('save','undo'):
            self.tabs.widget(0).setEnabled(False)
        self._elapsed_timer.start()
        job=BatchJob(kind,payload,self)
        self._batch_threads.append(job)
        self._active_batch_job=job
        job.progress.connect(self._batch_progress_changed)
        job.chunk.connect(self.batch_model.append)
        job.completed.connect(self._batch_completed)
        job.failed.connect(self._batch_failed)
        job.finished.connect(lambda:self._batch_job_finished(job))
        job.start()
    def _batch_progress_changed(self,current,total,text):
        if total>0:
            self.batch_progress.setRange(0,total)
            self.batch_progress.setValue(current)
            self._last_batch_text='%s / %s — %s' % (current,total,text)
        else:
            self.batch_progress.setRange(0,0)
            self._last_batch_text=text
        self._update_elapsed()
    def _update_elapsed(self):
        elapsed=int(time.monotonic()-self._batch_started)
        self.batch_status.setText(self._last_batch_text+' — '+str(elapsed)+' s')
    def _batch_completed(self,result):
        kind=result['kind']
        if kind=='load':
            errors=result['errors']
            self._last_batch_text='%s MP3s in der Liste; %s Lesefehler' % (len(self.batch_model.rows),len(errors))
            for message in errors[:50]:
                self.log(message)
            if errors:
                QMessageBox.warning(self,'Einige Dateien konnten nicht gelesen werden','\n'.join(errors[:12]))
        elif kind=='save':
            updates=result['rows']
            transaction=result['transaction']
            if transaction is not None:
                self._transactions.append(transaction)
                self._batch_undo=[entry for entry in self._batch_undo if entry['kind']=='saved']
                self._batch_undo.append({'kind':'saved','transaction':transaction})
                mapping={record['source']:record['target'] for record in transaction['records']}
                self._map_session_paths(mapping)
            self.batch_model.replace(updates)
            self._last_batch_text='%s ausgewählte MP3(s) gespeichert und geprüft' % len(updates)
            self.log(self._last_batch_text)
            self._reload_current_editor()
        elif kind=='undo':
            transaction=result['transaction']
            self.batch_model.replace(result['rows'])
            self._map_session_paths({record['target']:record['source'] for record in transaction['records']})
            if self._batch_undo and self._batch_undo[-1].get('transaction') is transaction:
                self._batch_undo.pop()
            self._last_batch_text='Gespeicherte Änderungen rückgängig gemacht'
            self._reload_current_editor()
        elif kind=='cancelled':
            self._last_batch_text='Abgebrochen. Ein bereits begonnenes Speichern wurde zurückgesetzt.' if self._batch_kind=='save' else 'Laden abgebrochen; bereits eingelesene Dateien bleiben sichtbar.'
        self._update_elapsed()
    def _map_session_paths(self,mapping):
        self.session_merged_outputs=[mapping.get(path,path) for path in self.session_merged_outputs]
        self.last_merged_output=mapping.get(self.last_merged_output,self.last_merged_output)
        self._editor_requested=mapping.get(self._editor_requested,self._editor_requested)
    def _batch_failed(self,message):
        self._last_batch_text='Vorgang fehlgeschlagen — Details im Protokoll'
        self.log(message)
        QMessageBox.warning(self,'Batch-Vorgang fehlgeschlagen',message)
    def _batch_job_finished(self,job):
        self._elapsed_timer.stop()
        self._batch_busy=False
        self.batch_cancel.setEnabled(False)
        self.batch_progress.setRange(0,1)
        self.batch_progress.setValue(1)
        self._update_elapsed()
        for widget in self._batch_controls:
            widget.setEnabled(True)
        self.tabs.widget(0).setEnabled(True)
        self.tabs.widget(2).setEnabled(True)
        if job in self._batch_threads:
            self._batch_threads.remove(job)
        job.deleteLater()
        if self._load_queue:
            paths,self._load_queue=self._load_queue,[]
            QTimer.singleShot(0,lambda:self.add_batch_paths(paths))
    def cancel_batch_job(self):
        if self._batch_busy and self._batch_kind!='undo':
            self._active_batch_job.requestInterruption()
            self.batch_cancel.setEnabled(False)
            self._last_batch_text='Abbruch angefordert; aktueller Vorgang wird sicher beendet/zurückgesetzt'
    def clear_batch_list(self):
        if self._batch_busy:
            return
        if QMessageBox.question(self,'Liste leeren','Nur die Liste leeren und ungespeicherte Vorschauen verwerfen? Dateien werden nicht gelöscht.')!=QMessageBox.Yes:
            return
        self._batch_undo.append({'kind':'clear','rows':list(self.batch_model.rows)})
        self.batch_model.reset_rows([])
        self._editor_requested=''
        self._editor_uid=None
        self._editor_dirty=False
        self.editor_current_file.setText('Keine Datei geladen')
        super().clear_editor_fields()
        self.id3_existing_list.clear()
    def _stage_batch(self,operation):
        if self._editor_dirty:
            self._stage_editor()
        rows=self._require_batch_rows()
        if not rows or self._batch_busy:
            return
        updates=[]
        try:
            for source in rows:
                row=copy.deepcopy(source)
                if operation=='parse':
                    row.update(batch_parse_filename(row['path'],self.batch_pattern_edit.text()))
                elif operation=='rename':
                    row['pending_name']=batch_render_filename(row,self.batch_pattern_edit.text())
                elif operation=='clean':
                    row['cleanup']=True
                row['dirty']=True
                updates.append(row)
        except Exception as error:
            QMessageBox.warning(self,'Keine Änderung übernommen',str(error)); return
        self._remember_preview({'kind':'preview','rows':[copy.deepcopy(row) for row in rows]})
        self.batch_model.replace(updates)
        self._batch_selection_changed()
    def apply_filename_to_tags(self):
        self._stage_batch('parse')
    def apply_tag_to_filename(self):
        self._stage_batch('rename')
    def clean_batch_tags(self):
        self._stage_batch('clean')
    def save_batch_changes(self):
        if self._editor_dirty:
            self._stage_editor()
        rows=self._require_batch_rows()
        if rows:
            self._save_rows(rows)
    def _save_rows(self,rows):
        rows=[copy.deepcopy(row) for row in rows if row['dirty']]
        if not rows:
            QMessageBox.information(self,'Keine Änderungen','Für diese Auswahl gibt es keine vorgemerkten Änderungen.'); return
        self._start_batch_job('save',(rows,self.chk_batch_cue.isChecked(),self.chk_batch_backup.isChecked()))
    def undo_batch(self):
        if self._batch_busy or not self._batch_undo:
            return
        entry=self._batch_undo[-1]
        if entry['kind']=='saved':
            self._start_batch_job('undo',entry['transaction'])
        else:
            self._batch_undo.pop()
            if entry['kind']=='clear':
                self.batch_model.reset_rows(entry['rows'])
            else:
                self.batch_model.replace(entry['rows'])
            self._reload_current_editor()
    def _batch_selection_changed(self,*args):
        if self._batch_busy:
            return
        indexes=self.batch_table.selectionModel().selectedRows()
        if not indexes:
            return
        current=self.batch_table.currentIndex().row()
        selected={index.row() for index in indexes}
        index=current if current in selected else indexes[0].row()
        self.load_id3_file(self.batch_model.rows[index]['path'],switch_tab=False)
    def load_id3_file(self,path,switch_tab=True):
        if self._editor_dirty and self._editor_uid is not None:
            self._stage_editor()
        self._editor_requested=path
        self._editor_pending=(path,switch_tab)
        QTimer.singleShot(120,self._start_editor_read)
    def _start_editor_read(self):
        if self._editor_running or self._editor_pending is None:
            return
        path,switch_tab=self._editor_pending
        self._editor_pending=None
        self._editor_running=True
        self.tabs.widget(2).setEnabled(False)
        job=BatchJob('editor',path,self)
        self._batch_threads.append(job)
        job.completed.connect(lambda result:self._editor_loaded(result,switch_tab))
        job.failed.connect(lambda message:self.log('ID3-Editor: '+message))
        job.finished.connect(lambda:self._editor_finished(job))
        job.start()
    def _editor_finished(self,job):
        self._editor_running=False
        if job in self._batch_threads:
            self._batch_threads.remove(job)
        job.deleteLater()
        if not self._batch_busy and self._editor_pending is None:
            self.tabs.widget(2).setEnabled(True)
        if self._editor_pending is not None:
            QTimer.singleShot(0,self._start_editor_read)
    def _editor_loaded(self,result,switch_tab):
        if result.get('kind')!='editor' or result['path']!=self._editor_requested:
            return
        row=next((row for row in self.batch_model.rows if row['path']==result['path']),None)
        if row is None:
            row=result['record']
            self.batch_model.append([row])
            uid=self.batch_model.by_path[row['realpath']]
            row=self.batch_model.rows[self.batch_model.by_uid[uid]]
        self._editor_uid=row['uid']
        self._editor_dirty=False
        self.editor_current_file.setText(row['path'])
        for field,edit in self._editor_widgets().items():
            edit.setText(row[field])
        self.edit_cover_path.setText(row['cover_path'])
        self.id3_existing_list.clear()
        for line in result['lines']:
            self.id3_existing_list.addItem(QListWidgetItem(line))
        self.cover_preview.clear()
        if result['cover']:
            self.show_cover_from_bytes(result['cover']['data'])
        else:
            self.cover_preview.setText('Kein Cover')
        if row['path'] in self.session_merged_outputs:
            self.current_editor_session_index=self.session_merged_outputs.index(row['path'])
        if switch_tab:
            self.tabs.setCurrentIndex(2)
    def _editor_widgets(self):
        return dict(zip(BATCH_FIELDS,[self.edit_artist,self.edit_title,self.edit_album,self.edit_tracknumber,
                                     self.edit_discnumber,self.edit_date,self.edit_genre]))
    def _stage_editor(self):
        index=self.batch_model.by_uid.get(self._editor_uid)
        if index is None:
            return None
        before=self.batch_model.rows[index]
        row=copy.deepcopy(before)
        row.update({field:edit.text().strip() for field,edit in self._editor_widgets().items()})
        row['cover_path']=self.edit_cover_path.text().strip()
        row['enabled']=list(self.gather_enabled_fields())
        row['dirty']=True
        self._remember_preview({'kind':'preview','rows':[copy.deepcopy(before)]})
        self.batch_model.replace([row])
        self._editor_dirty=False
        return row
    def save_editor_tags_to_loaded_file(self):
        if self._batch_busy:
            return
        row=self._stage_editor()
        if row is not None:
            self._save_rows([row])
    def delete_remaining_tags_from_loaded_file(self):
        index=self.batch_model.by_uid.get(self._editor_uid)
        if index is None or self._batch_busy:
            return
        before=self.batch_model.rows[index]
        row=copy.deepcopy(before)
        self._remember_preview({'kind':'preview','rows':[copy.deepcopy(before)]})
        row['cleanup'],row['dirty']=True,True
        self.batch_model.replace([row])
        QMessageBox.information(self,'Vorgemerkt','Bereinigung vorgemerkt. Erst „Änderungen speichern“ schreibt die Datei.')
    def apply_ddf_suggestion(self):
        if not self._editor_requested:
            return
        suggested=suggest_ddf_metadata(self._editor_requested)
        for field,edit in self._editor_widgets().items():
            edit.setText(suggested.get(field,''))
        self._editor_dirty=True
    def select_cover_for_editor(self):
        old=self.edit_cover_path.text()
        super().select_cover_for_editor()
        if self.edit_cover_path.text()!=old:
            self._editor_dirty=True
    def clear_editor_fields(self):
        super().clear_editor_fields()
        self._editor_dirty=True
    def show_cover_from_bytes(self,data):
        pix=QPixmap()
        pix.loadFromData(data)
        self.cover_preview.clear()
        if pix.isNull():
            self.cover_preview.setText('Kein lesbares Cover')
        else:
            self.cover_preview.setPixmap(pix.scaled(260,260,Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def _reload_current_editor(self):
        self._editor_dirty=False
        index=self.batch_model.by_uid.get(self._editor_uid)
        if index is not None:
            self.load_id3_file(self.batch_model.rows[index]['path'],switch_tab=False)
    def on_merged_file_created(self,path):
        self.last_merged_output=path
        if path not in self.session_merged_outputs:
            self.session_merged_outputs.append(path)
        self.current_editor_session_index=self.session_merged_outputs.index(path)
        self.log('Gemergte MP3 wird automatisch in ID3-Batch übernommen: '+path)
        self.add_batch_paths([path])
    def load_files(self,files):
        if self._batch_busy and self._batch_kind in ('save','undo'):
            return
        if getattr(self,'load_worker',None) is not None and self.load_worker.isRunning():
            QMessageBox.warning(self,'Laden läuft','Bitte zuerst das Ende des laufenden Einlesens abwarten.'); return
        if getattr(self,'worker',None) is not None and self.worker.isRunning():
            QMessageBox.warning(self,'Merge läuft','Bitte zuerst den Merge beenden oder abbrechen.'); return
        super().load_files(files)
    def start_batch_merge(self):
        if self._batch_busy and self._batch_kind in ('save','undo'):
            return
        if getattr(self,'load_worker',None) is not None and self.load_worker.isRunning():
            QMessageBox.warning(self,'Laden läuft','Bitte erst das Einlesen beenden.'); return
        if getattr(self,'worker',None) is not None and self.worker.isRunning():
            return
        if self.opt_delete_originals.isChecked() and QMessageBox.question(self,'Originaldateien löschen',
                'Originaldateien nach erfolgreichem Merge wirklich löschen?')!=QMessageBox.Yes:
            return
        super().start_batch_merge()
    def stop_current_work(self):
        if getattr(self,'load_worker',None) is not None and self.load_worker.isRunning():
            self.load_worker.cancel(); self.btn_stop.setEnabled(False); return
        self.stop_batch_merge()
    def on_load_cancelled(self):
        self.btn_stop.setEnabled(False)
        self.progress.setValue(0)
        self.log('Laden abgebrochen. Vorherige Daten bleiben erhalten.')
    def repair_cue_files(self):
        folder=QFileDialog.getExistingDirectory(self,'Ordner mit CUE- und MP3-Dateien')
        if not folder:
            return
        repaired,skipped,logs=repair_cue_files_in_folder(folder)
        for message in logs:
            self.log(message)
        self.log('CUE-Reparatur: %s repariert, %s unverändert/übersprungen' % (repaired,skipped))
    def closeEvent(self,event):
        active=[thread for thread in self._batch_threads if thread.isRunning()]
        main_active=any(getattr(self,name,None) is not None and getattr(self,name).isRunning() for name in ('worker','load_worker'))
        if active or main_active:
            for thread in active:
                if thread.kind!='undo': thread.requestInterruption()
            if main_active: self.stop_current_work()
            QMessageBox.information(self,'Vorgang läuft','Abbruch angefordert. Bitte das sichere Ende abwarten und danach schließen.')
            event.ignore(); return
        pending=self._editor_dirty or any(row['dirty'] for row in self.batch_model.rows)
        if pending or self._transactions:
            if QMessageBox.question(self,'Beenden','Ungespeicherte Vorschauen und Sitzungs-Rückgängig verwerfen und beenden? '
                    'Dauerhafte .id3backup-Dateien bleiben erhalten.')!=QMessageBox.Yes:
                event.ignore(); return
        self._settings.setValue('batch_header',self.batch_table.horizontalHeader().saveState())
        for transaction in self._transactions:
            shutil.rmtree(transaction['directory'],ignore_errors=True)
        event.accept()


if __name__ == '__main__':
    app=QApplication(sys.argv)
    window=MainWindow()
    window.show()
    sys.exit(app.exec_())
