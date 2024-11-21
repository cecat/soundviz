# SoundViz: A utility for visualizing data from the sound log files produced
# by the Home Assistant (experimental) Yamcam add-on
# (see https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
#
# Charlie Catlett October 2024
#
# sv.py
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import os
import logging
from datetime import datetime
from collections import defaultdict

from sv_functions import (
    output_dir, check_for_output_dir, autopct,
    make_pdf, label_threshold, percent_threshold, generate_pies,
    parse_args, prefix_timeline, prefix_camera_pie, prefix_group_pie,
    save_legend_as_png, cam_pie_legend, group_pie_legend, setup_logging
    )

from sv_reporting import (
    create_section_0, create_section_1,
    create_section_2, create_section_3
    )

# chunking logs with millions of rows
chunk_size = 100000

def is_valid_datetime(value):
    try:
        pd.to_datetime(value)
        return True
    except (ValueError, TypeError):
        return False

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
    setup_logging(verbose=verbose, silent=silent)   # decide how noisy to be

    # Set up output PDF path
    if args.output:
        output_pdf_path = args.output
        if not output_pdf_path.lower().endswith('.pdf'):
            output_pdf_path += '.pdf'
    else:
        output_pdf_path = os.path.join(output_dir, "Sound_viz.pdf")

    # Set input log file path
    log_file_path = args.input

    logging.info(f"Report will go to {output_pdf_path}.")
    #logging.warning(f"Check for plot directory {output_dir}.")
    check_for_output_dir(output_dir)

    # Read the first row to check for header
    with open(log_file_path, 'r') as f:
        first_line = f.readline()
        # Split the first line by comma to get individual columns
        first_row = first_line.strip().split(',')
        has_header = is_header(first_row) # set the header flag for later

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
    total_chunks = (total_lines + chunk_size - 1) // chunk_size  # Ceiling division
    logging.info(f"Total lines in file: {total_lines}. Estimated total chunks: {total_chunks}.")

    # Initialize variables for processing
    start_time = None
    end_time = None
    aggregated_rows = []
    total_classification_counts = defaultdict(int)
    camera_event_counts = defaultdict(int)
    hourly_event_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    group_class_counts = defaultdict(lambda: defaultdict(int))

    # Process the file in chunks
    chunk_number = 0
    try:
        for chunk in pd.read_csv(
            log_file_path,
            header=None,
            names=[
                "datetime",
                "camera",
                "group",
                "group_score",
                "class",
                "class_score",
                "group_start",
                "group_end"
            ],
            skiprows=1 if has_header else 0,  # Conditionally skip the first row
            # specify non-string column (datetime and scores) data types and processes
            dtype={
                "group": "str",
            },
            converters={
                "group_score": lambda x: float(x) if x else np.nan,
                "class_score": lambda x: float(x) if x else np.nan
            },
            chunksize=chunk_size
        ):
            chunk_number += 1
            logging.info(f"Processing chunk {chunk_number} of {total_chunks}...")
            valid_rows = chunk[chunk['datetime'].apply(is_valid_datetime)].copy()  # Added .copy()
            if valid_rows.empty:
                continue

            # Convert datetime column
            valid_rows['datetime'] = pd.to_datetime(valid_rows['datetime'])
            valid_rows['hour'] = valid_rows['datetime'].dt.floor('h')

            # Update start and end times
            if start_time is None or valid_rows['datetime'].min() < start_time:
                start_time = valid_rows['datetime'].min()
            if end_time is None or valid_rows['datetime'].max() > end_time:
                end_time = valid_rows['datetime'].max()

            # Append valid rows to aggregated data
            aggregated_rows.append(valid_rows)

            # Extract group names from 'class' column
            valid_rows[['group_name', 'class_name']] = valid_rows['class'].str.split('.', n=1, expand=True)

            # Update total classification counts
            group_counts = valid_rows['group_name'].value_counts()
            for group, count in group_counts.items():
                total_classification_counts[group] += count

            # Update camera event counts
            camera_counts = valid_rows['camera'].value_counts()
            for camera, count in camera_counts.items():
                camera_event_counts[camera] += count

            # Update hourly event counts
            events = valid_rows[valid_rows['group_start'].notna()]
            hourly_chunk_counts = events.groupby(['hour', 'camera', 'group_start']).size()
            for (hour, camera, group_start), count in hourly_chunk_counts.items():
                hourly_event_counts[hour][camera][group_start] += count

            # Update group class counts
            class_counts = valid_rows.groupby(['group_name', 'class_name']).size()
            for (group_name, class_name), count in class_counts.items():
                group_class_counts[group_name][class_name] += count

    except FileNotFoundError:
        logging.error(f"No log file found at {log_file_path}")
        sys.exit(1)

    # Combine all valid rows into a final DataFrame
    if not aggregated_rows:
        logging.error("No valid data found in the file.")
        sys.exit(1)
    df = pd.concat(aggregated_rows, ignore_index=True)


    ### Section 0: Overall Classification Distribution Pie Chart ###
    create_section_0(df, total_classification_counts, output_dir)

    ### Section 1: Stacked Column timelines for each camera ###
    events_df, pivot_table = create_section_1(df, hourly_event_counts, output_dir)

    ### Section 2: Individual pies for each camera ###
    create_section_2(pivot_table, camera_event_counts, events_df, output_dir)

    ### Section 3: Individual pies for each group, showing class distribution ###
    create_section_3(group_class_counts, total_classes, output_dir)

    ### Generate the PDF Report ###
    make_pdf(output_pdf_path, df, total_classification_items)
    if not silent:
        print(f"PDF report created at {output_pdf_path}")

if __name__ == "__main__":
    main()

