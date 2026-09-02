import pandas as pd
from pathlib import Path
from src.readers import read_wid

path = Path('data/WID_Data_Metadata/WID_Data_31082026-134910.csv')

# test directly
try:
    result = read_wid(path)
    print('Result:', result)
    if result:
        print('Keys:', list(result.keys()))
        for k, v in result.items():
            print(f'{k}: {len(v)} rows, years {v["year"].min()}-{v["year"].max()}')
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
