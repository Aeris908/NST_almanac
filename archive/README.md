# Архив одноразовых скриптов

Файлы отсюда **не участвуют в сборке сайта** (`build_all.py` их не вызывает и никто
их не импортирует). Хранятся только как история: по ним видно, как разбирались
источники данных и какие версии портала были до текущей.

- `debug/` — одноразовые «приставки» к данным и вёрстке: `inspect_*`, `search_*`,
  `list_*`, `find_*`, `map_sections.py`, `print_nav.py`, разбор отдельных страниц
  (`parse_page2.py`, `parse_cup_rules.py`, `parse_s7_sample.py`, ...) и точечные
  правки выгруженных файлов (`expand_away_links.py`, `resolve_vk_cc.py`,
  `filter_soccer_topics.py`, `download_missing_special.py`).
- `legacy_build/` — прежние генераторы `soccer.html` и дашбордов, которые заменил
  `portal/build_soccer.py`: `build_html_site.py`, `build_clean_nekketsu_portal.py`,
  `build_nekketsu_t358_site.py`, `render_ultimate_dashboard.py`,
  `unify_all_three_tournament_tabs.py`, `upgrade_team_tournaments_view.py`,
  `build_full_team_matches.py`, `generate_full_esports_suite.py`.
  `generate_full_esports_suite.py` — оригинальный генератор `nekketsu_master_table.json`;
  живой его вариант — `build_master_table.py` + `portal/master_table.py`. Архивную копию
  запускать нельзя: она перезапишет мастер-таблицу по старой модели (победа засчитывалась
  любому матчу Сезона 8 с участием RVD независимо от данных, победителю дописывалось +3
  «призрачных» гола, а при техническом результате без упоминания RVD победа доставалась
  первой стороне, а не действительно выигравшей).

Часть скриптов импортирует модули, которые с тех пор переехали или изменились,
поэтому запускать их «как есть» уже нельзя. Если нужен такой код — сначала
почитайте, что он пишет в файлы.
