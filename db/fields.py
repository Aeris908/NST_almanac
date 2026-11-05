"""Распаковка полей строки матча: два независимых флага источника в одном столбце базы."""

PHASES = ("regular", "overtime", "penalties", "overtime_penalties")


def phase_of(row):
    """Источники разводят овертайм и буллиты двумя флагами; ничья в овертайме и серия буллитов — обе метки."""
    overtime, penalties = bool(row.get("ot")), bool(row.get("pk"))
    if overtime and penalties:
        return "overtime_penalties"
    if penalties:
        return "penalties"
    if overtime:
        return "overtime"
    return "regular"


def flags_of(phase):
    """Обратно к флагам страницы: (overtime, penalties)."""
    return phase in ("overtime", "overtime_penalties"), phase in ("penalties", "overtime_penalties")


def outcome_of(s1, s2):
    """Обычный матч: счёт определяет исход сторон."""
    if s1 is None or s2 is None:
        return "none", "none"
    if s1 > s2:
        return "win", "loss"
    if s1 < s2:
        return "loss", "win"
    return "draw", "draw"


def outcomes_for(s1, s2, technical, loser, names_a):
    """Технический результат: снявшаяся сторона не выиграла и не проиграла — у неё `none`.

    Иначе `ТП (ПОРАЖЕНИЕ)` превращается в обычное поражение, а вместе с ним и win_rate:
    именно так старый генератор две чужие победы записал на Кирпич57.
    """
    if not technical or not loser:
        return outcome_of(s1, s2)
    return ("none", "win") if loser in (names_a or []) else ("win", "none")
