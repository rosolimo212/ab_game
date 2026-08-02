# coding: utf-8
"""
Точка входа приложения.

Цель:
    Прочитать settings (+ secrets), выбрать интерфейс и запустить клиент.

Запуск Streamlit напрямую:
    streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_app_config


def main() -> None:
    config = load_app_config("settings.yaml", "secrets.yaml")
    interface = config["app"]["interface"]

    if interface == "streamlit":
        from ui.streamlit_app import run_streamlit

        run_streamlit(config)
    elif interface in ("telegram", "console"):
        raise NotImplementedError(
            f"Интерфейс {interface!r} пока не реализован. Используйте streamlit."
        )
    else:
        raise ValueError(
            f"Неизвестный интерфейс: {interface!r}. Ожидается streamlit."
        )


if __name__ == "__main__":
    main()
