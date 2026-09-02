from pathlib import Path

import pandas as pd

READ_ERRORS = (OSError, KeyError, TypeError, ValueError, pd.errors.ParserError)


def read_destatis(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, sep=';', decimal=',', engine='python', encoding='utf-8')
        # Normalize column names.
        df.columns = [str(c).strip().strip('"') for c in df.columns]
        # Find the year column.
        id_col = None
        for c in df.columns:
            if str(c).lower().startswith('jahr') or str(c).lower().startswith('year'):
                id_col = c
                break
        if id_col is None:
            id_col = df.columns[0]
        # Find the first period column, such as "1951-1970".
        period_cols = [c for c in df.columns if c != id_col and '-' in str(c) and not 'Durchschnitt' in str(c)]
        if not period_cols:
            return None
        value_col = period_cols[0]
        # Extract year and value, converting decimal commas to dots.
        out = df[[id_col, value_col]].copy()
        out.columns = ['year', 'value']
        out['year'] = out['year'].astype(str).str.extract(r'(\d{4})').astype(int)
        out['value'] = pd.to_numeric(out['value'], errors='coerce')
        out = out.dropna(subset=['value'])
        return out.sort_values('year')
    except READ_ERRORS:
        return None


def read_worldbank(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    # Find the header row.
    header_idx = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        for i, line in enumerate(fh):
            if 'Country Name' in line and 'Indicator Code' in line:
                header_idx = i
                break
    if header_idx is None:
        return None
    try:
        df = pd.read_csv(path, skiprows=header_idx, engine='python')
        # Standardize column names.
        df.columns = [str(c).strip().strip('"') for c in df.columns]
        # Identify year columns.
        year_cols = [c for c in df.columns if str(c).isdigit()]
        if not year_cols:
            return None
        # Filter Germany and the GDP growth indicator.
        mask = (df['Country Name'].str.contains('Germany', na=False)) & (df['Indicator Code'].str.contains('NY.GDP.MKTP.KD.ZG', na=False))
        sub = df[mask]
        if sub.empty:
            # Fall back to the country filter.
            sub = df[df['Country Name'].str.contains('Germany', na=False)]
        if sub.empty:
            return None
        row = sub.iloc[0]
        records = []
        for y in year_cols:
            val = row.get(y, None)
            try:
                v = float(val)
            except (TypeError, ValueError):
                v = None
            if v is not None and not pd.isna(v):
                records.append({'year': int(y), 'value': v})
        out = pd.DataFrame.from_records(records)
        return out.sort_values('year')
    except READ_ERRORS:
        return None


def read_wid(path: Path) -> dict[str, pd.DataFrame] | None:
    """Read WID data and return a mapping of variable names to dataframes."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, sep=';', skiprows=1, encoding='utf-8', quoting=1)
        df.columns = [c.strip() for c in df.columns]
        # The supplied file contains German data only.
        result = {}
        for var in df['Variable'].unique():
            # Skip missing or non-string variable names.
            if pd.isna(var) or not isinstance(var, str):
                continue
            var_data = df[df['Variable'] == var].copy()
            # Use the first line of the quoted variable description as its key.
            var_name = var.strip('"').split('\n')[0].strip()
            if not var_name:
                continue
            var_df = var_data[['Year', 'Value']].copy()
            var_df.columns = ['year', 'value']
            # Convert numeric columns before removing incomplete rows.
            var_df['year'] = pd.to_numeric(var_df['year'], errors='coerce')
            var_df['value'] = pd.to_numeric(var_df['value'], errors='coerce')
            var_df = var_df.dropna()
            if not var_df.empty:
                var_df['year'] = var_df['year'].astype(int)
                result[var_name] = var_df.sort_values('year')
        return result if result else None
    except READ_ERRORS:
        return None


def read_gesis(folder: Path) -> pd.DataFrame | None:
    # Read the first two columns and skip metadata rows.
    if not folder.exists() or not folder.is_dir():
        return None
    # Use the first XLS file in the folder.
    xls_files = list(folder.glob('*.xls'))
    if not xls_files:
        return None
    try:
        f = xls_files[0]
        df = pd.read_excel(f, usecols=[0, 1], header=None)
        # Keep rows whose first cell is a valid year.
        records = []
        for idx, row in df.iterrows():
            try:
                year = int(float(str(row[0]).strip()))
                if 1900 <= year <= 2100:
                    val = float(row[1])
                    if not pd.isna(val):
                        records.append({'year': year, 'value': val})
            except (ValueError, TypeError):
                continue
        if not records:
            return None
        out = pd.DataFrame.from_records(records)
        return out.sort_values('year')
    except READ_ERRORS:
        return None
