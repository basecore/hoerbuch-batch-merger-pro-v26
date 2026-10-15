#!/usr/bin/env python3
# --- Automatischer Modul-Installer (V40) ---
import importlib as _importlib
import subprocess as _subprocess
import sys as _sys

_REQUIRED_PACKAGES = {
    "PyQt5": "PyQt5",
    "mutagen": "mutagen",
}

for _module_name, _package_name in _REQUIRED_PACKAGES.items():
    try:
        _importlib.import_module(_module_name)
    except ImportError:
        print(f"📦 Fehlendes Paket wird installiert: {_package_name}")
        _subprocess.check_call(
            [_sys.executable, "-m", "pip", "install", "--user", _package_name]
        )

# --- Ende automatischer Modul-Installer ---

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
from mutagen import File as MutagenFile
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


# ==========================================
# ERKENNUNGS-HILFSFUNKTIONEN AUS V3/V14
# ==========================================
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


# ==========================================
# CUE / ID3 HILFSFUNKTIONEN
# ==========================================
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


def first_tag_value(tags, key, default=""):
    values = tags.get(key, []) if tags else []
    if not values:
        return default
    value = values[0]
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return value.decode(encoding, errors="replace")
            except Exception:
                pass
        return default
    return str(value)


def parse_track_number(value):
    if value is None:
        return 999
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if isinstance(value, int):
        return value if value > 0 else 999
    text = str(value).strip()
    if not text:
        return 999
    match = re.search(r'(?:track|tracknr|tracknummer|titel|nr\.?|no\.?)[\s_.:-]*(\d{1,4})', text, re.IGNORECASE)
    if not match:
        match = re.search(r'(?<!\d)(\d{1,4})(?:\s*/\s*\d{1,4})?(?!\d)', text)
    if not match:
        return 999
    try:
        number = int(match.group(1))
        return number if number > 0 else 999
    except Exception:
        return 999


def track_number_from_filename(path):
    filename = os.path.basename(path)
    stem = os.path.splitext(filename)[0]
    match = re.search(r'(?:track|tracknr|tracknummer|titel|nr\.?|no\.?)[\s_.:-]*(\d{1,4})', stem, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        return number if number > 0 else 999
    match = re.search(r'(?<!\d)(\d{1,4})(?!\d)', stem)
    if not match:
        return 999
    number = int(match.group(1))
    return number if number > 0 else 999


def normalize_story_title(title, filename):
    text = (title or '').strip()
    if not text:
        text = os.path.splitext(os.path.basename(filename))[0]

    # Führende Tracknummer entfernen
    text = re.sub(r'^\s*\d{1,4}\s*[.\-_)]?\s*', '', text)

    # Format "Geschichte - Kapitel 1_Untertitel" -> "Geschichte"
    match = re.match(
        r'^(.*?)\s*[-–]\s*Kapitel\s*\d+\s*[_:]?\s*.*$',
        text,
        flags=re.IGNORECASE
    )
    if match:
        text = match.group(1)

    # Format "Kapitel 06_Geschichte" -> "Geschichte"
    text = re.sub(
        r'^\s*(?:kapitel|track|titel|teil)\s*\d{1,4}\s*[_:.]?\s*',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Restliche übliche Endungen entfernen
    text = re.sub(r'\s*[-–:]\s*(?:teil|kapitel|track|titel)\s*\d{1,4}\s*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(?:teil|kapitel|track|titel)\s*\d{1,4}\s*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(\s*folge\s*\d{1,4}\s*\)\s*$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\[\s*bonus\s*\]\s*$', '', text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text).strip(' -_:')
    return text


def detect_story_segments(items):
    if len(items) < 4:
        return False
    runs = []
    for item in items:
        story = normalize_story_title(item.get('title', ''), item.get('filename', ''))
        if not story:
            story = 'Unbenannte Geschichte'
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
    meta = {
        'album': 'Unbekanntes_Album',
        'title': '',
        'artist': '',
        'track': 999,
        'disc': 1,
        'year': '',
        'genre': '',
        'filename': os.path.basename(path),
        'path': path,
        'category': '-',
        'story_split': False,
        'tag_error': ''
    }

    try:
        audio = MutagenFile(path, easy=True)
        tags = audio.tags if audio else None
        if tags:
            meta['album'] = first_tag_value(tags, 'album', meta['album'])
            meta['title'] = first_tag_value(tags, 'title')
            meta['artist'] = first_tag_value(tags, 'artist')
            meta['year'] = first_tag_value(tags, 'date')
            meta['genre'] = first_tag_value(tags, 'genre')
            meta['track'] = parse_track_number(tags.get('tracknumber'))
            disc_num = parse_track_number(tags.get('discnumber'))
            meta['disc'] = disc_num if disc_num and disc_num != 999 else 1
    except Exception as exc:
        meta['tag_error'] = f'EasyID3/MutagenFile: {type(exc).__name__}: {exc}'

    if meta['track'] == 999:
        try:
            id3 = ID3(path)
            for key in id3.keys():
                if key.startswith('TRCK'):
                    number = parse_track_number(getattr(id3[key], 'text', None))
                    if number != 999:
                        meta['track'] = number
                        break
        except Exception as exc:
            meta['tag_error'] = (meta['tag_error'] + '; ' if meta['tag_error'] else '') +                 f'ID3: {type(exc).__name__}: {exc}'

    if meta['disc'] == 1:
        try:
            id3 = ID3(path)
            for key in id3.keys():
                if key.startswith('TPOS'):
                    number = parse_track_number(getattr(id3[key], 'text', None))
                    if number and number != 999:
                        meta['disc'] = number
                        break
        except Exception:
            pass

    if meta['track'] == 999:
        meta['track'] = track_number_from_filename(path)

    if meta['disc'] == 1:
        match = re.search(r'CD[\s_.-]*(\d+)', path, re.IGNORECASE)
        if match:
            meta['disc'] = int(match.group(1))
            meta['cd_in_path'] = True
        else:
            meta['cd_in_path'] = False
    else:
        meta['cd_in_path'] = False
    return meta


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


def check_track_completeness(items, require_start_from_one=True):
    track_nums = sorted(set([item['track'] for item in items if isinstance(item['track'], int) and item['track'] > 0 and item['track'] != 999]))
    if not track_nums:
        return False, "Keine brauchbaren Tracknummern vorhanden."
    end = max(track_nums)
    if require_start_from_one:
        missing = [n for n in range(1, end + 1) if n not in track_nums]
    else:
        missing = [n for n in range(track_nums[0], end + 1) if n not in track_nums]
    if not missing and (track_nums[0] == 1 or not require_start_from_one):
        return True, f"Tracks vollständig: {track_nums[0]} bis {end} vorhanden."
    if track_nums[0] != 1 and require_start_from_one:
        return False, f"Tracks unvollständig: Startet bei {track_nums[0]} statt 1. Fehlend: {[n for n in range(1, track_nums[0])]}"
    return False, f"Tracks unvollständig: Fehlende Tracknummern {missing}"


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


def delete_unwanted_id3_frames(path, keep_apic=True):
    keep_prefixes = {'TPE1', 'TIT2', 'TALB', 'TPOS', 'TRCK', 'TDRC', 'TCON'}
    removed = []
    try:
        id3 = ID3(path)
        for key in list(id3.keys()):
            prefix = key[:4]
            if prefix in keep_prefixes:
                continue
            if keep_apic and prefix == 'APIC':
                continue
            removed.append(key)
            del id3[key]
        id3.save(v2_version=3)
    except Exception as e:
        removed.append(f'Fehler beim Löschen: {e}')
    return removed


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
    easy.save()

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
    id3.save(v2_version=3)


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


# ==========================================
# WORKER
# ==========================================
class LoadWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(object)
    diagnostics_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal()

    def __init__(self, file_paths, group_by_album, adv_mode, auto_multicd=True, split_stories=False):
        super().__init__()
        self.file_paths = file_paths
        self.group_by_album = group_by_album
        self.adv_mode = adv_mode
        self.auto_multicd = auto_multicd
        self.split_stories = split_stories
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        parsed_files = []
        total = len(self.file_paths)
        for i, path in enumerate(self.file_paths):
            if self._is_cancelled:
                self.cancelled_signal.emit()
                return
            self.progress_signal.emit(i + 1, total)
            meta = safe_meta_from_file(path)
            parsed_files.append(meta)
            self.diagnostics_signal.emit(
                f"🔍 [{i + 1}/{total}] Track={meta['track'] if meta['track'] != 999 else '??'} | "
                f"Disc={meta['disc']} | {meta['filename']}"
                + (f" | ⚠ {meta['tag_error']}" if meta['tag_error'] else "")
            )

        groups = defaultdict(list)
        for pf in parsed_files:
            group_key = pf['album'] if self.group_by_album and pf['album'] else os.path.dirname(pf['path'])
            groups[group_key].append(pf)

        result = defaultdict(list)
        album_reasons = {}
        for base_key, pfs in groups.items():
            is_advent = False
            if self.adv_mode and pfs:
                check_text_full = f"{base_key} {pfs[0]['filename']} {pfs[0]['title']}".lower()
                if 'advent' in check_text_full or 'weihnacht' in check_text_full or 'bescherung' in check_text_full:
                    is_advent = True

            max_disc_initial = max([pf['disc'] for pf in pfs]) if pfs else 1
            has_cd_folder = any([pf.get('cd_in_path', False) for pf in pfs])
            drop_detected = False
            kw_short_story = get_short_story_keyword(base_key)
            if self.auto_multicd and max_disc_initial == 1 and len(pfs) > 1 and not kw_short_story and not is_advent:
                drop_detected = detect_missing_discs(pfs)

            if is_advent:
                album_reasons[base_key] = "🎅 ADVENT erkannt"
                day_markers = []
                for idx, pf in enumerate(pfs):
                    day = extract_advent_day_helper(pf['filename'], pf['title'])
                    pf['day'] = day
                    if day:
                        day_markers.append(idx)
                if day_markers:
                    min_day_idx = day_markers[0]
                    for idx, pf in enumerate(pfs):
                        pf['category'] = pf['day'] if pf['day'] else ('Intro' if idx < min_day_idx else 'Outro')
                        result[base_key].append(pf)
                    continue

            if kw_short_story:
                album_reasons[base_key] = f"📚 KURZGESCHICHTEN erkannt ({kw_short_story})"
                for pf in pfs:
                    pf['category'] = extract_short_story_name(pf['title'], pf['filename']).replace('/', '-').replace(':', ' -')
                    result[base_key].append(pf)
                continue

            max_disc_after_detect = max([pf['disc'] for pf in pfs]) if pfs else 1
            if self.split_stories and max_disc_after_detect <= 1 and detect_story_segments(pfs):
                album_reasons[base_key] = "📖 MEHRERE GESCHICHTEN erkannt"
                result[base_key].extend(pfs)
                continue

            if self.auto_multicd and max_disc_after_detect > 1:
                if max_disc_initial > 1:
                    album_reasons[base_key] = "💿 MULTI-CD erkannt"
                elif drop_detected:
                    album_reasons[base_key] = "💿 MULTI-CD automatisch erkannt"
                for pf in pfs:
                    pf['category'] = f"CD {pf['disc']}"
                    result[base_key].append(pf)
            else:
                album_reasons[base_key] = "🎧 NORMALES HÖRSPIEL"
                for pf in pfs:
                    pf['category'] = '-'
                    result[base_key].append(pf)

        self.finished_signal.emit((result, album_reasons))


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
        list_file_path = '/tmp/concat_batch_list.txt'

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
                    is_story = any(item.get('story_split', False) for item in cat_items)
                    if category == '-':
                        display_name = display_base
                    elif is_story:
                        display_name = str(category)
                    elif str(category).startswith('CD ') or str(category).startswith('Tag ') or category in ['Intro', 'Outro']:
                        display_name = f"{display_base} {category}"
                    else:
                        display_name = f"{display_base} - {category}"

                    ok, msg = check_track_completeness(cat_items, require_start_from_one=(category == '-' or not is_story))
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
                            f.write(f"file '{item['path'].replace("'", "\\'")}'\n")

                    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file_path, '-c', 'copy', output_file]
                    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
                    for line in process.stderr:
                        if 'Error' in line:
                            self.log_signal.emit(line.strip())
                    process.wait()
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

                    ensure_normal_permissions(out_dir)
                    self.merged_signal.emit(output_file)
                except Exception as e:
                    self.log_signal.emit(f"❌ FEHLER: {e}")

        if os.path.exists(list_file_path):
            os.remove(list_file_path)
        self.finished_signal.emit(True)


# ==========================================
# GUI
# ==========================================
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux Mint Hörbuch Batch-Merger PRO V40 (inkl. Abbruch, User-Zielordner, Session-Navigation & kompakter Logs)")
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

        title = QLabel("🎧 Hörbuch Batch-Merger PRO V40")
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 6px 0;")
        outer.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { background:#2b2b2b; color:#ddd; padding:10px 16px; } QTabBar::tab:selected { background:#3d70b2; color:white; }")
        outer.addWidget(self.tabs)

        self.build_main_tab()
        self.build_options_tab()
        self.build_id3_tab()

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

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background:#111; color:#dcdcdc;")
        layout.addWidget(self.log_output)

        self.tabs.addTab(tab, "Hauptansicht")

    def build_options_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.opt_group_by_album = QCheckBox("Nach Album gruppieren")
        self.opt_group_by_album.setChecked(True)
        form.addRow("Gruppierung:", self.opt_group_by_album)

        self.opt_adv_mode = QCheckBox("Advent-/Weihnachts-Erkennung aktivieren")
        self.opt_adv_mode.setChecked(True)
        form.addRow("Advent-Erkennung:", self.opt_adv_mode)

        self.opt_auto_multicd = QCheckBox("MULTI-CD automatisch erkennen")
        self.opt_auto_multicd.setChecked(True)
        self.opt_auto_multicd.setToolTip(
            "Erkennt zusätzliche CDs anhand zurückspringender Track-/Dateinummern. "
            "Deaktivieren, wenn fortlaufende MP3s fälschlich aufgeteilt werden. "
            "CD-Angaben aus ID3-Tags oder Pfaden bleiben berücksichtigt. "
            "Änderungen gelten beim nächsten Einlesen der Dateien."
        )
        form.addRow("Multi-CD-Erkennung:", self.opt_auto_multicd)

        self.opt_split_stories = QCheckBox("Mehrere Geschichten pro Album trennen")
        self.opt_split_stories.setChecked(False)
        self.opt_split_stories.setToolTip(
            "Erkennt zusammenhängende Blöcke mit demselben Geschichte-Titel, z. B. "
            "'Conni kann nicht einschlafen' und 'Conni macht das Seepferdchen'. "
            "Die Ausgabedateien erhalten den jeweiligen Geschichtsnamen."
        )
        form.addRow("Geschichten trennen:", self.opt_split_stories)

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
        self.load_worker = LoadWorker(
            files, self.opt_group_by_album.isChecked(), self.opt_adv_mode.isChecked(),
            auto_multicd=self.opt_auto_multicd.isChecked(),
            split_stories=self.opt_split_stories.isChecked()
        )
        self.load_worker.progress_signal.connect(lambda c, t: self.progress.setMaximum(t) or self.progress.setValue(c))
        self.load_worker.diagnostics_signal.connect(self.log)
        self.load_worker.cancelled_signal.connect(self.on_load_cancelled)
        self.load_worker.finished_signal.connect(self.on_load_finished)
        self.btn_stop.setEnabled(True)
        self.load_worker.start()

    def on_load_cancelled(self):
        self.btn_stop.setEnabled(False)
        self.progress.setValue(0)
        self.log("🛑 Laden wurde abgebrochen. Es wurden keine Daten übernommen.")
        self.data_structure = defaultdict(list)
        self.album_reasons = {}
        self.tree.clear()
        self.reason_label.setText("Erkennung: Laden abgebrochen")
        self.track_check_label.setText("Track-Check: Laden abgebrochen")

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
        incomplete_albums = []
        for base_key, items in self.data_structure.items():
            ok, msg = check_track_completeness(items)
            name = os.path.basename(base_key) if os.path.isabs(base_key) else str(base_key)
            self.log(f"📚 {name}: {self.album_reasons.get(base_key, '-')}, {msg}")
            if not ok:
                incomplete_albums.append((name, msg))
        if incomplete_albums:
            self.log("")
            self.log("🚨 NICHT VOLLSTÄNDIGE ALBEN / FOLGEN:")
            for name, msg in incomplete_albums:
                self.log(f"🚨 {name}: {msg}")
            self.log("")
            self.log("⚠ Bitte diese Alben vor einem Batch-Merge prüfen.")
        else:
            self.log("✅ Alle geladenen Alben bzw. Folgen sind trackmäßig vollständig.")
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
                is_story = any(item.get('story_split', False) for item in cat_items)
                ok, msg = check_track_completeness(cat_items, require_start_from_one=(cat == '-' and not is_story))
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

    def stop_current_work(self):
        if hasattr(self, 'load_worker') and self.load_worker.isRunning():
            self.load_worker.cancel()
            self.log("🛑 Laden abgebrochen/Abbruch angefordert ...")
            self.btn_stop.setEnabled(False)
            return
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.log("🛑 Abbruch angefordert... Bitte warten, bis der aktuelle Vorgang stoppt.")
            self.btn_stop.setEnabled(False)
            self.update_batch_status(True, True)

    def stop_batch_merge(self):
        self.stop_current_work()

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
