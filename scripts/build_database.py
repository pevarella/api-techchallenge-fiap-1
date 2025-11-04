"""Build the SQLite database consumed by the FastAPI service."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.config import Settings
from api.database import ensure_database

LOGGER = logging.getLogger("build_database")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or refresh the SQLite catalogue")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        help="Path to the scraped CSV file (defaults to settings BOOKS_CSV_FILENAME)",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=None,
        help="Path where the SQLite database will be written",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild database even if it already exists",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v for INFO, -vv for DEBUG)",
    )
    return parser.parse_args(argv)


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    settings = Settings()

    csv_path = Path(args.csv_path).resolve() if args.csv_path else None
    db_path = Path(args.db_path).resolve() if args.db_path else None

    if csv_path and db_path and csv_path.parent != db_path.parent:
        LOGGER.error("CSV and DB paths must reside in the same directory")
        return 1

    if csv_path:
        settings.data_dir = csv_path.parent
        settings.csv_filename = csv_path.name

    if db_path:
        settings.data_dir = db_path.parent
        settings.db_filename = db_path.name

    if args.force:
        settings.rebuild_db_on_startup = True

    try:
        ensure_database(settings)
    except Exception as exc:  # noqa: BLE001 - CLI guard
        LOGGER.exception("Failed to build database: %s", exc)
        return 1

    LOGGER.info("Database available at %s", settings.db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
