"""Attach verified VK comment and stream links to match dictionaries."""

from portal.name_tables import TOPIC_MAP_BY_NAME
from portal.names import clean_tok_name

COMMENT_FIELDS = (
    ("vk_url", "vk_url"),
    ("video_url", "video_url"),
    ("vk_text", "text"),
    ("vk_date", "date"),
    ("vk_page", "page"),
)
GLOBAL_SCOPE = "global"


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


def _first_hit(lookup, keys):
    for key in keys:
        hit = lookup.get(key)
        if hit:
            return hit
    return None


def enrich_vk_source(match, lookup):
    """Add vk_url, video_url, vk_text, vk_date and vk_page from the verified archive."""
    p1, p2 = clean_tok_name(match.get("p1", "")), clean_tok_name(match.get("p2", ""))
    if not p1 or not p2:
        return match
    source = _first_hit(
        lookup,
        candidate_keys(
            topic_id(match.get("season", "")), p1, p2, int(match.get("s1", 0)), int(match.get("s2", 0))
        ),
    )
    if source:
        for field, source_key in COMMENT_FIELDS:
            if source.get(source_key):
                match[field] = source[source_key]
    return match
