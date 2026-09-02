"""Data-processing pipeline for German economic growth data."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .plotting import DATASET_LABELS, plot_growth_chart
from .readers import read_destatis, read_gesis, read_wid, read_worldbank

PROCESSING_ERRORS = (OSError, KeyError, TypeError, ValueError, pd.errors.ParserError)


def filter_by_year_range(
    dataframe: pd.DataFrame, year_start: int | None, year_end: int | None
) -> pd.DataFrame:
    """Return rows within the optional inclusive year range."""
    if year_start is not None:
        dataframe = dataframe[dataframe["year"] >= year_start]
    if year_end is not None:
        dataframe = dataframe[dataframe["year"] <= year_end]
    return dataframe.copy()


def setup_logger(output_dir: Path) -> logging.Logger:
    """Create a file logger for one pipeline run."""
    logger = logging.getLogger("data_pipeline")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    handler = logging.FileHandler(output_dir / f"pipeline_log_{timestamp}.txt", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


def clear_output_dir(output_dir: Path) -> None:
    """Create the output directory and remove files from earlier runs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.is_file():
            path.unlink()


def prepare_series(
    dataframe: pd.DataFrame | None,
    key: str,
    source_is_percent: bool,
    year_start: int | None,
    year_end: int | None,
    logger: logging.Logger,
) -> pd.DataFrame | None:
    """Sort, transform, filter, and name a single source series."""
    if dataframe is None or dataframe.empty:
        logger.warning("%s: no data available", key)
        return None

    prepared = dataframe.sort_values("year").copy()
    prepared["percent"] = prepared["value"]
    if not source_is_percent:
        prepared["percent"] = prepared["value"].pct_change() * 100
    prepared = filter_by_year_range(prepared, year_start, year_end).dropna(subset=["percent"])
    if prepared.empty:
        logger.warning("%s: no data remains after year filtering", key)
        return None

    prepared["source"] = DATASET_LABELS[key]
    logger.info("%s: %d rates prepared", key, len(prepared))
    return prepared


def load_sources(data_dir: Path, logger: logging.Logger) -> dict[str, pd.DataFrame]:
    """Read available source files into dataframes keyed by source name."""
    source_paths = {
        "destatis": data_dir / "destatis-bip-1950-heute.csv",
        "worldbank": data_dir / "Worldbank" / "API_NY.GDP.MKTP.KD.ZG_DS2_en_csv_v2_57.csv",
        "gesis": data_dir / "gesis-ddr-heske",
    }
    readers = {"destatis": read_destatis, "worldbank": read_worldbank, "gesis": read_gesis}
    sources = {}
    for key, path in source_paths.items():
        try:
            dataframe = readers[key](path)
            if dataframe is not None and not dataframe.empty:
                sources[key] = dataframe
                logger.info("%s: %d rows loaded", key, len(dataframe))
            else:
                logger.warning("%s: no data loaded", key)
        except PROCESSING_ERRORS as error:
            logger.error("%s: %s", key, error)

    wid_files = list((data_dir / "WID_Data_Metadata").glob("WID_Data_*.csv"))
    if wid_files:
        try:
            for variable, dataframe in (read_wid(wid_files[0]) or {}).items():
                sources[f"wid_{variable.split('_')[0]}"] = dataframe
                logger.info("WID %s: %d rows loaded", variable, len(dataframe))
        except PROCESSING_ERRORS as error:
            logger.error("WID: %s", error)
    else:
        logger.warning("WID: no input file found")
    return sources


def export_growth_rates(series: list[pd.DataFrame], output_dir: Path, logger: logging.Logger) -> Path | None:
    """Export the same processed data used in the plots."""
    if not series:
        return None
    export = pd.concat(series, ignore_index=True)[["source", "year", "percent"]]
    export.columns = ["Herkunft", "Jahr", "Prozent"]
    path = output_dir / "growth_rates.csv"
    export.sort_values(["Herkunft", "Jahr"]).to_csv(
        path, sep=";", decimal=",", index=False, encoding="utf-8-sig"
    )
    logger.info("CSV exported: %s (%d rows)", path.name, len(export))
    return path


def process_targets_pipeline(
    data_dir: str = "data",
    output_dir: str = "outputs",
    year_start: int | None = None,
    year_end: int | None = None,
) -> list[str]:
    """Generate growth plots and a CSV export from all available sources."""
    output_path = Path(output_dir)
    clear_output_dir(output_path)
    logger = setup_logger(output_path)
    logger.info("Pipeline started; year range: %s to %s", year_start, year_end)

    raw_sources = load_sources(Path(data_dir), logger)
    percent_sources = {"destatis", "worldbank"}
    prepared = [
        result
        for key, dataframe in raw_sources.items()
        if (result := prepare_series(dataframe, key, key in percent_sources, year_start, year_end, logger)) is not None
    ]
    outputs = []
    if csv_path := export_growth_rates(prepared, output_path, logger):
        outputs.append(str(csv_path))

    for series in prepared:
        key = next(key for key, label in DATASET_LABELS.items() if label == series["source"].iloc[0])
        if key.startswith("wid_"):
            continue
        path = output_path / f"{key}_growth.png"
        plot_growth_chart([series], f"{series['source'].iloc[0]} - Wachstumsrate", path, logger)
        outputs.append(str(path))

    wid_series = [series for series in prepared if series["source"].iloc[0].startswith("WID ")]
    if wid_series:
        path = output_path / "wid_growth.png"
        plot_growth_chart(wid_series, "WID - Wachstumsrate", path, logger, dashed=True)
        outputs.append(str(path))
    if prepared:
        path = output_path / "combined_growth.png"
        plot_growth_chart(prepared, "Deutschland - Zusammenfassung aller Datensätze", path, logger, dashed=True)
        outputs.append(str(path))

    logger.info("Pipeline completed: %d files generated", len(outputs))
    return outputs


if __name__ == "__main__":
    print(process_targets_pipeline())