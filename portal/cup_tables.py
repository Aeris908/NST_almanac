"""Hand-verified Cup of the Leagues results for the early seasons.

`champion`/`runner_up` страница читает отсюда же, а игры — из базы: справочник питает
`db/import_stores.py`, а не сборку страницы (см. `db/catalog.py: cup_rows_from_db()`).
"""

# Сезон без подписанного года в `prepare_site_data.seasons_data` попадает в базу с этим.
DEFAULT_CUP_YEAR = "2018"

HISTORIC_CUPS_DATA = {
  "Season 2": {
    "champion": "mafuta",
    "runner_up": "Kunio",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Kipriot",
        "p2": "Romario",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Transistor",
        "p2": "wanchous",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Dopi",
        "p2": "Кирпич57",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "TubusTD",
        "p2": "Rustin Cohle",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Dopi",
        "p2": "Dr1N",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Transistor",
        "p2": "BOР95",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "TubusTD",
        "p2": "Ric25",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Huba Buba",
        "p2": "Kipriot",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Dopi",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Huba Buba",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Memori",
        "p2": "TubusTD",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Kunio",
        "p2": "Transistor",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Memori",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Kunio",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "Kunio",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 3": {
    "champion": "mafuta",
    "runner_up": "BOР95",
    "matches": [
      {
        "tour": "1/8 финала",
        "p1": "BOР95",
        "p2": "Flash",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Ric25",
        "p2": "Dopi",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "mafuta",
        "p2": "Сenturion",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "ectoPower",
        "p2": "ArmFly",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "BOР95",
        "p2": "Ric25",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "BOР95",
        "p2": "Kunio",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Memori",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "BOР95",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 4": {
    "champion": "mafuta",
    "runner_up": "Transistor",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "3aBuCTb",
        "p2": "FC Pushistik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Romix",
        "p2": "Aeris",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "TubusTD",
        "p2": "Flash",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "high",
        "p2": "Kubik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kipriot",
        "p2": "3aBuCTb",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "izzzotope",
        "p2": "Romix",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kunio",
        "p2": "high",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Ric25",
        "p2": "TubusTD",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "izzzotope",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Kipriot",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Transistor",
        "p2": "Kunio",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Буц",
        "p2": "Ric25",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Kipriot",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Transistor",
        "p2": "Буц",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "Transistor",
        "s1": 5,
        "s2": 3,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 5": {
    "champion": "RVD (МГБ)",
    "runner_up": "PacnyTHuK",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Romix",
        "p2": "Kubik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "СentZloy",
        "p2": "Jamlight",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "RVD (МГБ)",
        "p2": "Chocopie",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "RVD (МГБ)",
        "p2": "Kunio",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "FC Pushistik",
        "p2": "СentZloy",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Romix",
        "p2": "Ric25",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "LiptOn",
        "p2": "Texas",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "RVD (МГБ)",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "izzzotope",
        "p2": "Romix",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "LiptOn",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "PacnyTHuK",
        "p2": "FC Pushistik",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "RVD (МГБ)",
        "p2": "mafuta",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "PacnyTHuK",
        "p2": "izzzotope",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "RVD (МГБ)",
        "p2": "PacnyTHuK",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 6": {
    "champion": "ectoPower",
    "runner_up": "Transistor",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Memori",
        "p2": "E_not",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Tymoschuk",
        "p2": "dynamik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Rock",
        "p2": "yoxter",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Tymoschuk",
        "p2": "LiptOn",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Memori",
        "p2": "FC Pushistik",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Rock",
        "p2": "Ric25",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Transistor",
        "p2": "Huba Buba",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Memori",
        "p2": "Romix",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Rock",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Transistor",
        "p2": "Tymoschuk",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Centurion",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "ectoPower",
        "p2": "Memori",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Transistor",
        "p2": "mafuta",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "ectoPower",
        "p2": "Transistor",
        "s1": 5,
        "s2": 4,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 7": {
    "champion": "ectoPower",
    "runner_up": "RVD (МГБ)",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Yuliy_Cezar",
        "p2": "RASH",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Aeris",
        "p2": "ruby",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "leonudomlya",
        "p2": "wanchous",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Bubnov",
        "p2": "leonudomlya",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kunio",
        "p2": "Aeris",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Cyneprepou4uk",
        "p2": "E_not",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Memori",
        "p2": "Yuliy_Cezar",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "RVD (МГБ)",
        "p2": "Bubnov",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Kunio",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Romix",
        "p2": "Memori",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Cyneprepou4uk",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "RVD (МГБ)",
        "p2": "Romix",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "ectoPower",
        "p2": "mafuta",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "ectoPower",
        "p2": "RVD (МГБ)",
        "s1": 5,
        "s2": 3,
        "league": "Кубок лиг"
      }
    ]
  }
}
