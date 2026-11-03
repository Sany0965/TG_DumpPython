import os
import sys
from pathlib import Path


def find_project_dir():
    candidates = []
    file_name = globals().get("__file__")
    if file_name:
        try:
            candidates.append(Path(file_name).resolve().parent)
        except (OSError, RuntimeError):
            pass
    try:
        candidates.append(Path.cwd().resolve())
    except OSError:
        pass


    for raw in (
        "/storage/emulated/0",
        "/storage/emulated/0/Download",
        "/storage/emulated/0/Documents",
        "/storage/emulated/0/TG_DumpPython",
        "/storage/emulated/0/Android/data/ru.iiec.pydroid3/files",
        "/data/user/0/ru.iiec.pydroid3/files",
    ):
        candidates.append(Path(raw))

    checked = set()
    for base in candidates:
        try:
            base = base.resolve()
        except (OSError, RuntimeError):
            continue
        if base in checked or not base.exists():
            continue
        checked.add(base)
        if (base / "web_app.py").is_file():
            return base



        try:
            for candidate in base.glob("*/web_app.py"):
                if candidate.is_file():
                    return candidate.parent
            for candidate in base.glob("*/*/web_app.py"):
                if candidate.is_file():
                    return candidate.parent
            for candidate in base.glob("*/*/*/web_app.py"):
                if candidate.is_file():
                    return candidate.parent
        except OSError:
            pass
    return None


PROJECT_DIR = find_project_dir()
if PROJECT_DIR is None:
    raise SystemExit(
        "Не найден web_app.py. Запусти app.py из полной папки проекта TG_DumpPython.\n"
        "Рядом с app.py должны находиться web_app.py, index.py, info.py, utils.py, "
        "channel.py, css.py и папка web. Не открывай web/index.html отдельно."
    )

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
os.chdir(PROJECT_DIR)

try:
    from web_app import main
except ModuleNotFoundError as error:

    if error.name == "web_app":
        raise SystemExit(
            f"Не удалось загрузить web_app.py из {PROJECT_DIR}. "
            "Проверь, что файл не переименован и не повреждён."
        ) from error
    raise


if __name__ == "__main__":
    main()
