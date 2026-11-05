"""Разбор живой выгрузки ВКонтакте: вики-календари и комментарии обсуждений → встречи.

Общий слой для `db/import_live.py` (заносить) и `scratch/vk_reconcile.py` (сверять): чтобы
одно и то же «что здесь написано про матч» два скрипта понимали одинаково.

Календарь лиги устроен таблицей: строка-заголовок тура («1 Тур - 28.03. Гвинея, трава»), потом
строки `['ArmFly -- Transistor', '0-5', '4-9', 'видео']`, то есть **по cell на ногу**. Ссылки
(видео, таблицы, внешние календари) приходят вместе с ячейкой: браузер отдаёт их отдельным
списком, потому что текст ячейки счёт не различает.
"""

import json
import re
import urllib.parse
from pathlib import Path

TOUR_HEAD = re.compile(r"(\d{1,2})\s*тур|тур\s*(\d{1,2})|\b№\s*(\d{1,2})\b", re.I)
PAIR_CELL = re.compile(r"^(.{3,60}?)\s*(?:--|—|–|\bvs\.?\b|\bпротив\b)\s*(.{3,60}?)$", re.I)
SCORE_CELL = re.compile(r"(\d{1,2})\s*[-:]\s*(\d{1,2})")
PARENS = re.compile(r"\([^)]*\)")


def load_pages(dump_dir):
    """Вычитанные вики-страницы: `{id: {"title", "text", "tables"}}`."""
    folder = Path(dump_dir) / "wiki_browser"
    pages = {}
    if not folder.exists():
        return pages
    for path in sorted(folder.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        pages[str(page["id"])] = page
    return pages


def cell_split(cell):
    """Ячейка бывает трёх форм: «текст» (первый проход), ['текст', [ссылок]] и ['текст', [ссылок], [строк]]."""
    if isinstance(cell, (list, tuple)):
        text = str(cell[0]) if cell else ""
        links = [str(x) for x in (cell[1] if len(cell) > 1 else [])]
        parts = [str(x) for x in (cell[2] if len(cell) > 2 else [])] or [t for t in text.split(" | ") if t]
        return text.strip(), links, parts
    return str(cell or "").strip(), [], [str(cell or "").strip()]


def clean_link(href):
    """`/away.php?to=https%3A%2F%2Fyoutube…` → настоящий адрес; короткие vk.cc оставляем как есть."""
    target = re.search(r"[?&]to=([^&]+)", href or "")
    if not target:
        return href
    return urllib.parse.unquote(target.group(1))


TEAM_SPLIT = re.compile(r"\s*(?:&|\+|/)\s*")
TEAM_VS = re.compile(r"^(.+?)\s+(?:vs\.?|--|—|–|против)\s+(.+)$", re.I)


def team_names(text):
    """«Kunio & Memori (Десять лет золота нет)» → ['Kunio', 'Memori']."""
    bare = PARENS.sub(" ", str(text or ""))
    return [part.strip() for part in TEAM_SPLIT.split(bare) if part.strip()]


def sides_from_row(full, parts):
    """Две стороны встречи из ячейки: сначала по тексту («A & B vs C & D»), потом по строкам."""
    match = TEAM_VS.match(full)
    if match:
        return team_names(match.group(1)), team_names(match.group(2))
    if len(parts) == 2 and any(sep in parts[0] for sep in "&+/"):
        return team_names(parts[0]), team_names(parts[1])
    if len(parts) == 4:
        return parts[:2], parts[2:]
    return [], []


def cell_parts(cell):
    """Строки ячейки с развернутыми сущностями: VK отдаёт «&amp;» вместо «&»."""
    _text, links, parts = cell_split(cell)
    return [urllib.parse.unquote(part) for part in parts], links, (urllib.parse.unquote(_text) or _text)


def row_blocks(row):
    """Строка календаря → блоки «сторона + её счёт(а)».

    Календарь лиги — одна колонка (`['ArmFly -- Transistor', '0-5', '4-9', 'видео']`: две ноги
    одной встречи), календарь командного турнира — две колонки рядом
    (`[состав дворовой, счёт, состав высшей, счёт]`), и блок начинается там, где ячейка снова
    похожа на пару, а не на число.
    """
    blocks = []
    for index, cell in enumerate(row):
        parts, links, full = cell_parts(cell)
        if not full or SCORE_CELL.search(full) or TOUR_HEAD.search(full):
            continue
        if len(parts) < 2 and not PAIR_CELL.match(full) and not TEAM_VS.match(full):
            continue
        scores = []
        for follower in row[index + 1:]:
            f_parts, f_links, f_full = cell_parts(follower)
            if f_full and not SCORE_CELL.search(f_full):
                break
            for a, b in SCORE_CELL.findall(f_full):
                scores.append(((int(a), int(b)), f_full, f_links))
        blocks.append({"index": index, "sides_cell": (parts, full), "scores": scores})
    return blocks


def sides_of_cell(parts, full):
    """Две стороны из ячейки: две строки (календарь в две колонки) или текст с «vs»/«--»."""
    if len(parts) >= 2:
        return team_names(parts[0]), team_names(parts[1])
    return sides_from_row(full, parts)


def team_meetings(page):
    """Встречи командного календаря: две команды по два игрока и счёт.

    Строки без счёта — встреча, которая не сыграна (или результат не записан): мы её не
    выдумываем, а отдаём в отчёт отдельным числом.
    """
    meetings, unscored = [], 0
    tours = re.findall(r"тур\s*(\d{1,2})", str(page.get("text") or ""), re.I)
    for t_index, table in enumerate(page.get("tables") or []):
        tour = f"Тур {tours[t_index]}" if t_index < len(tours) else ""
        header = table[0] if table else []
        league_by_column = {}
        for index, cell in enumerate(header):
            _, _, text = cell_parts(cell)
            if "ига" in text:
                league_by_column[index] = text
        for row in table[1:] if header else table:
            if not row:
                continue
            for block in row_blocks(row):
                parts, full = block["sides_cell"]
                names_a, names_b = sides_of_cell(parts, full)
                if len(names_a) < 2 or len(names_b) < 2:
                    continue
                if not block["scores"]:
                    unscored += 1
                    continue
                (s1, s2), note, links = block["scores"][0]
                video = [clean_link(h) for h in links if any(k in h for k in ("video", "clips", "youtu"))]
                meetings.append({"tour": tour, "page": page.get("id"), "line": full[:120],
                                 "league": league_by_column.get(block["index"], ""),
                                 "names_a": names_a, "names_b": names_b,
                                 "scores": (s1, s2), "note": note, "links": video})
    return meetings, unscored


def tour_of(head):
    match = TOUR_HEAD.search(head)
    if not match:
        return ""
    return next((g for g in match.groups() if g), "").strip()


def calendar_rows(page):
    """Встречи с календаря: сторона A, сторона B и ноги с пометками и ссылками."""
    rows = []
    tour = ""
    for table in page.get("tables") or []:
        for cells in table:
            if not cells:
                continue
            first = cell_split(cells[0])[0]
            head = " ".join(cell_split(c)[0] for c in cells).strip()
            if not first:
                continue
            pair = PAIR_CELL.match(first)
            if not pair:
                if TOUR_HEAD.search(head) and not SCORE_CELL.search(first):
                    tour = tour_of(head)
                continue
            legs = []
            for cell in cells[1:]:
                text, links, _ = cell_split(cell)
                bare = PARENS.sub(" ", text)  # «4:4 (6:5 PK)» — в скобках серия, не нога
                for a, b in SCORE_CELL.findall(bare):
                    if int(a) <= 30 and int(b) <= 30:
                        legs.append({"scores": (int(a), int(b)), "note": text, "links": links})
            if legs:
                rows.append({"tour": tour, "line": head[:160], "page": page.get("id"),
                             "raw": (pair.group(1).strip(), pair.group(2).strip()), "legs": legs})
    return rows
