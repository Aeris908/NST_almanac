"""Импорт всех матчей страницы (2 340 + 148 + 16) в единую базу — из файлов-носителей.

Носителей шесть, но склейка между ними уже сделана в `portal.match_catalog` и
`portal.season_pages`, поэтому импортёр вызывает те же функции и получает те же строки с той же
provenance (source, vk_url, vk_date). Намеренно НЕ читает собранную страницу: база кормит
страницу, а не наоборот. Совпадения с уже импортированным рейтинговым пулом помечаются
duplicate_of — матчи не удваиваются, но след второго источника остаётся виден.

Повторный запуск чист: сперва удаляются строки этого импортёра (пул не трогается), затем всё
вставляется заново. Если в базе есть записи журнала правок — импортёр останавливается.
"""

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.build_db import ensure_player, ensure_stage, ensure_tournament, slugify  # noqa: E402
from db.docs import store_docs  # noqa: E402
from db.fields import outcomes_for, phase_of  # noqa: E402
from portal import dataset  # noqa: E402
from portal.cup_tables import DEFAULT_CUP_YEAR, HISTORIC_CUPS_DATA  # noqa: E402
from portal.match_catalog import build as build_catalog  # noqa: E402
from portal.names import clean_alias  # noqa: E402
from portal.season_pages import enrich_vk_source, special_match_rows  # noqa: E402
from db import store  # noqa: E402

DB_PATH = store.DB_PATH
# Носители документов читаются с диска, а не из базы: база — это то, что импортёр пишет, и
# кормиться ею он не должен.
SPECIAL_SOURCE = ROOT / "special_tournaments_data.json"
TEAM_SOURCE = ROOT / "team_tournaments_data.json"
DOC_FIELD = {"special": "matches", "team": "playoff_matches"}
# Срез строки страницы говорит «каталог», а источник — что это правленая человеком проверка кубка:
# по нему читатель возвращает строке её исходную форму (без stage/ot/pk) и по нему же фильтр
# псевдо-кубковых строк её не трогает.
CUP_SOURCE = "cup_tables"

# Стороны, которые игроками не являются: клубные команды межсезонья Goal 4.
CLANS = {"Яжежал", "Геймклуб", "Мегадрайв", "Пластиковый татарин", "Рединский отряд"}
KO_TOKENS = ("Плей-офф", "1/", "2/", "Финал", "финал", "Четверть", "Полу",
             "Winners", "Losers", "Баттл", "Матч за")

SOURCE_BY_PREFIX = {
    "wiki_page": ("vk_wiki",),
    "sportcup_api": ("sportcup_api",),
    "season_1_archive": ("early_archive",),
}


def side_of(text):
    """'lenin1st & ectoPower' -> (['lenin1st', 'ectoPower'], исходная строка).

    Ники сохраняются как их показала сборка каталога: своя нормализация здесь породила
    93-го игрока вместо 92 (страница знает 'lenin1st' и 'High', а справочник привёл бы их к
    'Lenin1st' и 'high'). Склейка написаний — дело таблицы player_aliases и редактора, а не импорта.
    """
    tokens = [part.strip() for part in re.split(r"\s*&\s*", str(text).strip()) if part.strip()]
    return tokens, str(text).strip()


def is_playoff(row):
    haystack = " ".join(str(row.get(key) or "") for key in ("tour", "stage", "league", "score"))
    return any(token in haystack for token in KO_TOKENS)


def parse_score(value):
    match = re.match(r"^\s*(\d+)\s*[:\-–]\s*(\d+)\s*$", str(value or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


MIN_TIMESTAMP = 10 ** 8  # 1973-03-03: меньше — это не секунды, а год (кубковые строки вписаны годом)


def date_of(row):
    """(дата в ISO, точность, исходное значение). Год не превращаем в «1 января 1970»."""
    raw = row.get("vk_date")
    if isinstance(raw, int) and raw >= MIN_TIMESTAMP:
        return dt.datetime.fromtimestamp(raw, dt.timezone.utc).strftime("%Y-%m-%d"), "exact", str(raw)
    if isinstance(raw, int) and 1900 <= raw <= 2100:
        return None, "season", str(raw)
    return None, "source_order", None if raw is None else str(raw)


def split_source(raw):
    """'wiki_page_50190588' -> ('vk_wiki', 'wiki_page_50190588'); неизвестное — как есть."""
    if not raw:
        return "unknown", None
    text = str(raw)
    for prefix, (name,) in SOURCE_BY_PREFIX.items():
        if text.startswith(prefix):
            return name, text
    return text, None


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def store_rows():
    """Все строки каталога матчей прямо из носителей, без чтения собранной страницы.

    Иначе получилась бы зависимость по кругу: база кормит страницу, а страница — базу.
    Берём результат `portal.match_catalog` (склейка шести носителей) ДО фильтрации
    `season_pages`: база обязана хранить и те строки, которые витрина сейчас отсеивает,
    иначе правка в базе не сможет их вернуть. Отфильтрованное и добавленное — дело
    сборочного конвейера, он остаётся единственным местом, где это решается.

    Спец- и командные турниры отдаются документами, а не плоским списком игр: строке нужен
    документ, к которому она принадлежит, — иначе рамку турнира нельзя собрать обратно.
    """
    data = dataset.load()
    combined = build_catalog(data)
    for match in combined:
        enrich_vk_source(match, data.vk_sources_lookup)
    return {
        "league": combined,
        "special": load_json(SPECIAL_SOURCE),
        "team": load_json(TEAM_SOURCE),
        "cup": list(HISTORIC_CUPS_DATA.items()),
        "years": {season["name"]: season.get("year") for season in data.seasons_data},
        "vk_sources": data.vk_sources_lookup,
    }


def signature(names_a, names_b, s1, s2):
    """Стороны как множество «ник|счёт», без порядка: ориентация матча не важна.
    Счёт может быть None (источник записал результат словами) — потому ключ строкой."""
    left = tuple(sorted(f"{name}|{s1}" for name in names_a))
    right = tuple(sorted(f"{name}|{s2}" for name in names_b))
    return tuple(sorted([left, right]))


def score_mentions(text, s1, s2):
    """Сколько раз в описании тура эта пара показана с этим счётом (в любой ориентации)."""
    if text is None or s1 is None or s2 is None:
        return 0
    pattern = re.compile(rf"(?<!\d){s1}\s*[:\-–]\s*{s2}(?!\d)|(?<!\d){s2}\s*[:\-–]\s*{s1}(?!\d)")
    return len(pattern.findall(str(text)))


def expected_games(text, s1, s2, wiki):
    """Сколько игр с таким счётом источник действительно перечисляет в этом документе и туре.

    Это единственное честное основание спрятать строку: «daz vs yoxter 0:1, 0:1» в описании
    тура — две настоящие игры, а одна и та же строка таблицы вики, продублированная дважды, —
    одна. Если доказательств нет (текст молчит, документ не таблица турa) — не прячем ничего,
    случай уходит в кандидаты на просмотр.
    """
    mentions = score_mentions(text, s1, s2)
    if mentions:
        return mentions
    return 1 if wiki else None


IMPORTED_ROW_SETS = ("catalog", "special", "team")
# Очереди просмотра, которые импортёр пересчитывает с нуля на каждом прогоне. Чужие батчи
# (`twins_…` из db/flag_twins_for_review.py, сырые выгрузки сборщиков) не трогаем.
CONFLICTS_BATCH = "edit-conflicts_2026-11-03"
DOUBLES_BATCH = "doubles_2026-11-03"
IMPORTER_BATCHES = (CONFLICTS_BATCH, DOUBLES_BATCH)


def reset_review_queues(con):
    """Снимает старые очереди до импорта: иначе запись, оставшаяся от прошего прогона, потом
    ссылается на матч, которого уже нет, и удаление этого матча роняет сборку."""
    for batch in IMPORTER_BATCHES:
        con.execute("delete from incoming where batch = ?", (batch,))


def reset_previous_imports(con):
    """Очищает только свои срезы и только немаркированные строки.

    Правленая строка получает `manual = 1` (см. db/edit.py) и не удаляется; если при этом журнал
    правок ссылается на строку, которую импортёр всё-таки хочет удалить, — останавливаемся:
    это значит, что правка повешена на данные, которые сейчас пересоздаются, и молча её потерять
    нельзя.
    """
    placeholders = ",".join("?" for _ in IMPORTED_ROW_SETS)
    # `vk_live` — не носитель: эти строки приносит db/import_live.py и чистит он же. Если бы
    # импорт шести источников их сносил, живые результаты исчезали бы при каждой сборке.
    doomed = (f"select id from matches where row_set in ({placeholders}) and manual = 0 "
              f"and source <> 'vk_live'")
    # Проверка учитывает таблицу записи журнала: row_id у match_sides и matches — разные счётчики,
    # без table_name он даёт ложные срабатывания (и пропускает настоящие).
    dangling = con.execute(
        f"""select count(*) from corrections c
            where c.reverted_at is null and (
                (c.table_name = 'matches' and c.row_id in ({doomed}))
                or (c.table_name = 'match_sides' and c.row_id in
                    (select s.id from match_sides s where s.match_id in ({doomed})))
            )""", IMPORTED_ROW_SETS * 2).fetchone()[0]
    if dangling:
        sys.exit(f"Журнал правок ссылается на {dangling} строк(и), которые импорт пересоздаёт. "
                 f"Сначала разберитесь: python db/edit.py log")
    protected = con.execute("select count(*) from matches where manual = 1").fetchone()[0]
    # Ссылки на строки, которые сейчас пересоздаются, обнуляются до удаления: без этого удаление
    # ловит FOREIGN KEY constraint failed — очередь просмотра и пережитые правки помнят id,
    # который через секунду перестанет существовать.
    orphaned = con.execute(
        f"update incoming set matched_match_id = null where matched_match_id in ({doomed})",
        IMPORTED_ROW_SETS).rowcount
    stale_links = 0
    for field in ("duplicate_of", "hidden_by"):
        stale_links += con.execute(
            f"""update matches set {field} = null
                where {field} in ({doomed}) and (manual = 1 or row_set = 'pool')""",
            IMPORTED_ROW_SETS).rowcount
    con.execute(f"delete from match_links where match_id in ({doomed})", IMPORTED_ROW_SETS)
    # Тот же срез, что и выше: `vk_live` удаляет не этот импорт, а db/import_live.py — иначе
    # живые строки исчезали бы между шагами сборки, а очередь редактуры ссылалась бы на id,
    # которого через секунду нет (FOREIGN KEY constraint failed на удалении).
    deleted = con.execute(f"delete from matches where row_set in ({placeholders}) and manual = 0 "
                          f"and source <> 'vk_live'", IMPORTED_ROW_SETS).rowcount
    con.commit()
    if protected:
        print(f"защищено ручных строк: {protected}")
    if orphaned or stale_links:
        print(f"ссылок снято (пересоздаваемый срез): из очереди {orphaned}, между строками {stale_links}")
    return deleted


class Importer:
    """Дублем считается только та же самая игра из того же самого места: тот же `source_ref`, либо
    один и тот же документ — пост VK, конкретная страница вики или таблица турнира (`doc_id`) — в
    том же туре при той же паре и том же счёте. Пост покрывает тур целиком, поэтому «тот же пост»
    без того же тура доказательством не считается: одна пара успевает выдать одинаковый счёт в двух
    разных турах. Совпадение по одному счёту дублем тем более не считается — в серии best-of-N две
    игры 3:1 между теми же игроками это две разные игры. В таблице одного турнира повтора
    «тур + пара + счёт» в носителях нет (проверено), поэтому там он и считается вторым показом."""

    def __init__(self, con):
        self.con = con
        self.players, self.tournaments, self.stages = {}, {}, {}
        self.order = con.execute("select coalesce(max(order_in_source), -1) + 1 from matches").fetchone()[0]
        self.counts = {"new": 0, "duplicate": 0, "no_score": 0, "clan_sides": 0, "label_only": 0}
        self.unresolved = set()
        self.collisions = {}
        self.candidates = []
        self.by_key = {}
        self.existing_scores = {}
        self.manual_pair = {}
        self.conflicts = []
        self.seen = {}
        self._load_existing_keys()

    def _load_existing_keys(self):
        """Что уже лежит в базе и НЕ будет пересоздано: строки пула и ручные записи.

        Ручные строки (`manual = 1`) импортёр не трогает, но обязан заметить, что везёт ту же
        игру рядом с ручной правкой: такой случай уходит в кандидаты, а не молча удваивает матч.
        Стороны берётся подписью, а не списком игроков: у пары 2×2 игрок на игроке дал бы четыре
        комбинации, ни одна из которых не совпала бы с ключом строки, которую импортёр вычисляет
        при вставке.
        """
        rows = self.con.execute(
            """
            select m.id, m.row_set, m.source_ref, m.source_locator, m.tour, m.doc_id, m.manual,
                   m.source_place,
                   s.name as stage, l.url, sa.label as label_a, sb.label as label_b,
                   sa.score as score_a, sb.score as score_b, sa.id as side_a, sb.id as side_b
            from matches m
            join stages s on s.id = m.stage_id
            join match_sides sa on sa.match_id = m.id and sa.side_index = 0
            join match_sides sb on sb.match_id = m.id and sb.side_index = 1
            left join match_links l on l.match_id = m.id and l.kind = 'vk_post'
            where m.source_ref is not null or m.manual = 1
            order by m.order_in_source
            """
        ).fetchall()
        nicks = self._side_nicks()
        for row in rows:
            match_id, row_set = row["id"], row["row_set"]
            place = row["tour"] or row["stage"]
            # Место, которое у строки было до правки человека: иначе перенос игры в другой тур
            # (set-place) для строки без `source_ref` лишает импортёр ключа, и та же игра
            # возвращается вторым рядом.
            places = [place] if not row["source_place"] else [place, row["source_place"]]
            names_a = self.side_tokens(row["label_a"], row["side_a"], nicks)
            names_b = self.side_tokens(row["label_b"], row["side_b"], nicks)
            s1, s2 = row["score_a"], row["score_b"]
            if row["source_ref"]:
                self.by_key.setdefault(("ref", row["source_ref"], 0), (match_id, row_set))
                self.existing_scores[match_id] = (s1, s2)
            for known in places:
                doc_key = self.make_key(row["url"], row["source_locator"], known,
                                        names_a, names_b, s1, s2, doc_id=row["doc_id"])
                if doc_key:
                    self.by_key.setdefault(doc_key, (match_id, row_set))
                    if known == place:
                        self.seen[doc_key] = self.seen.get(doc_key, 0) + 1
                if row["manual"]:
                    # Ручная строка помнит себя и по паре без счёта: после правки счёта ключ
                    # документа уже не совпадёт, и источник принёс бы ту же игру вторым рядом.
                    self.manual_pair.setdefault(
                        self.pair_key(row["url"], row["source_locator"], known,
                                      names_a, names_b, doc_id=row["doc_id"]), (match_id, row_set))

    def _side_nicks(self):
        """Игроки стороны по её id — подпись источника отсутствует, например, у строк пула."""
        result = {}
        for side_id, nick in self.con.execute(
            """select sp.side_id, p.nick from side_players sp join players p on p.id = sp.player_id
               order by sp.side_id, sp.seat_index"""
        ):
            result.setdefault(side_id, []).append(nick)
        return result

    @staticmethod
    def side_tokens(label, side_id, nicks):
        return side_of(label)[0] if label else nicks.get(side_id, [])

    @staticmethod
    def document_of(url, locator, doc_id=None):
        """Что считается «одним и тем же документом источника».

        Пост VK покрывает тур целиком, поэтому сам по себе он дубля не доказывает; страница вики
        с конкретным id — доказывает; таблица турнира в базе (`doc_id`) — тоже, потому что внутри
        одной таблицы повтор «та же пара, тот же счёт, тот же тур» — это одна и та же строка.
        Грубые локаторы («весь ранний архив») в ключ не идут: там слишком крупно.
        """
        if url:
            return url
        if doc_id is not None:
            return f"doc:{doc_id}"
        return locator if (locator or "").startswith("wiki_page") else None

    @classmethod
    def pair_key(cls, url, locator, place, names_a, names_b, doc_id=None):
        doc = cls.document_of(url, locator, doc_id)
        if not doc:
            return None
        return ("manual-pair", doc, place,
                tuple(sorted([*[name for name in names_a], *[name for name in names_b]])))

    @classmethod
    def make_key(cls, url, locator, place, names_a, names_b, s1, s2, doc_id=None):
        """Ключ документа: пост VK, страница вики или таблица турнира + тур + стороны + счёт."""
        doc = cls.document_of(url, locator, doc_id)
        if not doc:
            return None
        return ("doc", doc, place, signature(names_a, names_b, s1, s2))

    def side_ids(self, tokens):
        ids = []
        for token in tokens:
            # Игрок опознаётся по написанию после clean_alias ('high' = 'High'), как именно его
            # назвал источник — остаётся в match_sides.label.
            canonical = clean_alias(token) or token
            kind = "clan" if canonical in CLANS or token in CLANS else "player"
            if kind == "clan":
                self.counts["clan_sides"] += 1
            if canonical not in self.players and not self.con.execute(
                "select 1 from players where nick = ?", (canonical,)
            ).fetchone():
                clash = self.con.execute(
                    "select nick from players where slug = ?", (slugify(canonical),)).fetchone()
                if clash:
                    # 'sokol' против 'Sokol': вторым игроком не заводим — был бы один slug на двоих,
                    # и ссылка в UI врала бы. Сторона остаётся текстом, случай — в отчёт.
                    self.collisions.setdefault(clash[0], set()).add(token)
                    self.counts["label_only"] += 1
                    continue
                self.unresolved.add(canonical)
            ids.append(ensure_player(self.con, canonical, self.players, kind=kind))
        return ids

    def add(self, *, tournament, season, kind, stage, names_a, names_b, s1, s2,
            phase="regular", playoff=False, source="unknown", source_ref=None,
            source_locator=None, note="", links=(), played_on=None,
            date_precision="source_order", label_a=None, label_b=None, primary_url=None,
            row_set="catalog", league=None, tour=None, source_page=None,
            source_text=None, source_date_raw=None, technical=False, technical_loser=None,
            series_detail=None, doc_id=None, outcomes=None, status=None):
        locator = source_locator if row_set == "catalog" else None
        place = tour or stage
        doc_key = self.make_key(primary_url, locator, place, names_a, names_b, s1, s2, doc_id)
        ref_key = ("ref", source_ref, 0) if source_ref else None

        if ref_key and ref_key in self.by_key:
            # Игра с этим `source_ref` уже лежит в базе и она правленая: немаркированные строки
            # снесены до импорта, а `source_ref` уникален по определению — вторая копия просто
            # не вставится. Правка остаётся на витрине, расчёт счёта с источником — в очередь.
            twin_id, _ = self.by_key[ref_key]
            if self.existing_scores.get(twin_id) != (s1, s2):
                self.conflicts.append((twin_id, f"{names_a} {s1}:{s2} {names_b}",
                                       str(doc_key[1] if doc_key else source_ref)))
            self.counts["duplicate"] += 1
            return twin_id

        duplicate_of = self.by_key.get(ref_key, (None, None))[0] if ref_key else None
        hidden_by = None
        if doc_key:
            nth = self.seen.get(doc_key, 0)
            twin = self.by_key.get(doc_key)
            expected = expected_games(source_text, s1, s2, wiki=not primary_url)
            if expected is None:
                if nth > 0 and twin:
                    self.candidates.append((twin[0], self.order,
                                            f"{names_a} {s1}:{s2} {names_b}", doc_key[1]))
            elif nth >= expected:
                if twin:
                    duplicate_of = duplicate_of or twin[0]
                    if twin[1] == row_set:
                        hidden_by = twin[0]
            else:
                self.seen[doc_key] = nth + 1
        if duplicate_of is None and hidden_by is None:
            pair_key = self.pair_key(primary_url, locator, place, names_a, names_b, doc_id)
            twin = self.manual_pair.get(pair_key) if pair_key else None
            if twin:
                # Источник настаивает на своём счёте, но в этой игре уже есть ручная правка:
                # правка важнее, свежая копия прячется, а спор уходит в очередь на просмотр.
                duplicate_of = twin[0]
                if twin[1] == row_set:
                    hidden_by = twin[0]
                self.conflicts.append((twin[0], f"{names_a} {s1}:{s2} {names_b}", doc_key[1] if doc_key else ""))
        tournament_id = ensure_tournament(self.con, tournament, season, self.tournaments, kind=kind)
        stage_id = ensure_stage(self.con, tournament_id, stage, self.stages)
        self.order += 1
        self.con.execute(
            "insert into matches(tournament_id, stage_id, row_set, doc_id, league, tour, is_playoff, phase,"
            " order_in_source, status, in_rating_pool, source, source_ref, source_locator, source_page,"
            " source_text, series_detail, source_date_raw, note, played_on, date_precision, duplicate_of,"
            " hidden_by)"
            " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tournament_id, stage_id, row_set, doc_id, league, tour, int(playoff), phase, self.order,
             status or ("technical" if technical else "played"), 0,
             source, source_ref, source_locator, source_page, source_text, series_detail,
             source_date_raw, note, played_on, date_precision, duplicate_of, hidden_by),
        )
        match_id = self.con.execute("select last_insert_rowid()").fetchone()[0]
        # Нога, решённая серией: счёт равный, а исход у сторон есть — его задаёт вызывающий.
        outcome_a, outcome_b = outcomes or outcomes_for(s1, s2, technical, technical_loser, names_a)
        for index, (tokens, score, outcome, label) in enumerate(
            [(names_a, s1, outcome_a, label_a), (names_b, s2, outcome_b, label_b)]
        ):
            self.con.execute(
                "insert into match_sides(match_id, side_index, outcome, score, label) values (?,?,?,?,?)",
                (match_id, index, outcome, score, label),
            )
            side_id = self.con.execute("select last_insert_rowid()").fetchone()[0]
            for seat, player_id in enumerate(self.side_ids(tokens)):
                self.con.execute("insert into side_players(side_id, player_id, seat_index) values (?,?,?)",
                                 (side_id, player_id, seat))
        for link_kind, url in links:
            self.con.execute("insert into match_links(match_id, kind, url) values (?,?,?)",
                             (match_id, link_kind, url))
        if hidden_by:
            self.counts["duplicate"] += 1
        else:
            self.counts["new"] += 1
            if ref_key:
                self.by_key.setdefault(ref_key, (match_id, row_set))
            if doc_key:
                self.by_key.setdefault(doc_key, (match_id, row_set))
        if s1 is None:
            self.counts["no_score"] += 1
        return match_id


def import_league(imp, rows):
    for row in rows:
        names_a, label_a = side_of(row["p1"])
        names_b, label_b = side_of(row["p2"])
        links = [(kind, row[key]) for kind, key in
                 (("vk_post", "vk_url"), ("video", "video_url")) if row.get(key)]
        played_on, precision, raw_date = date_of(row)
        source, locator = split_source(row.get("source"))
        imp.add(
            tournament=f"{row['season']} {row.get('league') or 'лига'}",
            season=row["season"],
            kind="cup" if "Кубок" in str(row.get("league")) else "league",
            stage=row.get("stage") or row.get("tour") or "Регулярный сезон",
            names_a=names_a, names_b=names_b, s1=row.get("s1"), s2=row.get("s2"),
            phase=phase_of(row), playoff=is_playoff(row),
            source=source, source_locator=locator,
            links=links, played_on=played_on, date_precision=precision,
            label_a=label_a, label_b=label_b, primary_url=row.get("vk_url"),
            league=row.get("league"), tour=row.get("tour"),
            source_page=row.get("vk_page"), source_text=row.get("vk_text"),
            source_date_raw=raw_date,
            technical=bool(row.get("is_technical")),
            technical_loser=row.get("technical_loser"),
            note=str(row.get("note") or ""),
        )


def import_special(imp, docs, doc_ids, vk_sources_lookup):
    for doc in docs:
        title = doc.get("title") or "Спецтурнир"
        category = doc.get("category") or "Спецтурниры"
        doc_id = doc_ids[doc["id"]]
        for row in special_match_rows([doc], vk_sources_lookup):
            names_a, label_a = side_of(row["p1"])
            names_b, label_b = side_of(row["p2"])
            links = [(kind, row[key]) for kind, key in
                     (("vk_post", "vk_url"), ("video", "video_url")) if row.get(key)]
            played_on, precision, raw_date = date_of(row)
            imp.add(
                tournament=title, season=category, kind="special",
                stage=row.get("stage") or row.get("tour") or "Турнир",
                names_a=names_a, names_b=names_b, s1=row.get("s1"), s2=row.get("s2"),
                playoff=is_playoff(row), source="special_data", source_locator=f"special:{title}",
                note=str(row.get("score") or ""), label_a=label_a, label_b=label_b,
                row_set="special", league=row.get("league"), tour=row.get("tour"),
                links=links, source_page=row.get("vk_page"), source_text=row.get("vk_text"),
                source_date_raw=raw_date, played_on=played_on, date_precision=precision,
                primary_url=row.get("vk_url"), series_detail=row.get("games"), doc_id=doc_id,
            )


def import_team(imp, docs, doc_ids):
    for doc in docs:
        for row in doc.get("playoff_matches") or []:
            names_a, label_a = side_of(row["t1"])
            names_b, label_b = side_of(row["t2"])
            parsed = parse_score(row.get("score"))
            s1, s2 = parsed if parsed else (None, None)
            if s1 is None and "Победа" in str(row.get("score")):
                winner = set(side_of(str(row["score"]).split("Победа", 1)[1])[0])
                if winner == set(names_a):
                    s1, s2 = 1, 0
                elif winner == set(names_b):
                    s1, s2 = 0, 1
            imp.add(
                tournament=doc["title"], season=doc.get("season_year") or "—",
                kind="team", stage=row.get("stage") or row.get("league") or "Плей-офф",
                names_a=names_a, names_b=names_b, s1=s1, s2=s2,
                playoff=True, source="team_data", source_locator=f"team:{doc['id']}",
                note=str(row.get("score") or ""), label_a=label_a, label_b=label_b,
                row_set="team", league=row.get("league"), tour=row.get("stage"),
                doc_id=doc_ids[doc["id"]],
            )


def import_cup(imp, cup_rows, years):
    """Проверенные игры Кубка лиг Сезонов 2–7 — из справочника `portal/cup_tables.py`.

    Это не выгрузка, а список, который ведёт человек, но в базе он обязателен: страница
    показывает эти строки, а редактор правит только то, что лежит в `matches`. Порядок
    задаётся позицией в справочнике (`CUP:Season 4#7`) — та же оговорка, что и у рукописных
    блоков пула: вставка в середину список сдвинет.
    """
    for season, cup in cup_rows:
        year = str(years.get(season) or DEFAULT_CUP_YEAR)
        for index, row in enumerate(cup["matches"]):
            names_a, label_a = side_of(row["p1"])
            names_b, label_b = side_of(row["p2"])
            imp.add(
                tournament=f"{season} Кубок лиг", season=season, kind="cup",
                stage=row["tour"], names_a=names_a, names_b=names_b,
                s1=row.get("s1"), s2=row.get("s2"),
                phase=phase_of(row), playoff=is_playoff(row),
                source=CUP_SOURCE, source_ref=f"CUP:{season}#{index}",
                source_locator=f"cup:{season}", row_set="catalog",
                league=row.get("league") or "Кубок лиг", tour=row.get("tour"),
                label_a=label_a, label_b=label_b,
                source_text=f"Кубок лиг • {row['tour']} • {row['p1']} vs {row['p2']}",
                source_date_raw=year, date_precision="season" if year.isdigit() else "source_order",
            )


SINGLES_SQL = """
select t.name, pa.nick, sa.score, pb.nick, sb.score, m.in_rating_pool, m.duplicate_of
from matches m
join tournaments t on t.id = m.tournament_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
join side_players a on a.side_id = sa.id
join side_players b on b.side_id = sb.id
join players pa on pa.id = a.player_id
join players pb on pb.id = b.player_id
where (select count(*) from side_players sp where sp.side_id = sa.id) = 1
  and (select count(*) from side_players sp where sp.side_id = sb.id) = 1
"""


def report_lookalikes(con):
    """Сколько записей из импорта страницы совпадают с рейтинговым пулом «один в один», но не
    склеены: у строк страницы нет uuid, поэтому склеить их надёжно можно только по нему."""
    pool, page = set(), set()
    pair_groups = {}
    for tournament, n1, s1, n2, s2, in_pool, duplicate_of in con.execute(SINGLES_SQL):
        if duplicate_of:
            continue
        sig = (tournament, signature([n1], [n2], s1, s2))
        (pool if in_pool else page).add(sig)
        pair_groups.setdefault((tournament, tuple(sorted([n1, n2]))), set()).add(sig)
    same = len(pool & page)
    repeated = sum(1 for sigs in pair_groups.values() if len(sigs) > 1)
    print(f"\nпохожих на матч из рейтингового пула (не склеены, ждут uuid): {same}")
    print(f"пар «те же игроки в том же турнире, но разные счета» (это разные игры серий): {repeated}")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Импорт шести носителей матчей в единую базу")
    parser.add_argument("--db", default=str(DB_PATH),
                        help="файл базы: по умолчанию data/nst.db; нужен, чтобы прогонять правки на копии")
    args = parser.parse_args(argv)
    carriers = store_rows()

    con = store.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    reset_review_queues(con)
    removed = reset_previous_imports(con)
    left = con.execute("select count(*) from matches").fetchone()[0]
    print(f"удалено строк предыдущего импорта: {removed} | осталось в базе (пул + живые "
          f"строки vk_live): {left}")

    doc_ids = {
        **store_docs(con, carriers["special"], "special", DOC_FIELD["special"]),
        **store_docs(con, carriers["team"], "team", DOC_FIELD["team"]),
    }
    imp = Importer(con)
    import_league(imp, carriers["league"])
    import_cup(imp, carriers["cup"], carriers["years"])
    import_special(imp, carriers["special"], doc_ids, carriers["vk_sources"])
    import_team(imp, carriers["team"], doc_ids)
    con.commit()

    stored = con.execute("select count(*) from matches").fetchone()[0]
    distinct = con.execute("select count(*) from matches where duplicate_of is null").fetchone()[0]
    docs = con.execute("select kind, count(*) from tournament_docs group by kind").fetchall()
    people = con.execute("select count(*) from players where kind = 'player'").fetchone()[0]
    clans = con.execute("select count(*) from players where kind = 'clan'").fetchone()[0]
    dated = con.execute("select count(*) from matches where played_on is not null").fetchone()[0]
    linked = con.execute("select count(distinct match_id) from match_links").fetchone()[0]
    print(f"новых {imp.counts['new']} | дубликатов другого источника {imp.counts['duplicate']} | "
          f"без числового счёта {imp.counts['no_score']}")
    print(f"всего строк {stored} | неповторяющихся {distinct} | игроков {people} | кланов {clans}")
    print(f"документов турниров {', '.join(f'{kind} {count}' for kind, count in docs)}")
    print(f"с датой {dated} | со ссылкой на пост или видео {linked}")
    report_lookalikes(con)
    if imp.unresolved:
        print(f"\nимён вне справочника ({len(imp.unresolved)}) — заведены новыми игроками:")
        print("   " + ", ".join(sorted(imp.unresolved)))
    if imp.collisions:
        print(f"\nнаписаний, которые совпадают по slug с уже существующим игроком "
              f"({len(imp.collisions)}) — сторона осталась текстом, решать алиасами:")
        for known, variants in sorted(imp.collisions.items()):
            print(f"   {known} ← {', '.join(sorted(variants))}")
    if imp.conflicts:
        for kept_id, label, doc in imp.conflicts:
            con.execute(
                "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
                " values (?, 'catalog', ?, ?, 'conflict', ?)",
                (CONFLICTS_BATCH, None, json.dumps({"kept_manual_id": kept_id, "source_claim": str(label),
                                                    "doc": str(doc)}, ensure_ascii=False), kept_id),
            )
        con.commit()
        print(f"\nконфликтов «источник против ручной правки»: {len(imp.conflicts)} — в incoming"
              f" batch {CONFLICTS_BATCH}, на витрине осталась ручная строка")
    if imp.candidates:
        for twin_id, order, label, doc in imp.candidates:
            con.execute(
                "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
                " values (?, 'catalog', ?, ?, 'conflict', ?)",
                (DOUBLES_BATCH, str(order), json.dumps({"kept_id": twin_id, "match": str(label),
                                                        "doc": str(doc)}, ensure_ascii=False), twin_id),
            )
        con.commit()
        print(f"\nпар без доказательства «это одна игра» (текст источника молчит): {len(imp.candidates)} —"
              f" в incoming batch {DOUBLES_BATCH}, на витрине обе строки остались")

    from db.close_cup_pairs import main as close_cup_pairs
    from db.close_early_mirrors import main as close_early_mirrors
    from db.close_sportcup_pairs import main as close_pairs
    close_pairs()
    close_cup_pairs()
    close_early_mirrors()
    return 0


if __name__ == "__main__":
    sys.exit(main())
