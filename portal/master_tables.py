"""Редакционные справочники мастер-таблицы: лиги, титулы, ярлыки и «кумиры».

Эти таблицы никто не вычисляет из данных — их ведёт человек. Всё остальное в
``portal.master_table`` считается из пула матчей, а рейтинг — в ``portal.elo``.
"""

DOCUMENT_TITLE = "NEKKETSU SPORTS TOURNAMENTS — Kunio-kun no Nekketsu Soccer League Comprehensive Esports Database"
GAME = "Kunio-kun no Nekketsu Soccer League (Goal 3 / 热血足球)"
PLATFORM = "NES / Famicom / Dendy (Mednafen Netplay)"
COMMUNITY_URL = "https://vk.ru/nekketsu"

# Сезон считается «годом» его середины: CURRENT_YEAR — точка, от которой считается простой.
SEASON_YEAR = {
    "Season 4": 2017.0, "Season 5": 2017.5, "Season 6": 2018.0,
    "Season 7": 2022.0, "Season 8": 2024.0, "Season 9": 2025.5,
}
SEASON_ORDER = ["Season 4", "Season 5", "Season 6", "Season 7", "Season 8", "Season 9"]
CURRENT_YEAR = 2025.5

DEFAULT_TIER = "Дворовая"

LEAGUE_TIERS = {
    "ectoPower": "Высшая", "mafuta": "Высшая", "Kunio": "Высшая",
    "PacnyTHuK": "Высшая", "Romix": "Высшая", "Transistor": "Высшая",
    "RVD (МГБ)": "Высшая", "Rock": "Высшая", "Ric25": "Высшая",
    "Cyneprepou4uk": "Высшая", "leonudomlya": "Высшая", "Memori": "Высшая",
    "Kipriot": "Высшая", "izzzotope": "Высшая", "FC Pushistik": "Высшая",

    "Буц": "Средняя", "Aeris": "Средняя", "Yuliy_Cezar": "Средняя",
    "Kubik": "Средняя", "Jamlight": "Средняя",
    "Dune": "Средняя", "E_not": "Средняя", "RASH": "Средняя", "Кирпич57": "Средняя",

    "Sokol": "Дворовая", "Hanter": "Дворовая", "Ryumaru": "Дворовая",
    "frzz": "Дворовая", "yoxter": "Дворовая", "ruby": "Дворовая",
    "Taeda": "Дворовая", "Сахарок": "Дворовая",
    "Веселый Роджер": "Дворовая", "Spartacus": "Дворовая", "mikr84": "Дворовая",
    "TBP_Machiavelli": "Дворовая", "BigPlay": "Дворовая", "daz": "Дворовая",
    "blanco": "Дворовая",
}

# Титулы, статус, архетип и стиль — тоже человек. `record: None` значит «посчитать по личным встречам».
TITLES = {
    "ectoPower": {"premier": 4, "cup": 2, "minor": 0, "finals": 9, "status": "АКТИВЕН", "archetype": "The Undisputed GOAT (Сверххищник)", "playstyle": "Тотальный блицкриг"},
    "PacnyTHuK": {"premier": 0, "cup": 1, "minor": 0, "finals": 3, "status": "Активен (S8)", "archetype": "Grand Clutch Master (Клатч-машина)", "playstyle": "Тактический контрудар"},
    "Kunio": {"premier": 2, "cup": 0, "minor": 0, "finals": 4, "status": "АКТИВЕН", "archetype": "The Iron Wall (Катеначчо)", "playstyle": "Глухая позиционная оборона"},
    "Romix": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Master of Steel (Академик)", "playstyle": "Сбалансированный прессинг"},
    "mafuta": {"premier": 3, "cup": 4, "minor": 0, "finals": 8, "status": "Инактив (3.5 г.)", "archetype": "Dynasty King (Император)", "playstyle": "Классический контроль поля"},
    "Transistor": {"premier": 1, "cup": 0, "minor": 0, "finals": 3, "status": "Инактив (7.5 л.)", "archetype": "Fallen Titan (Экс-чемпион S4)", "playstyle": "Агрессивный сольный дриблинг"},
    "Rock": {"premier": 0, "cup": 0, "minor": 0, "finals": 1, "status": "АКТИВЕН", "archetype": "Chaos Fighter (Финалист S9)", "playstyle": "Вертикальный силовой футбол"},
    "Cyneprepou4uk": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Heavy Striker (Боец Вышки)", "playstyle": "Открытые перестрелки"},
    "Ric25": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Premier Gatekeeper (Страж)", "playstyle": "Вязкая плотная опека"},
    "leonudomlya": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Division Climber (Ветеран)", "playstyle": "Контратакующий стиль"},
    "RVD (МГБ)": {"premier": 0, "cup": 2, "minor": 0, "finals": 2, "status": "Инактив (1.5 г.)", "archetype": "Playoff Slayer (Кубковый хищник)", "playstyle": "Ураганная безбашенная атака"},
    "Memori": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Architect (Организатор)", "playstyle": "Позиционный комбинационный"},
    "Буц": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Battering Ram (Тяжеловес)", "playstyle": "Мощный силовой навал"},
    "Aeris": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Bridge (Ветеран двух лиг)", "playstyle": "Универсальный темповый"},
    "Yuliy_Cezar": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "OT Gladiator (Король овертаймов)", "playstyle": "Выносливый затяжной стиль"},
    "Kubik": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Anchor (Старожил Средней)", "playstyle": "Надёжный прагматичный"},
    "Jamlight": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Division Champion (Чемпион S9)", "playstyle": "Быстрые фланговые прорывы"},
    "Dune": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Midfield Engine (Мотор Средней)", "playstyle": "Плотный прессинг"},
    "E_not": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Tenacious Fighter (Неуступчивый)", "playstyle": "Борьба за подборы"},
    "RASH": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Speedster (Скоростной форвард)", "playstyle": "Быстрые удары издали"},
    "Кирпич57": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Iron Heart (Железное сердце)", "playstyle": "Бескомпромиссная борьба"},
    "Sokol": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Prodigy (Вундеркинд Двора)", "playstyle": "Сокрушительный темп во Дворе"},
    "Hanter": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Emperor (Триумфатор Двора S9)", "playstyle": "Тотальный контроль новичков"},
    "Ryumaru": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Minimalist (Минималист)", "playstyle": "Низовой сухой футбол"},
    "yoxter": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Stalwart (Ветеран Двора)", "playstyle": "Оборонительный позиционный"},
    "frzz": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Striker (Форвард Двора)", "playstyle": "Контратакующий"},
    "ruby": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Contender (Бронза S9)", "playstyle": "Аккуратная игра от обороны"},
    "Taeda": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Veteran (Боец Двора)", "playstyle": "Упорные низовые матчи"},
    "Сахарок": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Novice (Дебютант)", "playstyle": "Любительский"},
    "blanco": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "Веселый Роджер": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Jolly Pirate (Шоумен)", "playstyle": "Хаотичный открытый"},
    "Spartacus": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "mikr84": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "TBP_Machiavelli": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "BigPlay": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "daz": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
}

DEFAULT_TITLE = {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен", "archetype": "Боец", "playstyle": "Стандарт"}

NEMESIS_MATCHUPS = [
    {"rivalry": "Финал эпох: ectoPower vs PacnyTHuK", "p1": "ectoPower", "p2": "PacnyTHuK",
     "record": None,
     "notes": "Единственный игрок в мире, имеющий положительный баланс личных встреч против ectoPower!"},
    {"rivalry": "Кошмар наяву: Rock vs ectoPower", "p1": "Rock", "p2": "ectoPower",
     "record": "0W - 7L (голы 11:36)",
     "notes": "Абсолютный психологический барьер Рока: 7 матчей, 0 побед, сухой разгром в финале S9 (0:5)."},
    {"rivalry": "Стена против Стража: Kunio vs Ric25", "p1": "Kunio", "p2": "Ric25",
     "record": "4W - 0L (голы 9:3)",
     "notes": "Рик ни разу не смог вскрыть катеначчо Кунио в официальных встречах Вышки."},
    {"rivalry": "Битва ветеранов Вышки: Romix vs ectoPower", "p1": "Romix", "p2": "ectoPower",
     "record": None,
     "notes": "Ожесточённое противостояние двух старожилов лиги: Ромикс регулярно цепляет победы, но плей-офф за ectoPower."},
    {"rivalry": "Reality Check: Sokol vs Kunio", "p1": "Sokol", "p2": "Kunio",
     "record": "1W - 4L (голы 6:14)",
     "notes": "Кунио показательно деклассировал доминатора Двора в серии 1/4 финала Кубка Лиг."},
    {"rivalry": "Reality Check 2: Hanter vs Ric25", "p1": "Hanter", "p2": "Ric25",
     "record": "0W - 3L (голы 0:8)",
     "notes": "Хантер (85.7% побед во Дворе) был сметён Риком всухую в первом же раунде Кубка."},
]
