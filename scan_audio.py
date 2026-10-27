import os
import sys
import re
import json
import shutil

sys.stdout.reconfigure(encoding='utf-8')

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
            "River City Ransom - Main Street (Закиньте .mp3 в audio/hub/)"
        ]
    },
    "soccer": {
        "name": "Футбольная лига Goal 3 (NES)",
        "badge": "⚽ ФУТБОЛ",
        "folder": "soccer",
        "placeholders": [
            "Goal 3 - Match Theme 1 (Закиньте .mp3 в audio/soccer/)",
            "Goal 3 - Match Theme 2 (Закиньте .mp3 в audio/soccer/)",
            "Goal 3 - Tournament Menu (Закиньте .mp3 в audio/soccer/)"
        ]
    },
    "quotes": {
        "name": "Золотой Цитатник (Chill & Retro)",
        "badge": "📜 ЦИТАТНИК",
        "folder": "quotes",
        "placeholders": [
            "River City Ransom - Cozy Coffee Shop (Закиньте .mp3 в audio/quotes/)",
            "Kunio Downtown - Mellow Stroll (Закиньте .mp3 в audio/quotes/)"
        ]
    },
    "hockey": {
        "name": "Хоккейная лига (Ike Ike! Nekketsu)",
        "badge": "🏒 ХОККЕЙ",
        "folder": "hockey",
        "placeholders": [
            "Nekketsu Hockey - Battle on Ice (Закиньте .mp3 в audio/hockey/)",
            "Nekketsu Hockey - Period Break (Закиньте .mp3 в audio/hockey/)"
        ]
    },
    "basketball": {
        "name": "Баскетбол 2х2 (Street Basket)",
        "badge": "🏀 БАСКЕТБОЛ",
        "folder": "basketball",
        "placeholders": [
            "Dunk Heroes - Florida Sun Court (Закиньте .mp3 в audio/basketball/)"
        ]
    },
    "fighting": {
        "name": "Бои 2х2 (Kakutou Densetsu)",
        "badge": "🥊 ДРАКИ 2x2",
        "folder": "fighting",
        "placeholders": [
            "Kakutou Densetsu - Danger Ring (Закиньте .mp3 в audio/fighting/)"
        ]
    }
}

AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".webm"}

def parse_id3(file_path):
    """Pure-Python ID3v1 & ID3v2 tag parser."""
    meta = {"title": None, "artist": None, "album": None}
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 128:
        return meta

    try:
        with open(file_path, "rb") as f:
            # Try ID3v2
            header = f.read(10)
            if len(header) == 10 and header[:3] == b"ID3":
                major_ver = header[3]
                tag_size = ((header[6] & 0x7F) << 21) | ((header[7] & 0x7F) << 14) | ((header[8] & 0x7F) << 7) | (header[9] & 0x7F)
                body = f.read(min(tag_size, 65536))
                idx = 0
                while idx < len(body) - 10:
                    frame_id = body[idx:idx+4]
                    if frame_id[0] == 0:
                        break
                    if major_ver == 3:
                        frame_size = int.from_bytes(body[idx+4:idx+8], 'big')
                    elif major_ver == 4:
                        fs = body[idx+4:idx+8]
                        frame_size = ((fs[0] & 0x7F) << 21) | ((fs[1] & 0x7F) << 14) | ((fs[2] & 0x7F) << 7) | (fs[3] & 0x7F)
                    else:
                        break
                    header_size = 10
                    frame_data = body[idx+header_size : idx+header_size+frame_size]
                    idx += header_size + frame_size
                    if len(frame_data) < 2:
                        continue
                    enc = frame_data[0]
                    raw_val = frame_data[1:]
                    val_str = None
                    try:
                        if enc == 0: val_str = raw_val.decode('cp1251', errors='replace').rstrip('\x00')
                        elif enc == 1: val_str = raw_val.decode('utf-16', errors='replace').rstrip('\x00')
                        elif enc == 2: val_str = raw_val.decode('utf-16-be', errors='replace').rstrip('\x00')
                        else: val_str = raw_val.decode('utf-8', errors='replace').rstrip('\x00')
                    except Exception:
                        pass
                    if val_str:
                        val_str = val_str.strip()
                        id_str = frame_id.decode('ascii', errors='ignore')
                        if id_str == 'TIT2' and not meta['title']: meta['title'] = val_str
                        elif id_str == 'TPE1' and not meta['artist']: meta['artist'] = val_str
                        elif id_str == 'TALB' and not meta['album']: meta['album'] = val_str

            # Check ID3v1 if needed
            if not meta['title'] or not meta['artist']:
                f.seek(-128, os.SEEK_END)
                id3v1 = f.read(128)
                if id3v1[:3] == b"TAG":
                    def decode_v1(b):
                        for c in ['utf-8', 'cp1251', 'latin1']:
                            try:
                                return b.decode(c).strip('\x00').strip()
                            except UnicodeDecodeError:
                                pass
                        return ""
                    if not meta['title']:
                        t = decode_v1(id3v1[3:33])
                        if t: meta['title'] = t
                    if not meta['artist']:
                        a = decode_v1(id3v1[33:63])
                        if a: meta['artist'] = a
    except Exception as e:
        pass
    return meta

def clean_filename_title(filename):
    name, _ = os.path.splitext(filename)
    name = re.sub(r'^\d+[\s._-]+', '', name)
    name = re.sub(r'[_]+', ' ', name)
    name = re.sub(r'\s*-\s*', ' - ', name)
    return name.strip() or filename

def scan_audio_library():
    print("=== SCANNING NEKKETSU AUDIO LIBRARY ===")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(DEPLOY_AUDIO_DIR, exist_ok=True)

    manifest = {}

    for disc_key, disc_info in DISCIPLINES.items():
        folder_name = disc_info["folder"]
        src_folder = os.path.join(AUDIO_DIR, folder_name)
        dst_folder = os.path.join(DEPLOY_AUDIO_DIR, folder_name)
        
        os.makedirs(src_folder, exist_ok=True)
        os.makedirs(dst_folder, exist_ok=True)

        # Bi-directional sync: if user placed MP3s directly in deploy/audio, copy back to root audio
        if os.path.exists(dst_folder):
            for item in os.listdir(dst_folder):
                ext = os.path.splitext(item)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    dep_file = os.path.join(dst_folder, item)
                    root_file = os.path.join(src_folder, item)
                    if not os.path.exists(root_file) or os.path.getmtime(dep_file) > os.path.getmtime(root_file):
                        try:
                            shutil.copy2(dep_file, root_file)
                        except Exception:
                            pass

        tracks = []
        found_files = []
        try:
            for item in sorted(os.listdir(src_folder)):
                ext = os.path.splitext(item)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    found_files.append(item)
        except Exception:
            pass

        if found_files:
            print(f"  [{disc_info['badge']}] Found {len(found_files)} tracks in audio/{folder_name}/")
            for filename in found_files:
                full_path = os.path.join(src_folder, filename)
                meta = parse_id3(full_path)
                
                raw_artist = (meta.get("artist") or "").strip()
                if raw_artist in ["<?>", "?", "Unknown", "Unknown Artist", "Various Artists", "None", ""]:
                    raw_artist = "Technos Japan"
                
                raw_title = (meta.get("title") or "").strip() or clean_filename_title(filename)
                
                if raw_artist and not raw_title.lower().startswith(raw_artist.lower()):
                    display_title = f"{raw_artist} - {raw_title}"
                else:
                    display_title = raw_title

                rel_url = f"audio/{folder_name}/{filename}"
                tracks.append({
                    "title": display_title,
                    "artist": raw_artist,
                    "album": meta.get("album") or "",
                    "file": rel_url,
                    "filename": filename,
                    "is_placeholder": False
                })

                # Copy to deploy folder
                dst_file = os.path.join(dst_folder, filename)
                try:
                    if not os.path.exists(dst_file) or os.path.getmtime(full_path) > os.path.getmtime(dst_file):
                        shutil.copy2(full_path, dst_file)
                except Exception as e:
                    print(f"    Warning: Could not copy {filename} to deploy: {e}")
        else:
            print(f"  [{disc_info['badge']}] No files in audio/{folder_name}/ (using placeholders)")
            for i, ph in enumerate(disc_info["placeholders"]):
                dummy_name = f"track_{i+1}.mp3"
                tracks.append({
                    "title": ph,
                    "artist": "Technos Japan",
                    "album": "Nekketsu Soundtrack",
                    "file": f"audio/{folder_name}/{dummy_name}",
                    "filename": dummy_name,
                    "is_placeholder": True
                })

        manifest[disc_key] = {
            "name": disc_info["name"],
            "badge": disc_info["badge"],
            "folder": f"audio/{folder_name}/",
            "tracks": tracks
        }

    # 1. Write playlist.json to audio/ and deploy/audio/
    json_path = os.path.join(AUDIO_DIR, "playlist.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    deploy_json_path = os.path.join(DEPLOY_AUDIO_DIR, "playlist.json")
    with open(deploy_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 2. Write playlist-manifest.js to audio/ and deploy/audio/
    js_content = f"/* Auto-generated by scan_audio.py */\nwindow.NEKKETSU_AUDIO_MANIFEST = {json.dumps(manifest, ensure_ascii=False, indent=2)};\n"
    
    js_path = os.path.join(AUDIO_DIR, "playlist-manifest.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    deploy_js_path = os.path.join(DEPLOY_AUDIO_DIR, "playlist-manifest.js")
    with open(deploy_js_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Successfully generated:")
    print(f"  - {json_path}")
    print(f"  - {js_path}")
    print(f"  - {deploy_json_path}")
    print(f"  - {deploy_js_path}")
    print("=== AUDIO LIBRARY SCAN COMPLETE ===\n")
    return manifest

if __name__ == "__main__":
    scan_audio_library()
