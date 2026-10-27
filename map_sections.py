import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('build_nekketsu_portal_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '<style>' in l: print(f'Line {i+1}: <style>')
    if '</style>' in l: print(f'Line {i+1}: </style>')
    if '<nav class="nav-bar">' in l: print(f'Line {i+1}: <nav>')
    if '<main' in l: print(f'Line {i+1}: <main>')
    if 'id="tab-quotes"' in l: print(f'Line {i+1}: #tab-quotes')
    if 'id="tab-leaderboard"' in l: print(f'Line {i+1}: #tab-leaderboard')
    if 'id="tab-seasons"' in l: print(f'Line {i+1}: #tab-seasons')
    if 'id="tab-special-tournaments"' in l: print(f'Line {i+1}: #tab-special-tournaments')
    if 'id="tab-team-tournaments"' in l: print(f'Line {i+1}: #tab-team-tournaments')
    if 'id="tab-clutch"' in l: print(f'Line {i+1}: #tab-clutch')
    if 'id="tab-h2h"' in l: print(f'Line {i+1}: #tab-h2h')
    if 'id="tab-hall-of-fame"' in l: print(f'Line {i+1}: #tab-hall-of-fame')
    if 'function renderQuotes' in l: print(f'Line {i+1}: function renderQuotes')
    if 'function openPlayerModal' in l: print(f'Line {i+1}: function openPlayerModal')
