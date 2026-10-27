import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open("c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\nekketsu_master_table.json", "r", encoding="utf-8") as f:
    db = json.load(f)

meta = db["metadata"]
rankings = db["power_rankings"]
p_table = db["divisions"]["premier_league"]
m_table = db["divisions"]["middle_league"]
y_table = db["divisions"]["yard_league"]
clutch = db["clutch_and_overtime_index"]
def_walls = db["defensive_walls_index"]
off_blitz = db["offensive_blitz_index"]
spectacle = db["spectacle_index"]
blowouts = db["all_time_records"]["top_blowouts"]
thrillers = db["all_time_records"]["top_thrillers"]
rivalries = db["kryptonite_rivalries"]

md = f"""# 🏆 Энциклопедический аналитический дашборд: Kunio-kun no Nekketsu Soccer League (Goal 3)
**Киберспортивное сообщество:** [NEKKETSU SPORTS TOURNAMENTS](https://vk.ru/nekketsu) (VK ID: `66162180`)  
**Платформа:** NES / Famicom / Dendy (Mednafen Netplay, хаки T349 / T355)  
**Объём проверенной базы данных:** **{meta['total_matches_analyzed']} матчей** | **{meta['total_goals_recorded']} голов** | **{meta['total_ot_pk_matches']} овертаймов/буллитов** | **{meta['total_players_tracked']} игроков**  
**Методология расчёта:** Division-Weighted Elo + **Time-Decay (Фактор давности и эволюция меты 2017–2025)**  
**Дата генерации:** 24 октября 2026 г.

---

## 📌 Раздел 1. Главные инсайты и выводы («Большая десятка»)

> [!IMPORTANT]
> 1. **Абсолютный GOAT сцены — ectoPower (Dominator Score: 928.8, Active Elo: 1743.7):**
>    - 4 титула Высшей лиги, 2 Кубка Лиг, 9 гранд-финалов, рекордные **40 побед** и феноменальная разница **+86 мячей**.
>    - В финале 9-го сезона (2025) поставил жирную точку, уничтожив Rock со счётом **5:0**.
> 2. **Фактор давности (Time-Decay) — ретро-чемпионы сошли с пьедестала:**
>    - **Транзистор (Transistor)** не играл **7.5 лет** (с 2018 года). Его исторический пик остаётся великим (**1650.2** в Зале Славы), но активный рейтинг в современной мете скорректирован до **1353.7**.
>    - Действующие лидеры Средней лиги (**Буц — 1421.1**, **Yuliy_Cezar — 1386.3**) в современной соревновательной форме закономерно стоят **выше заржавевшего Транзистора**.
>    - Доминатор Дворовой лиги **Sokol (1277.0)** подобрался к Транзистору всего на 76 очков Elo!
> 3. **«Клатч-машина» и единственный антидот против ectoPower — PacnyTHuK (Active Elo: 1691.6):**
>    - Обладатель Кубка S8 и единственный игрок лиги с положительным балансом личных встреч против ectoPower (**5W - 4L** в сериях).
> 4. **«Железный занавес» — Kunio (Active Elo: 1653.3, Чемпион S8 и S9):**
>    - Самая надёжная оборона в истории: всего **1.76 пропущенного гола за матч** среди элиты.
> 5. **«Кубковый фильтр» — иллюзия дворового доминирования:**
>    - Плей-офф Кубка Лиг регулярно деклассирует фаворитов Двора: триумфатор Двора S9 **Hanter** (85.7% побед во Дворе) был разбит в 1/8 финала старожилом Вышки **Ric25** всухую **0:3** (разница 0:8).
>    - Звезда Двора S8 **Sokol** в 1/4 финала был смят **Kunio** со счётом **1:4** (голы 6:14).
> 6. **17 голов за матч — исторический рекорд всех времён:**
>    - В 9-м сезоне в Высшей лиге состоялся самый безумный матч в истории: **Ric25 8 : 9 Memori** (17 мячей за 1 игру!).
> 7. **Самый свирепый разгром в плей-офф:**
>    - Четвертьфинал 8-го сезона: **ectoPower 9 : 0 Memori** (+9 мячей разницы).
> 8. **Гладиатор овертаймов — Yuliy_Cezar:**
>    - Сыграл рекордные **10 овертаймов/буллитов** и выиграл **7 из них (70.0%)**!
> 9. **100% клатч — Romix:**
>    - 3 овертайма в карьере — 3 победы (100% винрейт в валидольных концовках).
> 10. **Психологический барьер — «Комплекс ectoPower у Rock»:**
>     - 7 личных встреч между Rock и ectoPower закончились со счётом **0W - 7L** (голы 11:36).

---

## ⚡ Раздел 2. Актуальный Power Ranking (Общий зачёт активной меты 2025/2026)

*Игроки ранжированы по боеспособности на сегодняшний день с учётом штрафа за давность выступлений:*

| № | Игрок | Дивизион | Статус | Актуальный Elo | Пик Elo | Штраф | Матчи | W - L | WR% | Забито-Пропущено | Разница | Архетип и стиль |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(rankings[:25], 1):
    dec = f"-{p['decay_penalty']:.0f}" if p['decay_penalty'] > 0 else "0 (Актив)"
    md += f"| {i} | **{p['player']}** | {p['league']} | {p['status']} | **{p['active_elo']}** | {p['peak_elo']} | {dec} | {p['matches']} | {p['wins']}-{p['losses']} | {p['win_rate']}% | {p['goals_for']}:{p['goals_against']} | {p['goal_diff']:+d} | {p['archetype']} |\n"

md += """
---

## 🥇 Раздел 3. Высшая лига: Действующая элита и ретро-легенды

| № | Игрок | Статус | Актуальный Elo | Пик Elo | Штраф | Матчи | W - L | WR% | Разница | Титулы (Лига/Кубок) | Стиль игры |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(p_table, 1):
    dec = f"-{p['decay_penalty']:.0f}" if p['decay_penalty'] > 0 else "0"
    md += f"| {i} | **{p['player']}** | {p['status']} | **{p['active_elo']}** | {p['peak_elo']} | {dec} | {p['matches']} | {p['wins']}-{p['losses']} | {p['win_rate']}% | {p['goal_diff']:+d} | 🏆 {p['premier_titles']} / 🥇 {p['cup_titles']} | {p['playstyle']} |\n"

md += """
---

## 🥈 Раздел 4. Средняя лига: Середняки и ветераны дивизиона

| № | Игрок | Статус | Актуальный Elo | Пик Elo | Матчи | W - L | WR% | Разница | GPG | Роль в дивизионе |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(m_table, 1):
    md += f"| {i} | **{p['player']}** | {p['status']} | **{p['active_elo']}** | {p['peak_elo']} | {p['matches']} | {p['wins']}-{p['losses']} | {p['win_rate']}% | {p['goal_diff']:+d} | {p['gpg']} | {p['archetype']} |\n"

md += """
---

## 🥉 Раздел 5. Дворовая лига: Песочница новичков и аматоров

| № | Игрок | Статус | Актуальный Elo | Пик Elo | Матчи | W - L | WR% | Разница | Роль в дивизионе |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(y_table, 1):
    md += f"| {i} | **{p['player']}** | {p['status']} | **{p['active_elo']}** | {p['peak_elo']} | {p['matches']} | {p['wins']}-{p['losses']} | {p['win_rate']}% | {p['goal_diff']:+d} | {p['archetype']} |\n"

md += """
---

## 🧊 Раздел 6. Рейтинг «Хладнокровия»: Короли овертаймов и буллитов (Clutch Index)

*Минимум 3 матча, завершившихся в овертайме или по пенальти:*

| № | Игрок | Матчи в ОТ/буллитах | Победы в ОТ | Поражения в ОТ | % побед в клатче | Характеристика нервной системы |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(clutch[:15], 1):
    char = "Абсолютный дзен (100% побед)" if p["ot_win_rate"] == 100 else ("Стальные нервы" if p["ot_win_rate"] >= 70 else ("Боец овертаймов" if p["ot_win_rate"] >= 50 else "Плывёт в концовках"))
    md += f"| {i} | **{p['player']}** | {p['ot_matches']} | {p['ot_wins']} | {p['ot_losses']} | **{p['ot_win_rate']}%** | {char} |\n"

md += """
---

## ⚔️ Раздел 7. Атака vs Оборона: Стилистический профиль

### 🛡️ Топ-8 «Железных стен» (Минимум пропущенных голов за игру, мин. 15 матчей):
| № | Игрок | Дивизион | Матчи | Пропущено голов | В среднем за игру (GAPG) | «Сухие» матчи | % сухих матчей |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
"""

for i, p in enumerate(def_walls[:8], 1):
    md += f"| {i} | **{p['player']}** | {p['league']} | {p['matches']} | {p['goals_against']} | **{p['gapg']}** | {p['clean_sheets']} | {p['clean_sheet_pct']}% |\n"

md += """
### 🚀 Топ-8 «Атакующих ураганов» (Максимум забитых голов за игру, мин. 15 матчей):
| № | Игрок | Дивизион | Матчи | Забито голов | В среднем за игру (GPG) | Топ-результат |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
"""

for i, p in enumerate(off_blitz[:8], 1):
    md += f"| {i} | **{p['player']}** | {p['league']} | {p['matches']} | {p['goals_for']} | **{p['gpg']}** | {p['playstyle']} |\n"

md += """
---

## 📜 Раздел 8. Книга рекордов лиги всех времён

### 💥 Топ-10 крупнейших разгромов (Blowouts):
| № | Победитель | Счёт | Проигравший | Разница | Сезон и турнир | Стадия |
|:---:|:---|:---:|:---|:---:|:---|:---|
"""

for i, b in enumerate(blowouts[:10], 1):
    md += f"| {i} | **{b['winner']}** | **{b['score_winner']} : {b['score_loser']}** | {b['loser']} | **+{b['diff']}** | {b['tournament']} | {b['stage']} |\n"

md += """
### 🎯 Топ-10 самых результативных перестрелок (Thrillers):
| № | Матч | Счёт | Суммарно голов | Сезон и турнир | Стадия |
|:---:|:---|:---:|:---:|:---|:---|
"""

for i, t in enumerate(thrillers[:10], 1):
    md += f"| {i} | **{t['p1']}** vs **{t['p2']}** | **{t['s1']} : {t['s2']}** | **{t['total_goals']} голов** | {t['tournament']} | {t['stage']} |\n"

md += """
---

## 🦇 Раздел 9. «Криптониты» и личные счёты (Nemesis Matchups)

| Противостояние | Соперники | Личный баланс | Описание драмы |
|:---|:---|:---:|:---|
"""

for r in rivalries:
    md += f"| **{r['rivalry']}** | {r['p1']} — {r['p2']} | **{r['record']}** | {r['notes']} |\n"

md += """
---

## 🏛️ Раздел 10. Зал Славы Чемпионов (Seasons 1–9)

| Сезон | Год | Чемпион Высшей лиги | Обладатель Кубка Лиг | Главный финал плей-офф | Бронза |
|:---:|:---:|:---|:---|:---|:---|
| **S1** | 2015 | **mafuta** | **mafuta** | — | — |
| **S2** | 2016 | **mafuta** | **mafuta** | ectoPower | — |
| **S3** | 2016 | **mafuta** | **mafuta** | ectoPower | Ric25 |
| **S4** | 2017 | **Transistor** | **mafuta** | mafuta / Transistor | ectoPower |
| **S5** | 2017 | **ectoPower** | **RVD (МГБ)** | PacnyTHuK (5:2) | mafuta / izzzotope |
| **S6** | 2018 | **ectoPower** | **ectoPower** | Transistor (5:4 в 9 матчах!) | Rock / Memori |
| **S7** | 2022 | **ectoPower** | **RVD (МГБ)** | mafuta / ectoPower | Romix |
| **S8** | 2024 | **Kunio** | **PacnyTHuK** | ectoPower (5:3 в 8 матчах!) | Romix / Kunio |
| **S9** | 2025 | **Kunio** | **ectoPower** | Rock (5:0 всухую) | Romix |

---

## 🎖️ Раздел 11. Персональные номинации и награды

```mermaid
graph TD
    subgraph "ИНДИВИДУАЛЬНЫЕ НАГРАДЫ КИБЕРСПОРТИВНОЙ СЦЕНЫ GOAL 3"
        A1["👑 THE GOAT (Игрок эпохи):<br/><b>ectoPower</b> (4 титула лиги, 2 кубка, +86 GD)"]
        A2["🎯 CLUTCH GOD (Мастер нервов):<br/><b>Romix</b> (100% ОТ) & <b>PacnyTHuK</b> (80% ОТ)"]
        A3["🛡️ THE IRON WALL (Лучший защитник):<br/><b>Kunio</b> (1.76 GAPG)"]
        A4["💥 THE CANNON (Золотая бутса):<br/><b>ectoPower</b> (3.64 GPG, 215 голов)"]
        A5["🗡️ PLAYOFF SLAYER (Кубковый хищник):<br/><b>RVD / МГБ</b> (2 Кубка Лиг)"]
        A6["🦅 BREAKOUT STAR (Прорыв года):<br/><b>Sokol</b> (22 победы во Дворе + 1/4 Кубка)"]
    end
```
"""

with open("c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\nekketsu_dashboard.md", "w", encoding="utf-8") as f:
    f.write(md)

print("nekketsu_dashboard.md successfully written with all 11 modules!")
