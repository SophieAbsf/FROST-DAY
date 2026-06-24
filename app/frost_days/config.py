from __future__ import annotations

import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache" / "frost_days"
GEO_API_URL = "https://geo.api.gouv.fr/communes"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
