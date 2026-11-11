# Сбор данных (не участвует в сборке сайта)

Скрипты, которые выгружают и обогащают архивные данные сообщества из ВКонтакте
(форумы, стены, комментарии, wiki-календари) и пересобирают JSON-базы в корне репозитория.

Запускать из корня репозитория (`python collectors/...py`) — пути к JSON у скриптов
относительные, они пишут в корень.

```bash
python collectors/sync_sportcup.py                   # data/sportcup_games.json (Сезоны 8-9)
python collectors/fetch_wall_chronicles.py           # wall_tournaments_posts.json
python collectors/extract_early_seasons_matches.py   # early_seasons_matches.json
python collectors/parse_all_vk_wiki_pages.py         # wiki_seasons_matches.json
python collectors/save_vk_matches.py                 # all_vk_seasons_matches.json
python collectors/merge_and_verify_all_matches.py    # проверка склейки источников
python collectors/generate_team_tournaments_data.py  # team_tournaments_data.json
python collectors/parse_special_tournaments_data.py  # special_tournaments_data.json
python collectors/generate_enhanced_vk_lookup.py     # vk_match_sources_lookup.json
python collectors/match_comments_and_videos.py       # vk_soccer_comments_cache.json
```

`fetch_avatars.py` обновляет `player_avatars.json`. `sync_sportcup.py` работает без токена:
матчи Сезонов 8–9 берутся из публичных турнирных страниц Sportcup. Локальные преобразования
готовых выгрузок (например, `merge_and_verify_all_matches.py` и
`generate_enhanced_vk_lookup.py`) также не обращаются к API и токена не требуют.
Скриптам, которые запрашивают API ВКонтакте, нужен `VK_API_TOKEN`
(см. `.env.example` в корне). Без переменной скрипт сразу завершается с понятным
сообщением и ничего не перезаписывает.

Изменённые JSON нужно закоммитить, а затем пересобрать сайт: `python build_all.py`.
