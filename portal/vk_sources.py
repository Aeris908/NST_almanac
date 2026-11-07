"""Attach verified VK comment and stream links to match dictionaries."""

from portal.name_tables import TOPIC_MAP_BY_NAME
from portal.names import clean_tok_name, homoglyph_fold

COMMENT_FIELDS = (
    ("vk_url", "vk_url"),
    ("video_url", "video_url"),
    ("vk_text", "text"),
    ("vk_date", "date"),
    ("vk_page", "page"),
)
GLOBAL_SCOPE = "global"

# Ключи архива сворачиваем по гомоглифам один раз на словарь: строк в сборке тысячи, а
# перестраивать копию на каждую было бы дороже самой сборки.
_folded_views = {}


def topic_id(season):
    """VK board id of the first topic name mentioned in the season label."""
    lowered = str(season).lower()
    for needle, tid in TOPIC_MAP_BY_NAME.items():
        if needle in lowered:
            return tid
    return None


def candidate_keys(topic, p1, p2, s1, s2):
    """Lookup keys from the most specific pairing to the loosest one."""
    p_min, p_max = min(p1, p2), max(p1, p2)
    s_min, s_max = min(s1, s2), max(s1, s2)
    if topic:
        yield f"{topic}|{p_min}|{p_max}|{s_min}|{s_max}"
        yield f"{topic}|{p1}|{p2}|{s1}|{s2}"
    yield f"{GLOBAL_SCOPE}|{p_min}|{p_max}|{s_min}|{s_max}"
    if topic:
        yield f"{topic}|{p_min}|{p_max}"


def folded_keys(topic, p1, p2, s1, s2):
    """Те же ключи по свёрнутым написаниям и в обоих порядках пары.

    Архив ключует ники так, как их написал игрок: «boр95» с кириллической «р», а база помнит
    того же человека «ВОР95». Без складки игра не находила источник вовсе — строка оставалась
    без ссылки и текста, и проверить её глазами было нельзя. Порядок пары перебираем обоими
    способами, потому что архив сортировал ники по своему написанию, а складка порядок букв
    меняет: «вор95» идёт после «centurion», а свёрнутая «bop95» — до него.
    """
    left, right = homoglyph_fold(p1), homoglyph_fold(p2)
    for a, b in ((left, right), (right, left)):
        for first, second in ((s1, s2), (s2, s1)):
            if topic:
                yield f"{topic}|{a}|{b}|{first}|{second}"
            yield f"{GLOBAL_SCOPE}|{a}|{b}|{first}|{second}"
        if topic:
            yield f"{topic}|{a}|{b}"


def folded_key(key):
    """Ключ архива с свёрнутыми написаниями; порядок слов в нём остаётся как в файле."""
    parts = str(key).split("|")
    if len(parts) < 3:
        return key
    scope, p1, p2, *rest = parts
    return "|".join((scope, homoglyph_fold(p1), homoglyph_fold(p2), *rest))


def folded_view(lookup):
    """Гомоглифная копия архива, построенная один раз на словарь."""
    cached = _folded_views.get(id(lookup))
    if cached is not None and cached[0] is lookup:
        return cached[1]
    view = {}
    for key, info in lookup.items():
        # При совпадении свёрнутых ключей остаётся первая запись файла: это другой комментарий
        # о той же паре и счёте, а не о другой игре.
        view.setdefault(folded_key(key), info)
    # Оригинал держим вместе с копией: без ссылки `id` мог бы вернуться для нового словаря.
    _folded_views[id(lookup)] = (lookup, view)
    return view


def _first_hit(lookup, keys):
    for key in keys:
        hit = lookup.get(key)
        if hit:
            return hit
    return None


def enrich_vk_source(match, lookup):
    """Add vk_url, video_url, vk_text, vk_date and vk_page from the verified archive.

    Точное совпадение ключа важнее складки: пока оно есть, строка получает ровно тот
    комментарий, что получала всегда.
    """
    p1, p2 = clean_tok_name(match.get("p1", "")), clean_tok_name(match.get("p2", ""))
    if not p1 or not p2:
        return match
    topic, s1, s2 = topic_id(match.get("season", "")), int(match.get("s1", 0)), int(match.get("s2", 0))
    source = _first_hit(
        lookup, candidate_keys(topic, p1, p2, s1, s2)
    ) or _first_hit(folded_view(lookup), folded_keys(topic, p1, p2, s1, s2))
    if source:
        for field, source_key in COMMENT_FIELDS:
            if source.get(source_key):
                match[field] = source[source_key]
    return match
