"""Scan the audio library and write the playlist manifests consumed by the site and by deploy/."""

import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
DEPLOY_AUDIO_DIR = os.path.join(BASE_DIR, "deploy", "audio")

DISCIPLINES = {
    "hub": {
        "name": "Главный хаб NST (Альманах)",
        "badge": "🏛️ ХАБ",
        "folder": "hub",
        "placeholders": [
            "Nekketsu Koukou - Title Screen (Закиньте .mp3 в audio/hub/)",
            "River City Ransom - Main Street (Закиньте .mp3 в audio/hub/)",
        ],
    },
    "soccer": {
        "name": "Футбольная лига Goal 3 (NES)",
        "badge": "⚽ ФУТБОЛ",
        "folder": "soccer",
        "placeholders": [
            "Goal 3 - Match Theme 1 (Закиньте .mp3 в audio/soccer/)",
            "Goal 3 - Match Theme 2 (Закиньте .mp3 в audio/soccer/)",
            "Goal 3 - Tournament Menu (Закиньте .mp3 в audio/soccer/)",
        ],
    },
    "quotes": {
        "name": "Золотой Цитатник (Chill & Retro)",
        "badge": "📜 ЦИТАТНИК",
        "folder": "quotes",
        "placeholders": [
            "River City Ransom - Cozy Coffee Shop (Закиньте .mp3 в audio/quotes/)",
            "Kunio Downtown - Mellow Stroll (Закиньте .mp3 в audio/quotes/)",
        ],
    },
    "hockey": {
        "name": "Хоккейная лига (Ike Ike! Nekketsu)",
        "badge": "🏒 ХОККЕЙ",
        "folder": "hockey",
        "placeholders": [
            "Nekketsu Hockey - Battle on Ice (Закиньте .mp3 в audio/hockey/)",
            "Nekketsu Hockey - Period Break (Закиньте .mp3 в audio/hockey/)",
        ],
    },
    "basketball": {
        "name": "Баскетбол 2х2 (Street Basket)",
        "badge": "🏀 БАСКЕТБОЛ",
        "folder": "basketball",
        "placeholders": ["Dunk Heroes - Florida Sun Court (Закиньте .mp3 в audio/basketball/)"],
    },
    "fighting": {
        "name": "Бои 2х2 (Kakutou Densetsu)",
        "badge": "🥊 ДРАКИ 2x2",
        "folder": "fighting",
        "placeholders": ["Kakutou Densetsu - Danger Ring (Закиньте .mp3 в audio/fighting/)"],
    },
}

AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".webm"}

# ID3 tag layout: v2 frames at the head of the file, a fixed 128-byte v1 block at the tail.
ID3V2_MAGIC = b"ID3"
ID3V2_MIN_MAJOR_VERSION = 3
ID3V2_MAX_MAJOR_VERSION = 4
ID3V2_FRAME_HEADER_SIZE = 10
ID3V2_BODY_READ_LIMIT = 65536
ID3V1_MAGIC = b"TAG"
ID3V1_BLOCK_SIZE = 128
ID3V1_TITLE = slice(3, 33)
ID3V1_ARTIST = slice(33, 63)
ID3V1_TEXT_ENCODINGS = ("utf-8", "cp1251", "latin1")
ID3_TEXT_FRAME_ENCODINGS = {0: "cp1251", 1: "utf-16", 2: "utf-16-be"}
ID3_TEXT_FRAME_DEFAULT_ENCODING = "utf-8"
ID3_FRAMES_TO_META_FIELDS = {"TIT2": "title", "TPE1": "artist", "TALB": "album"}

DEFAULT_ARTIST = "Technos Japan"
PLACEHOLDER_ALBUM = "Nekketsu Soundtrack"
PLACEHOLDER_EXTENSION = ".mp3"
# Artist labels tag editors use instead of a real name.
ANONYMOUS_ARTIST_LABELS = frozenset({"<?>", "?", "Unknown", "Unknown Artist", "Various Artists", "None", ""})

PLAYLIST_JSON_PATH = os.path.join(AUDIO_DIR, "playlist.json")
PLAYLIST_JS_PATH = os.path.join(AUDIO_DIR, "playlist-manifest.js")
DEPLOY_PLAYLIST_JSON_PATH = os.path.join(DEPLOY_AUDIO_DIR, "playlist.json")
DEPLOY_PLAYLIST_JS_PATH = os.path.join(DEPLOY_AUDIO_DIR, "playlist-manifest.js")
MANIFEST_PATHS = (PLAYLIST_JSON_PATH, PLAYLIST_JS_PATH, DEPLOY_PLAYLIST_JSON_PATH, DEPLOY_PLAYLIST_JS_PATH)


def _decode_id3v1_text(raw):
    """Decode one fixed-size ID3v1 text field, trying the encodings legacy taggers used."""
    for encoding in ID3V1_TEXT_ENCODINGS:
        try:
            return raw.decode(encoding).strip("\x00").strip()
        except UnicodeDecodeError:
            pass
    return ""


def _synchsafe_int(raw):
    """Decode a 4-byte ID3v2 synchsafe size (seven usable bits per byte)."""
    return ((raw[0] & 0x7F) << 21) | ((raw[1] & 0x7F) << 14) | ((raw[2] & 0x7F) << 7) | (raw[3] & 0x7F)


def _decode_id3v2_frame(frame_data):
    """Turn a raw ID3v2 text frame into a clean string, or None when it cannot be read."""
    if len(frame_data) < 2:
        return None
    encoding = ID3_TEXT_FRAME_ENCODINGS.get(frame_data[0], ID3_TEXT_FRAME_DEFAULT_ENCODING)
    try:
        value = frame_data[1:].decode(encoding, errors="replace").rstrip("\x00")
    except Exception:
        return None
    value = value.strip()
    return value or None


def parse_id3(file_path):
    """Pure-Python ID3v1 & ID3v2 tag parser."""
    meta = {"title": None, "artist": None, "album": None}
    if not os.path.exists(file_path) or os.path.getsize(file_path) < ID3V1_BLOCK_SIZE:
        return meta

    try:
        with open(file_path, "rb") as handle:
            header = handle.read(10)
            if len(header) == 10 and header[:3] == ID3V2_MAGIC:
                major_version = header[3]
                tag_size = _synchsafe_int(header[6:10])
                body = handle.read(min(tag_size, ID3V2_BODY_READ_LIMIT))
                index = 0
                while index < len(body) - ID3V2_FRAME_HEADER_SIZE:
                    frame_id = body[index : index + 4]
                    if frame_id[0] == 0:
                        break
                    if major_version == ID3V2_MIN_MAJOR_VERSION:
                        frame_size = int.from_bytes(body[index + 4 : index + 8], "big")
                    elif major_version == ID3V2_MAX_MAJOR_VERSION:
                        frame_size = _synchsafe_int(body[index + 4 : index + 8])
                    else:
                        break
                    frame_data = body[
                        index + ID3V2_FRAME_HEADER_SIZE : index + ID3V2_FRAME_HEADER_SIZE + frame_size
                    ]
                    index += ID3V2_FRAME_HEADER_SIZE + frame_size
                    value = _decode_id3v2_frame(frame_data)
                    if not value:
                        continue
                    field = ID3_FRAMES_TO_META_FIELDS.get(frame_id.decode("ascii", errors="ignore"))
                    if field and not meta[field]:
                        meta[field] = value

            if not meta["title"] or not meta["artist"]:
                handle.seek(-ID3V1_BLOCK_SIZE, os.SEEK_END)
                trailer = handle.read(ID3V1_BLOCK_SIZE)
                if trailer[:3] == ID3V1_MAGIC:
                    if not meta["title"]:
                        meta["title"] = _decode_id3v1_text(trailer[ID3V1_TITLE]) or meta["title"]
                    if not meta["artist"]:
                        meta["artist"] = _decode_id3v1_text(trailer[ID3V1_ARTIST]) or meta["artist"]
    except Exception:
        pass
    return meta


def clean_filename_title(filename):
    """Human title for a file without usable tags: strip track numbers, unfold underscores."""
    name, _ = os.path.splitext(filename)
    name = re.sub(r"^\d+[\s._-]+", "", name)
    name = re.sub(r"[_]+", " ", name)
    name = re.sub(r"\s*-\s*", " - ", name)
    return name.strip() or filename


def _find_audio_files(folder):
    """Audio file names in a discipline folder, sorted; an unreadable folder reads as empty."""
    try:
        entries = sorted(os.listdir(folder))
    except Exception:
        return []
    return [name for name in entries if os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS]


def _sync_deploy_folder_back(src_folder, dst_folder):
    """Adopt MP3s dropped straight into deploy/audio by copying them back into the source library."""
    for item in os.listdir(dst_folder):
        if os.path.splitext(item)[1].lower() not in AUDIO_EXTENSIONS:
            continue
        deploy_file = os.path.join(dst_folder, item)
        root_file = os.path.join(src_folder, item)
        if not os.path.exists(root_file) or os.path.getmtime(deploy_file) > os.path.getmtime(root_file):
            try:
                shutil.copy2(deploy_file, root_file)
            except Exception:
                pass


def _copy_to_deploy(source, target, filename):
    """Refresh the deployed copy when the source file is newer."""
    try:
        if not os.path.exists(target) or os.path.getmtime(source) > os.path.getmtime(target):
            shutil.copy2(source, target)
    except Exception as error:
        print(f"    Warning: Could not copy {filename} to deploy: {error}")


def _build_track(folder_name, filename, meta):
    """Playlist entry for a real audio file, titled `Artist - Track` when the artist is known."""
    artist = (meta.get("artist") or "").strip()
    if artist in ANONYMOUS_ARTIST_LABELS:
        artist = DEFAULT_ARTIST
    title = (meta.get("title") or "").strip() or clean_filename_title(filename)
    if artist and not title.lower().startswith(artist.lower()):
        title = f"{artist} - {title}"
    return {
        "title": title,
        "artist": artist,
        "album": meta.get("album") or "",
        "file": f"audio/{folder_name}/{filename}",
        "filename": filename,
        "is_placeholder": False,
    }


def _placeholder_tracks(folder_name, placeholders):
    """Playlist entries standing in for an as-yet empty discipline folder."""
    tracks = []
    for index, placeholder in enumerate(placeholders, start=1):
        filename = f"track_{index}{PLACEHOLDER_EXTENSION}"
        tracks.append(
            {
                "title": placeholder,
                "artist": DEFAULT_ARTIST,
                "album": PLACEHOLDER_ALBUM,
                "file": f"audio/{folder_name}/{filename}",
                "filename": filename,
                "is_placeholder": True,
            }
        )
    return tracks


def _scan_track(folder_name, src_folder, dst_folder, filename):
    """Read one file's tags and mirror the file into the deploy folder."""
    source = os.path.join(src_folder, filename)
    track = _build_track(folder_name, filename, parse_id3(source))
    _copy_to_deploy(source, os.path.join(dst_folder, filename), filename)
    return track


def scan_discipline(disc_info):
    """Manifest block for one discipline: real tracks when the folder has them, placeholders otherwise."""
    folder_name = disc_info["folder"]
    src_folder = os.path.join(AUDIO_DIR, folder_name)
    dst_folder = os.path.join(DEPLOY_AUDIO_DIR, folder_name)
    os.makedirs(src_folder, exist_ok=True)
    os.makedirs(dst_folder, exist_ok=True)
    _sync_deploy_folder_back(src_folder, dst_folder)

    found_files = _find_audio_files(src_folder)
    if found_files:
        print(f"  [{disc_info['badge']}] Found {len(found_files)} tracks in audio/{folder_name}/")
        tracks = [_scan_track(folder_name, src_folder, dst_folder, name) for name in found_files]
    else:
        print(f"  [{disc_info['badge']}] No files in audio/{folder_name}/ (using placeholders)")
        tracks = _placeholder_tracks(folder_name, disc_info["placeholders"])

    return {
        "name": disc_info["name"],
        "badge": disc_info["badge"],
        "folder": f"audio/{folder_name}/",
        "tracks": tracks,
    }


def _write_manifest_files(manifest):
    """Write the manifest as JSON and as a JS global, in audio/ and in deploy/audio/."""
    json_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    js_text = f"/* Auto-generated by scan_audio.py */\nwindow.NEKKETSU_AUDIO_MANIFEST = {json_text};\n"
    for path, text in (
        (PLAYLIST_JSON_PATH, json_text),
        (DEPLOY_PLAYLIST_JSON_PATH, json_text),
        (PLAYLIST_JS_PATH, js_text),
        (DEPLOY_PLAYLIST_JS_PATH, js_text),
    ):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def scan_audio_library():
    """Rebuild every discipline playlist and publish the two manifests."""
    print("=== SCANNING NEKKETSU AUDIO LIBRARY ===")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(DEPLOY_AUDIO_DIR, exist_ok=True)

    manifest = {}
    for disc_key, disc_info in DISCIPLINES.items():
        manifest[disc_key] = scan_discipline(disc_info)

    _write_manifest_files(manifest)

    print("Successfully generated:")
    for path in MANIFEST_PATHS:
        print(f"  - {path}")
    print("=== AUDIO LIBRARY SCAN COMPLETE ===\n")
    return manifest


if __name__ == "__main__":
    scan_audio_library()
