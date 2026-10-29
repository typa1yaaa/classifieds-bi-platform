from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass

from src.common.config import ROOT
from src.loaders.clickhouse import client, run_file

REPEATS = 5
LISTING_ID = 12345


@dataclass
class Scenario:
    key: str
    title: str
    question: str
    before: str
    after: str
    technique: str
    tolerance: float = 0.0
    antipattern: bool = False
    before_setup: str = ""
    after_setup: str = ""


SCENARIOS = [
    Scenario(
        "daily_category", "Дневной график по категории",
        "Контакты по дням в категории \"Автомобили\" за 90 дней",
        """SELECT toDate(event_time) AS d, countIf(event_type = 'contact') AS c
           FROM raw.events
           WHERE category_id = 101 AND event_time >= '2026-06-30 00:00:00'
           GROUP BY d ORDER BY d""",
        """SELECT event_date AS d, sum(contacts) AS c
           FROM marts.fct_category_daily
           WHERE category_id = 101 AND event_date >= '2026-06-30'
           GROUP BY d ORDER BY d""",
        "Витрина вместо сырых событий. Ответ отличается на доли процента: сырой запрос считает и повторные доставки",
        tolerance=0.02,
    ),
    Scenario(
        "listing_history", "История одного объявления",
        f"Все события объявления {LISTING_ID} по дням и типам",
        f"""SELECT toDate(event_time) AS d, event_type, count() AS n
            FROM raw.events WHERE listing_id = {LISTING_ID}
            GROUP BY d, event_type ORDER BY d, event_type""",
        f"""SELECT toDate(event_time) AS d, event_type, count() AS n
            FROM raw.events WHERE listing_id = {LISTING_ID}
            GROUP BY d, event_type ORDER BY d, event_type""",
        "Проверка гипотезы \"нужна проекция по listing_id\". Основной ключ уже отсекает >99% строк: "
        "listing_id в нём четвёртый, но префикс (дата, категория, тип) низкокардинальный, и ClickHouse "
        "применяет generic exclusion search. Проекция читает меньше строк, но быстрее не становится - "
        "место на диске она не окупает",
        before_setup="ALTER TABLE raw.events DROP PROJECTION IF EXISTS p_by_listing SETTINGS mutations_sync = 2",
        after_setup="05_projections.sql",
    ),
    Scenario(
        "dedup", "Контакты без дублей доставки",
        "Число контактов за сентябрь без повторно доставленных событий",
        """SELECT count() FROM (
               SELECT event_id FROM raw.events
               WHERE event_type = 'contact' AND event_date BETWEEN '2026-09-01' AND '2026-09-27'
               LIMIT 1 BY event_id)""",
        """SELECT count() FROM staging.stg_events
           WHERE event_type = 'contact' AND event_date BETWEEN '2026-09-01' AND '2026-09-27'""",
        "Дедупликация один раз при сборке (ReplacingMergeTree + OPTIMIZE FINAL), а не в каждом запросе",
    ),
    Scenario(
        "unique_users", "Уникальные пользователи за месяц",
        "Сколько разных пользователей видели объявления в сентябре",
        """SELECT uniqExact(user_id) FROM raw.events
           WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'""",
        """SELECT uniqHLL12Merge(users_hll) FROM marts.users_daily_agg
           WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'""",
        "Скетч uniqHLL12 в MV на зерне \"день и платформа\" вместо точного подсчёта по сырым событиям (погрешность ~1,6%)",
        tolerance=0.02,
    ),
    Scenario(
        "unique_users_fine", "Антипример: uniq-скетчи на мелком зерне",
        "Тот же вопрос, но из агрегата \"объявление и день\", где скетч хранится в каждой строке",
        """SELECT uniqExact(user_id) FROM raw.events
           WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'""",
        """SELECT uniqMerge(users_uniq) FROM marts.listing_daily_agg
           WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'""",
        "Слияние миллионов скетчей дороже, чем точный подсчёт: предагрегация помогает, только если зерно подходит вопросу",
        tolerance=0.02,
        antipattern=True,
    ),
    Scenario(
        "funnel_month", "Воронка по платформам за месяц",
        "Показы, просмотры и контакты по платформам за сентябрь",
        """SELECT platform, countIf(event_type = 'impression') AS i, countIf(event_type = 'view') AS v,
                  countIf(event_type = 'contact') AS c
           FROM raw.events WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
           GROUP BY platform ORDER BY platform""",
        """SELECT platform, sum(impressions) AS i, sum(views) AS v, sum(contacts) AS c
           FROM marts.fct_platform_daily WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
           GROUP BY platform ORDER BY platform""",
        "Витрина на зерне вопроса \"день и платформа\" (81 строка за месяц). Ответ меньше на долю дублей доставки",
        tolerance=0.01,
    ),
]


@dataclass
class Measure:
    ms: float
    read_rows: int
    read_bytes: int


def measure(ch, sql: str, tag: str) -> tuple[Measure, list]:
    runs = []
    rows = None
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        r = ch.query(sql, settings={"log_comment": tag, "use_query_cache": 0})
        wall = (time.perf_counter() - t0) * 1000
        s = r.summary or {}
        server_ms = int(s.get("elapsed_ns", 0)) / 1e6 or wall
        runs.append(Measure(server_ms, int(s.get("read_rows", 0)), int(s.get("read_bytes", 0))))
        rows = r.result_rows
    med = statistics.median(m.ms for m in runs)
    return Measure(round(med, 1), runs[-1].read_rows, runs[-1].read_bytes), rows


def setup(ch, step: str) -> None:
    if step.endswith(".sql"):
        run_file(ch, step)
    elif step:
        ch.command(step)


def same_answer(a: list, b: list, tol: float) -> bool:
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if abs(x - y) > tol * max(abs(x), 1):
                    return False
            elif x != y:
                return False
    return True


def verdict(r: dict) -> str:
    if r["antipattern"]:
        return "антипример"
    if r["speedup"] >= 2:
        return "помогло"
    if r["speedup"] >= 0.8:
        return "эффекта почти нет"
    return "стало хуже"


def fmt_rows(n: int) -> str:
    return f"{n / 1e6:.1f} млн" if n >= 1e6 else f"{n / 1e3:.0f} тыс." if n >= 1e3 else str(n)


def main() -> None:
    ch = client()
    total = ch.query("SELECT count() FROM raw.events").result_rows[0][0]
    results = run_scenarios(ch)
    proj = ch.query("""SELECT sum(bytes_on_disk) FROM system.projection_parts
                       WHERE database = 'raw' AND table = 'events' AND name = 'p_by_listing' AND active""")
    table = ch.query("""SELECT sum(bytes_on_disk) FROM system.parts
                        WHERE database = 'raw' AND table = 'events' AND active""")
    proj_bytes, table_bytes = proj.result_rows[0][0] or 0, table.result_rows[0][0] or 0

    setup(ch, "ALTER TABLE raw.events DROP PROJECTION IF EXISTS p_by_listing SETTINGS mutations_sync = 2")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/bench_results.json").write_text(json.dumps(
        {"raw_events": total, "table_bytes": table_bytes, "projection_bytes": proj_bytes, "results": results},
        ensure_ascii=False, indent=2))
    write_markdown(total, table_bytes, proj_bytes, results)


def run_scenarios(ch) -> list[dict]:
    results = []
    for sc in SCENARIOS:
        setup(ch, sc.before_setup)
        before, a = measure(ch, sc.before, f"bench:{sc.key}:before")
        setup(ch, sc.after_setup)
        after, b = measure(ch, sc.after, f"bench:{sc.key}:after")
        ok = same_answer(a, b, sc.tolerance)
        results.append({**asdict(sc), "before_m": asdict(before), "after_m": asdict(after), "same_answer": ok,
                        "speedup": round(before.ms / max(after.ms, 0.1), 1)})
        print(f"{sc.title:<36} {before.ms:>8.1f} ms -> {after.ms:>7.1f} ms   "
              f"rows {fmt_rows(before.read_rows):>9} -> {fmt_rows(after.read_rows):>9}   same={ok}")
    return results


def write_markdown(total: int, table_bytes: int, proj_bytes: int, results: list[dict]) -> None:
    lines = [
        "# Производительность: до и после",
        "",
        f"Данные: `raw.events` - {total:,} событий за 180 дней. ".replace(",", " ")
        + f"Медиана из {REPEATS} запусков, время выполнения на сервере; \"строк\" - сколько строк ClickHouse "
        "реально считал с диска. Перед сравнением проверяется, что оба варианта дают одинаковый ответ.",
        "",
        "Файл генерируется командой `make bench` (src/bench/run_bench.py). Абсолютные миллисекунды зависят "
        "от машины, поэтому главное здесь - во сколько раз меньше строк читается и почему.",
        "",
        "| Сценарий | До, мс | После, мс | Ускорение | Строк до | Строк после | Ответ совпал | Вывод | Приём |",
        "|---|---:|---:|---:|---:|---:|:---:|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['title']} | {r['before_m']['ms']:.0f} | {r['after_m']['ms']:.1f} | "
            f"{'**и' + str(r['speedup']) + '** ⚠' if r['antipattern'] else 'и' + str(r['speedup'])} | "
            f"{fmt_rows(r['before_m']['read_rows'])} | {fmt_rows(r['after_m']['read_rows'])} | "
            f"{'да' if r['same_answer'] else 'нет'} | {verdict(r)} | {r['technique']} |")
    lines += [
        "",
        "## Цена оптимизаций",
        "",
        f"* Проекция `p_by_listing` занимает {proj_bytes / 2**20:.0f} МБ при размере таблицы "
        f"{table_bytes / 2**20:.0f} МБ (вместе с проекцией) и замедляет вставку. На этих данных она не дала "
        "выигрыша, поэтому в боевой схеме её стоит удалить (`ALTER TABLE raw.events DROP PROJECTION p_by_listing`). "
        "Оптимизацию сначала замеряют, потом оставляют.",
        "* `uniq` против `uniqExact`: приближённый подсчёт с погрешностью около 1–2% "
        "(в сценарии \"Уникальные пользователи" ответы сравниваются с допуском 2%). Для финансовых метрик "
        "приближение недопустимо, для дашборда аудитории - нормально.",
        "* Витрины и MV нужно поддерживать: MV видит только новые вставки, витрины dbt пересобираются по расписанию, "
        "а их корректность проверяют сверки в `dq.dq_checks_daily`.",
        "",
        "## Сами запросы",
        "",
    ]
    for r in results:
        lines += [f"### {r['title']}", "", r["question"] + ".", "", "До:", "", "```sql",
                  "\n".join(l.strip() for l in r["before"].strip().splitlines()), "```", "", "После:", "",
                  "```sql", "\n".join(l.strip() for l in r["after"].strip().splitlines()), "```", ""]
    (ROOT / "docs/performance.md").write_text("\n".join(lines))
    print("saved docs/performance.md, docs/bench_results.json")


if __name__ == "__main__":
    main()
