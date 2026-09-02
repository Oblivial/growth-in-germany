"""Plot configuration and utilities for the growth pipeline."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

AXIS_CONFIG = {
    "xlabel": "Jahr",
    "ylabel": "Veränderungsrate in %, gemessen am Vorjahr",
}

DATASET_LABELS = {
    "destatis": "DESTATIS BIP",
    "worldbank": "Worldbank BIP",
    "gesis": "Heskes BIP für die DDR",
    "wid_agdpro": "WID BIP",
    "wid_agninc": "WID Nettonationaleinkommen",
}

OUTLIER_MULTIPLIER = 5


def plot_series_with_clipped_outliers(
    ax, series: pd.DataFrame, notes: list[str], **plot_kwargs
) -> None:
    """Plot a series, clipping rates above five times its absolute upper quartile."""
    rates = series["percent"]
    magnitudes = rates.abs().dropna()
    threshold = magnitudes.quantile(0.75) * OUTLIER_MULTIPLIER
    outliers = rates.abs() > threshold if threshold > 0 else pd.Series(False, index=rates.index)
    clipped = rates.mask(outliers)
    line = ax.plot(series["year"], clipped, label=series["source"].iloc[0], **plot_kwargs)[0]

    if not outliers.any():
        return
    normal_rates = clipped.dropna()
    padding = max((normal_rates.max() - normal_rates.min()) * 0.1, 1)
    limits = (normal_rates.min() - padding, normal_rates.max() + padding)
    ax.set_ylim(*limits)
    for _, row in series[outliers].iterrows():
        marker_y = limits[0] if row["percent"] < 0 else limits[1]
        ax.plot(row["year"], marker_y, marker="*", color=line.get_color(), markersize=12)
        ax.annotate("//", (row["year"], marker_y), ha="center", va="bottom")
        notes.append(f"* {row['source']}, {row['year']}: tatsächliche Rate {row['percent']:.1f} %")


def plot_growth_chart(
    series: list[pd.DataFrame], title: str, path: Path, logger: logging.Logger, dashed: bool = False
) -> None:
    """Save a growth chart for one or more prepared source series."""
    figure, ax = plt.subplots(figsize=(12, 6) if len(series) > 1 else (10, 5))
    notes = []
    for dataframe in series:
        style = {"linestyle": "--"} if dashed and dataframe["source"].iloc[0].startswith("WID ") else {}
        plot_series_with_clipped_outliers(ax, dataframe, notes, **style)

    ax.set(xlabel=AXIS_CONFIG["xlabel"], ylabel=AXIS_CONFIG["ylabel"], title=title)
    ax.axhline(0, color="red", linestyle="--", linewidth=0.7, alpha=0.5)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_ylabel(AXIS_CONFIG["ylabel"], fontsize=9)
    ax.legend()
    if notes:
        figure.text(0.1, 0.03, "\n".join(notes), fontsize=9)
        logger.info("Clipped outliers in %s: %s", path.name, "; ".join(notes))
    figure.tight_layout(rect=(0, 0.1 if notes else 0, 1, 1))
    figure.savefig(path)
    plt.close(figure)