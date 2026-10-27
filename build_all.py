import subprocess
import sys
import shutil
import os

sys.stdout.reconfigure(encoding='utf-8')

print("=== BUILDING FULL NEKKETSU ALMANAC SUITE ===")

print("\n1. Scanning Audio Library & Generating Manifests (scan_audio.py)...")
subprocess.run([sys.executable, "scan_audio.py"], check=True)

print("\n2. Building Soccer Portal (soccer.html)...")
subprocess.run([sys.executable, "build_nekketsu_portal_v2.py"], check=True)

print("\n3. Building Standalone Quotes Portal (quotes.html)...")
subprocess.run([sys.executable, "build_quotes_page.py"], check=True)

print("\n4. Building 100% Non-scrolling Grand Landing Hub (index.html)...")
subprocess.run([sys.executable, "build_landing_page.py"], check=True)

print("\n5. Deploying clean bundle to /deploy folder...")
os.makedirs("deploy", exist_ok=True)

files_to_deploy = ["index.html", "soccer.html", "quotes.html", "audio-player.js", "audio-player.css"]
for f in files_to_deploy:
    if os.path.exists(f):
        shutil.copy2(f, os.path.join("deploy", f))

if os.path.exists("audio"):
    shutil.copytree("audio", os.path.join("deploy", "audio"), dirs_exist_ok=True)

print("\n=== ALL PAGES BUILT & COPIED TO 'deploy/' SUCCESSFULLY! ===")
print("Folder 'deploy/' is ready to be uploaded to hosting:")
print("  - deploy/index.html               (Main Landing Hub)")
print("  - deploy/soccer.html              (Goal 3 Soccer League)")
print("  - deploy/quotes.html              (NST Quotes Almanac)")
print("  - deploy/audio-player.js          (Persistent Audio Deck & PJAX Router)")
print("  - deploy/audio-player.css         (Retro Deck Styling)")
print("  - deploy/audio/playlist.json      (Auto-generated Audio Library)")
print("  - deploy/audio/playlist-manifest.js (Direct JS Manifest)")
print("  - deploy/audio/hub/               (Drop MP3s for Hub/Main page)")
print("  - deploy/audio/soccer/            (Drop MP3s for Goal 3 Football)")
print("  - deploy/audio/quotes/            (Drop MP3s for Quotes Almanac)")
print("  - deploy/audio/hockey/            (Drop MP3s for Hockey League)")
print("  - deploy/audio/basketball/        (Drop MP3s for Basketball 2x2)")
print("  - deploy/audio/fighting/          (Drop MP3s for Fighting 2x2)")
