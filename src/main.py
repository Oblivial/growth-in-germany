import argparse

from dotenv import load_dotenv

from .data_processing import process_targets_pipeline


def main():
    parser = argparse.ArgumentParser(description='German Economic Data Pipeline')
    parser.add_argument('--targets', action='store_true', help='Run the targets pipeline to produce percent-change line graphs')
    parser.add_argument('--year-range', nargs=2, type=int, metavar=('START', 'END'), 
                       help='Zeitspanne für die Darstellung: --year-range 1970 2025')
    args = parser.parse_args()

    load_dotenv()

    if args.targets:
        year_start = args.year_range[0] if args.year_range else None
        year_end = args.year_range[1] if args.year_range else None
        out = process_targets_pipeline(year_start=year_start, year_end=year_end)
        print('Targets pipeline saved outputs:', out)


if __name__ == '__main__':
    main()
