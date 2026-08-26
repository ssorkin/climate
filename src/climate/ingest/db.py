"""DuckDB views over the Parquet store, for ad-hoc exploration and checks."""

from __future__ import annotations

import duckdb

from climate.paths import DUCKDB_PATH, PARQUET_DIR


def build() -> None:
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))
    daily_glob = str(PARQUET_DIR / "ghcnd_daily" / "*" / "data.parquet")
    con.execute(
        f"CREATE OR REPLACE VIEW daily_raw AS "
        f"SELECT * FROM read_parquet('{daily_glob}', hive_partitioning=true)"
    )
    con.execute("CREATE OR REPLACE VIEW daily_valid AS SELECT * FROM daily_raw WHERE qflag = ''")
    con.execute(
        """
        CREATE OR REPLACE VIEW daily_wide AS
        SELECT id, date,
               max(CASE WHEN element = 'TMAX' THEN value END) AS tmax,
               max(CASE WHEN element = 'TMIN' THEN value END) AS tmin,
               max(CASE WHEN element = 'PRCP' THEN value END) AS prcp,
               max(CASE WHEN element = 'TMAX' THEN obs_time END) AS obs_tmax,
               max(CASE WHEN element = 'TMIN' THEN obs_time END) AS obs_tmin
        FROM daily_valid
        GROUP BY id, date
        """
    )
    for name in ("ghcnd_stations", "ghcnd_inventory"):
        p = PARQUET_DIR / name / "data.parquet"
        view = name.removeprefix("ghcnd_")
        con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{p}')")
    n = con.execute("SELECT count(*) FROM daily_raw").fetchone()[0]
    con.close()
    print(f"  duckdb views rebuilt ({n:,} daily rows) -> {DUCKDB_PATH.name}")
