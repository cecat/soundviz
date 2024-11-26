# SoundViz: A utility for visualizing data from the sound log files produced
# by the Home Assistant Yamcam add-on
# or the Yamnet Sound Profiler (YSP).
#
# Charlie Catlett - November 2024
#
# sv.py

import pandas as pd
import os
import logging
from collections import defaultdict
from multiprocessing import Pool

from sv_functions import ( plot_dir, check_for_plot_dir,
    make_pdf, parse_args, setup_logging,
    process_chunk, convert_group_score, 
    convert_class_score, nested_defaultdict
)

from sv_graphs import SoundVisualizer

# chunking logs with millions of rows
chunk_size = 100000

# Determine number of cores to use
num_workers = os.cpu_count() or 4  # Default to 4 if CPU count is unavailable

# Function to determine if a row is a header
def is_header(row):
    return row[0].strip().lower() == "datetime"

#
# MAIN
#
def main():
    args = parse_args()
    verbose = args.verbose
    silent = args.silent
    setup_logging(verbose=verbose, silent=silent)

    # Set up output PDF path
    if args.output:
        output_pdf_path = args.output
        if not output_pdf_path.lower().endswith('.pdf'):
            output_pdf_path += '.pdf'
    else:
        output_pdf_path = os.path.join(plot_dir, "Sound_viz.pdf")

    # Set input log file path
    log_file_path = args.input

    logging.info(f"Report will go to {output_pdf_path}.")
    check_for_plot_dir(plot_dir)

    # Read the first row to check for header
    with open(log_file_path, 'r') as f:
        first_line = f.readline()
        first_row = first_line.strip().split(',')
        has_header = is_header(first_row)

    if has_header:
        logging.info("Header detected. The first row will be skipped during processing.")
    else:
        logging.info("No header detected. All rows will be processed.")

    # Estimate total number of chunks
    logging.info("Estimating total number of chunks...")
    with open(log_file_path, 'r') as f:
        total_lines = sum(1 for _ in f)
    if has_header:
        total_lines -= 1
    total_chunks = (total_lines + chunk_size - 1) // chunk_size
    if not silent and total_chunks > 10:
        print(f"INFO: Processing {total_chunks} {chunk_size}-row chunks.")
    logging.info(f"Total lines in logfile: {total_lines}. Estimated total chunks: {total_chunks}.")

    # Initialize variables for aggregation
    aggregated_rows = []
    total_classification_counts = defaultdict(int)
    camera_event_counts = defaultdict(int)
    hourly_event_counts = nested_defaultdict(3)
    group_class_counts = nested_defaultdict(2)
    start_time = None
    end_time = None

    # Process chunks in parallel
    try:
        chunk_generator = pd.read_csv(
            log_file_path,
            header=None,
            names=[
                "datetime", "camera", "group", "group_score",
                "class", "class_score", "group_start", "group_end"
            ],
            skiprows=1 if has_header else 0,
            dtype={"group": "str"},
            converters={
                "group_score": convert_group_score,
                "class_score": convert_class_score
            },
            chunksize=chunk_size
        )
        chunks = list(chunk_generator)

        # Use multiprocessing Pool
        num_workers = os.cpu_count() or 4
        with Pool(processes=num_workers) as pool:
            results_list = pool.map(process_chunk, chunks)
            for _ in results_list:
                print(".", end="", flush=True)

        # Aggregate results
        for results in results_list:
            aggregated_rows.extend(results["aggregated_rows"])
            for group, count in results["total_classification_counts"].items():
                total_classification_counts[group] += count
            for camera, count in results["camera_event_counts"].items():
                camera_event_counts[camera] += count
            for hour, cameras in results["hourly_event_counts"].items():
                for camera, groups in cameras.items():
                    for group, count in groups.items():
                        hourly_event_counts[hour][camera][group] += count
            for group_name, classes in results["group_class_counts"].items():
                for class_name, count in classes.items():
                    group_class_counts[group_name][class_name] += count
            if results["start_time"]:
                if start_time is None or results["start_time"] < start_time:
                    start_time = results["start_time"]
            if results["end_time"]:
                if end_time is None or results["end_time"] > end_time:
                    end_time = results["end_time"]

    except FileNotFoundError:
        logging.error(f"No log file found at {log_file_path}")
        sys.exit(1)

    # Combine all valid rows into a final DataFrame
    if not aggregated_rows:
        logging.error("No valid data found in the file.")
        sys.exit(1)
    df = pd.concat(aggregated_rows, ignore_index=True)

    # Generate the PNG graphs for the report
    logging.info("Creating the graphs")
    visualizer = SoundVisualizer(
        df=df,
        total_classification_counts=total_classification_counts,
        hourly_event_counts=hourly_event_counts,
        camera_event_counts=camera_event_counts,
        group_class_counts=group_class_counts,
        plot_dir=plot_dir
    )
    visualizer.create_graphs()

    # Generate the PDF report
    classification_counts = pd.Series(total_classification_counts).sort_values(ascending=False)
    total_classification_items = classification_counts.sum()
    make_pdf(output_pdf_path, df, total_classification_items)
    if not silent:
        print(f"PDF report created at {output_pdf_path}")

if __name__ == "__main__":
    main()

