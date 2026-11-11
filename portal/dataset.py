"""Every archived dataset the soccer portal is built from."""

import json
from dataclasses import dataclass
from pathlib import Path

import prepare_site_data
from db.docs import special_from_db, team_from_db
from db.pool import DB_PATH
from db.rating_history import rating_history_from_db

QUOTES_PATH = "nst_quotes.json"
VK_SOURCES_PATH = "vk_match_sources_lookup.json"


@dataclass(frozen=True)
class SourceData:
    avatars: dict
    master_db: dict
    early_matches: list
    vk_matches: list
    wiki_matches: list
    base_matches: list
    vk_sources_lookup: dict
    team_tournaments: list
    special_tournaments: list
    quotes: list
    seasons_data: list


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_optional_json(path, default):
    try:
        return load_json(path)
    except Exception as error:
        print("Warning loading", path + ":", error)
        return default


def load(db_path=DB_PATH):
    """Всё, из чего собирается страница: игра — из базы, сырьё для базы — с диска.

    Спец- и командные турниры приходят из `db.docs`: их игры живут в `matches` на тех же правах,
    что и игры сезонов, и правка редактора должна доходить до страницы без файла-носителя.
    `db_path` нужен предпросмотру правки (`db/api.py`): он считает payload по копии базы, чтобы
    не трогать живую.
    """
    return SourceData(
        avatars=load_json("player_avatars.json"),
        master_db=load_json("nekketsu_master_table.json"),
        early_matches=load_json("early_seasons_matches.json"),
        vk_matches=load_json("all_vk_seasons_matches.json"),
        wiki_matches=load_json("wiki_seasons_matches.json"),
        base_matches=rating_history_from_db(db_path),
        vk_sources_lookup=load_optional_json(VK_SOURCES_PATH, {}),
        team_tournaments=team_from_db(db_path),
        special_tournaments=special_from_db(db_path),
        quotes=load_optional_json(QUOTES_PATH, []),
        seasons_data=prepare_site_data.seasons_data,
    )
