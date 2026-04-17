from __future__ import annotations

import argparse
import logging

from app.core.config import AppPaths, RuntimeConfig, load_environment
from app.data.database import Database
from app.services.sample_data import seed_demo_data
from app.ui.app import BeeDashboardApp


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bee Swarm / Natro dashboard")
    parser.add_argument("--seed-demo", action="store_true", help="Seed the database with sample data")
    args = parser.parse_args()

    load_environment()
    runtime = RuntimeConfig.from_env()
    configure_logging(runtime.debug_logging)
    database = Database(runtime.db_path)

    if args.seed_demo:
        seed_demo_data(database)

    app = BeeDashboardApp(database=database, paths=AppPaths())
    app.mainloop()


if __name__ == "__main__":
    main()

