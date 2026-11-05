"""Snapshot the Sportcup API responses for the seasons the repo does not store.

Seasons 8 and 9 were rebuilt from the live API on every build, so the published
statistics depended on a third-party service staying available and unchanged.
This tool freezes those responses into ``data/sportcup_games.json`` (committed),
which ``build_final_analytics`` then reads instead of going online.

Run from the repository root:

    python collectors/sync_sportcup.py

Add ``--check`` to only report how the snapshot compares with the live API.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_final_analytics import (  # noqa: E402
    SPORTCUP_GAMES_URL,
    SPORTCUP_HEADERS,
    T_CONFIGS,
    http_get_json,
)

SNAPSHOT_PATH = Path("data/sportcup_games.json")


def fetch_stage(config):
    url = SPORTCUP_GAMES_URL.format(uuid=config["uuid"])
    return http_get_json(url, headers=SPORTCUP_HEADERS, timeout=30)


def stage_record(config, response):
    games = (response or {}).get("list", [])
    finals = [g for g in games if g.get("resultStatus") == "FINAL"]
    print(f"  {config['season']:10s} {config['league']:10s} {config['uuid']:20s} "
          f"игр {len(games):4d} (FINAL {len(finals):3d})")
    return {**{k: config[k] for k in ("season", "league", "uuid")}, "response": response}


def winner_title(game):
    """Resolve the winner uuid back to one of the two participants."""
    winner = game.get('winner')
    if not isinstance(winner, str):
        return 'нет'
    for side in (game['member1'], game['member2']):
        if isinstance(side, dict) and side.get('uuid') == winner:
            return side.get('title') or 'нет'
    return winner[:8] + '…'


def audit(snapshot_path, configs):
    """Report where the raw API flags and the rules used by the build disagree."""
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    print(f'\nАудит {snapshot_path} (fetched_at {snapshot.get("fetched_at")}):')
    for stage in snapshot['stages']:
        games = [g for g in stage['response'].get('list', [])]
        final = [g for g in games if g.get('resultStatus') == 'FINAL'
                 and g.get('scoreMember1') is not None]
        other = {}
        for g in games:
            if g.get('resultStatus') != 'FINAL':
                other[g.get('resultStatus')] = other.get(g.get('resultStatus'), 0) + 1
        technical = [g for g in final if g.get('technicalWin')]
        # То же правило, что в build_final_analytics.fetch_sportcup_matches.
        site_marked = [g for g in final
                       if stage['season'] == 'Season 8' and 'RVD' in
                       ((g['member1'].get('title') or '') + (g['member2'].get('title') or ''))]
        only_api = [g for g in technical if g not in site_marked]
        zeros = [g for g in only_api
                 if (g['scoreMember1'], g['scoreMember2'], g.get('draw')) == (0, 0, True)]
        line = (f"  {stage['season']:9s} {stage['league']:9s} сыграно {len(final):3d}"
                f" | technicalWin {len(technical):2d} | их видит сайт {len(site_marked):2d}")
        if only_api:
            line += (f" | помечено только API: {len(only_api):2d}"
                     f" (из них 0:0 считаются ничьими: {len(zeros)})")
        if other:
            line += f" | несыгранных слотов: {other}"
        print(line)
        for g in only_api:
            print(f"      {g['member1'].get('title'):16s} {g['scoreMember1']}:{g['scoreMember2']} "
                  f"{g['member2'].get('title'):16s} draw={g.get('draw')} "
                  f"winner={winner_title(g)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="compare the live API with the stored snapshot, write nothing")
    parser.add_argument("--audit", action="store_true",
                        help="report mismatches between raw API flags and the build's rules")
    args = parser.parse_args()

    if args.audit:
        if not SNAPSHOT_PATH.exists():
            sys.exit(f"{SNAPSHOT_PATH} не найден — сначала python collectors/sync_sportcup.py")
        audit(SNAPSHOT_PATH, T_CONFIGS)
        return

    stored = {}
    if SNAPSHOT_PATH.exists():
        stored = {t["uuid"]: t.get("response") for t in
                  json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))["stages"]}

    print("Fetching Sportcup stages...")
    stages = [stage_record(config, fetch_stage(config)) for config in T_CONFIGS]
    incomplete = [s for s in stages if not s["response"]]
    if incomplete:
        names = ", ".join(f"{s['season']} {s['league']}" for s in incomplete)
        sys.exit(f"Нет ответа по стейджам: {names}. Снапшот не записан: частичный снапшот "
                 f"молча убрал бы эти матчи из сборки.")

    if args.check:
        changed = [s["uuid"] for s in stages if stored.get(s["uuid"]) != s["response"]]
        print(f"\nСнапшот против живых данных: {len(stages)} стейджей, отличается: {changed or 'нет'}")
        return

    snapshot = {
        "source": SPORTCUP_GAMES_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Ответы Sportcup API по Сезонам 8-9. Единственный источник этих матчей "
                "для сборки; обновляется collectors/sync_sportcup.py.",
        "stages": stages,
    }
    SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    games = sum(len((s["response"] or {}).get("list", [])) for s in stages)
    print(f"\n{SNAPSHOT_PATH}: {len(stages)} стейджей, {games} игр, "
          f"{SNAPSHOT_PATH.stat().st_size / 1024:.0f} КБ")


if __name__ == "__main__":
    main()
