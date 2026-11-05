"""The JSON blob embedded into the soccer page template."""

from portal.templates import group_thousands


def score_goals(raw_score):
    """Total goals in a ``"6:2"`` style score; anything unparseable counts as zero."""
    home, _, away = str(raw_score or "").partition(":")
    return (int(home) if home.isdigit() else 0) + (int(away) if away.isdigit() else 0)


def team_fixtures(team_tournaments):
    """Count and goals of the 2x2 playoff games stored inside the team tournaments."""
    rows = [m for tournament in team_tournaments for m in (tournament.get("playoff_matches") or [])]
    return len(rows), sum(score_goals(m.get("score")) for m in rows)


def headline_stats(data, combined_matches, profiles, seasons):
    """Headline numbers shown on the hub and in the soccer header.

    Both templates used to hardcode these, and the digits had drifted from the pool;
    the hub reads them from ``data/headline_stats.json`` written by the soccer build.
    """
    special = seasons["special_matches"]
    team_count, team_goals = team_fixtures(data.team_tournaments)
    league_goals = sum(m["s1"] + m["s2"] for m in combined_matches)
    special_goals = sum(m.get("s1", 0) + m.get("s2", 0) for m in special)
    authors = {
        str(q.get("author", "")).strip().lower() for q in data.quotes if q.get("author")
    }
    return {
        "matches": len(combined_matches) + team_count + len(special),
        "league_matches": len(combined_matches),
        "team_matches": team_count,
        "special_matches": len(special),
        "goals": league_goals + team_goals + special_goals,
        "players": len(profiles),
        "seasons": len(seasons["seasons_list"]),
        "videos": sum(1 for m in [*combined_matches, *special] if m.get("video_url")),
        "quotes": len(data.quotes),
        "quote_authors": len(authors),
    }


def headline_tokens(headline):
    """Template markers for the headline block, formatted for display."""
    return {
        "MATCHES": group_thousands(headline["matches"]),
        "LEAGUE_MATCHES": group_thousands(headline["league_matches"]),
        "GOALS": group_thousands(headline["goals"]),
        "PLAYERS": group_thousands(headline["players"]),
        "SEASONS": str(headline["seasons"]),
        "VIDEOS": group_thousands(headline["videos"]),
        "QUOTES": group_thousands(headline["quotes"]),
        "QUOTE_AUTHORS": str(headline["quote_authors"]),
    }


def build(data, combined_matches: list, profiles: list, seasons: dict, analytics: dict) -> dict:
    total_goals = sum(m["s1"] + m["s2"] for m in combined_matches)
    return {
        "metadata": {
            "total_matches_analyzed": len(combined_matches),
            "total_goals_recorded": total_goals,
            "total_ot_pk_matches": sum(1 for m in combined_matches if m.get("ot") or m.get("pk")),
            "avg_goals_per_match": round(total_goals / len(combined_matches), 2),
            "total_players_tracked": len(profiles),
            "active_players_count": seasons["active_count"],
            "inactive_players_count": seasons["inactive_count"],
        },
        "headline": headline_stats(data, combined_matches, profiles, seasons),
        "profiles": profiles,
        "seasons": seasons["seasons_list"],
        "season_rosters": seasons["season_rosters"],
        "divisions": data.master_db["divisions"],
        "clutch_index": data.master_db["clutch_and_overtime_index"],
        "records": data.master_db["all_time_records"],
        "rivalries": data.master_db["kryptonite_rivalries"],
        "special_tournaments": data.special_tournaments,
        "team_tournaments": data.team_tournaments,
        "special_matches": seasons["special_matches"],
        "medal_leaders": analytics["medal_leaders"],
        "clean_sheet_leaders": analytics["clean_sheet_leaders"],
        "clutch_leaders": analytics["clutch_leaders"],
        "spec_attacking": analytics["spec_attacking"],
        "spec_defensive": analytics["spec_defensive"],
        "top_scorers_leaders": analytics["top_scorers_leaders"],
        "veterans_longevity": analytics["veterans_longevity"],
    }
