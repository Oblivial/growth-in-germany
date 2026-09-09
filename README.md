# Growth in Germany

This project processes German economic time series into annual growth-rate charts and a consolidated CSV export. 

## Sources

- DESTATIS: German GDP growth rates [[https://www.deutschland-in-daten.de/volkswirtschaftliche-gesamtrechnung/| Deutschland in Daten - Volkswirtschaftliche Gesamtrechnung]] 
- World Bank: German GDP growth rates [[https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=DE| World Bank - GDP growth (annual %) - Germany]]
- WID: GDP and net national income series [[https://wid.world/country/germany/| World Inequality Database - Germany]] 
- GESIS / Heske: GDP series for the GDR (DDR) [[https://search.gesis.org/research_data/ZA8208| GESIS - Macroeconomic Development in East Germany 1970-2000]]

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the Pipeline

Generate all charts and the CSV export:

```powershell
python -m src.main --targets
```

Restrict the displayed period with an inclusive start and end year:

```powershell
python -m src.main --targets --year-range 1970 2025
```

The output directory is cleared before each run, including previous charts and logs.

## Outputs

The pipeline writes these files to `outputs/`:

- `growth_rates.csv`: processed values with `Herkunft`, `Jahr`, and `Prozent`
- `destatis_growth.png`
- `worldbank_growth.png`
- `gesis_growth.png`
- `wid_growth.png`: GDP and net national income together
- `combined_growth.png`: all available series together
- `pipeline_log_<timestamp>.txt`: loading, transformation, and export log

`growth_rates.csv` is encoded as UTF-8 with BOM, uses semicolons as delimiters, and uses decimal commas for compatibility with German Excel installations.

## Growth-Rate Calculation

DESTATIS and World Bank data already provide growth rates in percent. GESIS and WID data contain absolute values, which are converted to annual growth rates using:

$$
\text{growth rate}_t = \frac{\text{value}_t - \text{value}_{t-1}}{\text{value}_{t-1}} \times 100
$$

Each rate is therefore measured relative to the preceding data point, rather than a fixed reference year. The first calculable observation of GESIS and WID is included; rows without a defined rate are omitted from the CSV export.

## Configuration

Chart labels are defined centrally in [src/plotting.py](src/plotting.py):

- `AXIS_CONFIG` controls the x- and y-axis labels.
- `DATASET_LABELS` controls series names in charts and CSV exports.
- `OUTLIER_MULTIPLIER` controls visual clipping of extreme values.

An observation is visually clipped when its absolute growth rate exceeds five times the upper quartile of the absolute rates in the same series. The original value remains in `growth_rates.csv`; charts indicate it with `*`, `//`, and a note below the chart.

## Project Structure

```text
data/                 Input files by source
outputs/              Generated charts, CSV export, and run log
src/readers.py        Source-specific input readers
src/data_processing.py Pipeline orchestration and CSV export
src/plotting.py       Chart configuration and visualization helpers
src/main.py           Command-line entry point
```
