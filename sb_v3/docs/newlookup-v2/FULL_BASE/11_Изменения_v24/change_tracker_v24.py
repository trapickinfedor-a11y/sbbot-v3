from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "изменения v24" / "CHANGELOG_v24.md"
STATE_PATH = ROOT / "изменения v24" / ".change_tracker_state"
TRACKER_DIR = "изменения v24/"
IGNORED_PREFIXES = (
    ".git/",
    ".cursor_tmp_",
    ".pycache_local/",
)
IGNORED_EXACT = {
    "изменения v24/CHANGELOG_v24.md",
    "изменения v24/.change_tracker_state",
}


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def run_git_null_separated(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout
    if not output:
        return []
    return [item for item in output.split("\0") if item]


def should_ignore(file_path: str) -> bool:
    normalized = file_path.strip().strip('"')
    if normalized in IGNORED_EXACT:
        return True
    if normalized.startswith(TRACKER_DIR):
        return True
    return any(normalized.startswith(prefix) for prefix in IGNORED_PREFIXES)


def get_changed_files() -> list[str]:
    paths = set()
    for command in (
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        output = run_git_null_separated(*command)
        paths.update(path.strip() for path in output if path.strip())
    return sorted(path for path in paths if not should_ignore(path))


def get_file_digest(file_path: str) -> str:
    absolute_path = ROOT / file_path
    if not absolute_path.exists():
        return "__deleted__"
    if absolute_path.is_dir():
        return "__dir__"
    return hashlib.sha256(absolute_path.read_bytes()).hexdigest()


def build_snapshot(files: list[str]) -> dict[str, str]:
    return {file_path: get_file_digest(file_path) for file_path in files}


def classify_stack(files: list[str]) -> list[str]:
    stack: set[str] = {"Python 3.11"}
    modules: set[str] = set()

    for file_path in files:
        path = file_path.lower()
        if path.endswith(".py"):
            stack.update({"aiogram 3.x", "SQLAlchemy async"})
        if "web_panel/" in path or "fastapi" in path:
            stack.add("FastAPI")
            modules.add("web_panel")
        if "shared/database/" in path or "models.py" in path or "alembic" in path:
            stack.add("PostgreSQL")
            modules.add("database")
        if "redis" in path:
            stack.add("Redis")
        if "celery" in path:
            stack.add("Celery")
        if "mirror_bot/" in path:
            modules.add("mirror_bot")
        if "seller_bot/" in path:
            modules.add("seller_bot")
        if "support_bot/" in path or "worker_bot/" in path:
            modules.add("support_bot/worker_bot")
        if "marketer_bot/" in path or "marketing_bot" in path:
            modules.add("marketer_bot")
        if "shared/" in path:
            modules.add("shared")
        if "tests/" in path:
            modules.add("tests")

    ordered = sorted(stack)
    if modules:
        ordered.append("Modules: " + ", ".join(sorted(modules)))
    return ordered


def detect_risks(files: list[str]) -> list[str]:
    risks: list[str] = []
    lowered = [path.lower() for path in files]

    if any("shared/database/models.py" in path for path in lowered):
        risks.append("Изменён `shared/database/models.py`: нужна alembic-миграция и проверка совместимости схемы.")
    if any("order" in path or "payment" in path or "balance" in path or "transaction" in path for path in lowered):
        risks.append("Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.")
    if any("worker" in path or "support" in path for path in lowered):
        risks.append("Изменения в worker/support-потоке: проверить анонимность покупателя и фильтрацию контактов через `chat_filter`.")
    if any("seller_bot/" in path for path in lowered):
        risks.append("Изменения в seller-интерфейсах: убедиться, что seller не получает `buyer_user_id`, `username`, `telegram_id`.")
    if any("tests/" in path for path in lowered):
        risks.append("Есть тестовые изменения: сверить, что покрытие соответствует новому поведению.")
    if not risks:
        risks.append("Явных критических рисков по путям файлов не обнаружено; нужна ручная проверка бизнес-логики после завершения изменений.")

    return risks


def build_description(files: list[str], event_types: dict[str, list[str]]) -> str:
    parts: list[str] = []
    if event_types["new"]:
        parts.append(f"новые файлы: {len(event_types['new'])}")
    if event_types["modified"]:
        parts.append(f"изменены: {len(event_types['modified'])}")
    if event_types["deleted"]:
        parts.append(f"удалены/пропали: {len(event_types['deleted'])}")

    top_files = ", ".join(files[:5])
    if len(files) > 5:
        top_files += f" и ещё {len(files) - 5}"
    summary = "; ".join(parts) if parts else f"обнаружены изменения: {len(files)}"
    return f"{summary}. Файлы: {top_files}."


def classify_events(previous_snapshot: dict[str, str], current_snapshot: dict[str, str]) -> dict[str, list[str]]:
    events = {"new": [], "modified": [], "deleted": []}
    all_paths = sorted(set(previous_snapshot) | set(current_snapshot))

    for path in all_paths:
        previous_digest = previous_snapshot.get(path)
        current_digest = current_snapshot.get(path)
        if previous_digest == current_digest:
            continue
        if previous_digest is None and current_digest is not None:
            events["new"].append(path)
        elif previous_digest is not None and current_digest is None:
            events["deleted"].append(path)
        else:
            events["modified"].append(path)

    return events


def append_entry(files: list[str], event_types: dict[str, list[str]]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stack_info = classify_stack(files)
    risks = detect_risks(files)

    lines = [
        f"## {now}",
        "",
        f"- Время: {now}",
        f"- Краткое описание: {build_description(files, event_types)}",
        "- Затронутые файлы:",
    ]
    lines.extend(f"  - `{file_path}`" for file_path in files)
    lines.append(f"- Полный стек/модули: {'; '.join(stack_info)}")
    lines.append("- Риски:")
    lines.extend(f"  - {risk}" for risk in risks)
    lines.append("")

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines) + "\n")


def ensure_log_header() -> None:
    if LOG_PATH.exists():
        return

    header = """# CHANGELOG v24

Автоматический журнал изменений проекта `newlookup`.

Формат записи:
- Время
- Краткое описание
- Затронутые файлы
- Полный стек/модули
- Риски

"""
    LOG_PATH.write_text(header, encoding="utf-8")


def load_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, object]) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def initialize_state() -> dict[str, object]:
    files = get_changed_files()
    snapshot = build_snapshot(files)
    state = {
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline_snapshot": snapshot,
        "last_snapshot": snapshot,
    }
    save_state(state)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"## Мониторинг запущен: {state['started_at']}\n\n")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Track project changes every N minutes.")
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--duration-seconds", type=int, default=14400)
    args = parser.parse_args()

    ensure_log_header()
    state = load_state() or initialize_state()

    started_at = time.time()
    while True:
        files = get_changed_files()
        current_snapshot = build_snapshot(files)
        previous_snapshot = state.get("last_snapshot", {})
        event_types = classify_events(previous_snapshot, current_snapshot)
        changed_files = sorted(
            event_types["new"] + event_types["modified"] + event_types["deleted"]
        )
        if changed_files:
            append_entry(changed_files, event_types)
            state["last_snapshot"] = current_snapshot
            save_state(state)

        if time.time() - started_at >= args.duration_seconds:
            break

        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
