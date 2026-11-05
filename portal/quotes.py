"""Index of player quotes by canonical nickname."""

from portal.quote_tables import AUTHOR_PLAYER_ALIASES


def player_quotes_by_author(nst_quotes_raw):
    player_quotes_dict = {}
    for q in nst_quotes_raw:
        auth = q.get("author", "").strip().lower()
        p_matched = AUTHOR_PLAYER_ALIASES.get(auth)
        if not p_matched:
            for alias_k, orig_p in AUTHOR_PLAYER_ALIASES.items():
                if alias_k in auth:
                    p_matched = orig_p
                    break
        if p_matched:
            if p_matched not in player_quotes_dict:
                player_quotes_dict[p_matched] = []
            player_quotes_dict[p_matched].append(q.get("text", "").replace("\xa0", " ").strip())
    return player_quotes_dict
