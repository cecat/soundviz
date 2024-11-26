# SoundViz: A utility for visualizing data from the sound log files produced
# by the Home Assistant Yamcam add-on
# or the Yamnet Sound Profiler (YSP).
#
# Charlie Catlett - November 2024
#
# General Functions
#

# Functions in this file:
#
# Setup
#    setup_logging(verbose=False, silent=False)
#    parse_args()
#    check_for_plot_dir(directory)
#
# Processing
#    convert_group_score(value)
#    convert_class_score(value)
#    is_valid_datetime(value)
#    int_defaultdict()
#    two_level_defaultdict()
#    three_level_defaultdict()
#    nested_defaultdict(levels)
#    process_chunk(chunk)
#
# Graphing
#    autopct(pct)
#    generate_pies( data_list, titles, labels_list, colors_list, output_prefix
#    save_legend_as_png(title, colors, labels, output_filename)
#    add_images_to_pdf(c, image_paths, df, rows=4, cols=2)
#    make_pdf(output_pdf_path, df, total_classification_items)

# sv_functions.py

import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import logging
from PIL import Image
from reportlab.lib.pagesizes import letter, portrait
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import blue
from collections import defaultdict

# Constants
url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"
label_threshold = 5
percent_threshold = 3

# Directories
default_log_dir = './logs'
plot_dir = './plots'

# Filenames
sample_log_filename  = 'log.csv'        # default if not specified in command line
report_file          = 'Sound_viz.pdf'  # default if not specified in command line
# for graphics
prefix_timeline      = 'cam_timeline_'
prefix_camera_pie    = 'cam_pie_'
prefix_group_pie     = 'group_pie_'
# for legends
cam_pie_legend       = 'legend_cams'
group_pie_legend     = 'legend_'

###### Set up logging
def setup_logging(verbose=False, silent=False):
    """Configure logging settings."""
    if verbose:
        level = logging.INFO
    elif silent:
        level = logging.WARNING
    else:
        level = logging.ERROR
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

###### Functions

def parse_args():
    """Parse arguments and options."""
    parser = argparse.ArgumentParser(description="Generate a sound visualization PDF report.")
    parser.add_argument( "-o", "--output", type=str,
        help="Specify the output PDF file name (e.g., 'report.pdf'). If not provided, defaults to './plots/Sound_viz.pdf'"
    )
    parser.add_argument( "-i", "--input", type=str,
        help="Specify the input CSV log file (e.g., './logs/log.csv')."
    )
    parser.add_argument('-v', '--verbose', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument('-s', '--silent', action='store_true',
        help='Suppress all but warning/error output'
    )
    parser.add_argument('-c', '--cores', type=int, default=None,
        help='Specify how many cores to use.'
    )

    args = parser.parse_args()

    # Set default input file if none is provided
    if not args.input:
        args.input = os.path.join(default_log_dir, sample_log_filename)

    # Check if the input file exists
    if not os.path.exists(args.input):
        logging.error(f"Error: Input file '{args.input}' does not exist.")
        raise SystemExit

    return args


def check_for_plot_dir(directory):
    """Make sure plot_dir exists."""
    logging.info(f"Checking for {directory}")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as e:
        logging.error(f"Error: Failed to create plot directory '{directory}': {e}")
        raise SystemExit

    # now empty it to avoid confusion with old png files
    try:
        for file_name in os.listdir(plot_dir):
            file_path = os.path.join(plot_dir, file_name)
            if os.path.isfile(file_path):  # Check if it's a file
                os.remove(file_path)
    except OSError as e:
        logging.error(f"Error: Failed to empty plot directory '{directory}': {e}")
        raise SystemExit

#
#### Process Chunks
#

def convert_group_score(value):
    """Convert group_score to a float or NaN if the value is empty."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan


def convert_class_score(value):
    """Convert class_score to a float or NaN if the value is empty."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan

def is_valid_datetime(value):
    """Check to see if field is a date/time."""
    try:
        pd.to_datetime(value)
        return True
    except (ValueError, TypeError):
        return False

def int_defaultdict():
    """Return a defaultdict(int)."""
    return defaultdict(int)


def two_level_defaultdict():
    """Return a two-level nested defaultdict with innermost defaultdict(int)."""
    return defaultdict(int_defaultdict)


def three_level_defaultdict():
    """Return a three-level nested defaultdict with innermost defaultdict(int)."""
    return defaultdict(two_level_defaultdict)


def nested_defaultdict(levels):
    """
    Create a nested defaultdict with a specified number of levels.

    Args:
        levels (int): Number of nesting levels.

    Returns:
        defaultdict: A nested defaultdict.
    """
    if levels == 1:
        return int_defaultdict()
    elif levels == 2:
        return two_level_defaultdict()
    elif levels == 3:
        return three_level_defaultdict()
    else:
        raise ValueError("Only up to 3 levels of nesting are supported.")



def process_chunk(chunk):
    """
    Process a single chunk of data and return the results in a self-contained manner.

    Args:
        chunk (DataFrame): A pandas DataFrame representing a chunk of the log file.

    Returns:
        dict: A dictionary containing aggregated results for the chunk.
    """
    # Show progress
    # Initialize results with nested defaultdicts
    results = {
        "total_classification_counts": defaultdict(int),
        "camera_event_counts": defaultdict(int),
        "hourly_event_counts": nested_defaultdict(3),
        "group_class_counts": nested_defaultdict(2),
        "start_time": None,
        "end_time": None,
        "aggregated_rows": []
    }

    # Filter valid rows
    valid_rows = chunk[chunk['datetime'].apply(is_valid_datetime)].copy()
    if valid_rows.empty:
        return results

    # Convert datetime column
    valid_rows['datetime'] = pd.to_datetime(valid_rows['datetime'])
    valid_rows['hour'] = valid_rows['datetime'].dt.floor('h')

    # Determine start and end times
    results["start_time"] = valid_rows['datetime'].min()
    results["end_time"] = valid_rows['datetime'].max()

    # Append valid rows for potential aggregation
    results["aggregated_rows"].append(valid_rows)

    # Extract group and class names
    valid_rows[['group_name', 'class_name']] = valid_rows['class'].str.split('.', n=1, expand=True)

    # Update classification counts
    group_counts = valid_rows['group_name'].value_counts()
    for group, count in group_counts.items():
        results["total_classification_counts"][group] += count

    # Update camera event counts
    camera_counts = valid_rows['camera'].value_counts()
    for camera, count in camera_counts.items():
        results["camera_event_counts"][camera] += count

    # Update hourly event counts
    events = valid_rows[valid_rows['group_start'].notna()]
    hourly_chunk_counts = events.groupby(['hour', 'camera', 'group_start']).size()
    for (hour, camera, group_start), count in hourly_chunk_counts.items():
        results["hourly_event_counts"][hour][camera][group_start] += count

    # Update group-class counts
    class_counts = valid_rows.groupby(['group_name', 'class_name']).size()
    for (group_name, class_name), count in class_counts.items():
        results["group_class_counts"][group_name][class_name] += count

    return results


#
#### Make the PDF
#

def draw_footer(c, start_date, end_date):
    """
    Draws the footer on the current page of the PDF.

    Args:
        c (Canvas): The canvas object from ReportLab.
        start_date (str): The start date of the data analysis.
        end_date (str): The end date of the data analysis.
    """
    # Footer text parts
    text_prefix = f"Sound analysis ({start_date}-{end_date}) with data from "
    yamcam_text = "Yamcam"
    ysp_text = "ysp"

    # Footer link URLs
    yamcam_url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"
    ysp_url = "https://github.com/cecat/ysp"

    # Set font
    c.setFont("Helvetica", 10)

    # Draw prefix text
    text_x = 0.75 * inch
    c.drawString(text_x, 0.5 * inch, text_prefix)

    # Draw Yamcam link
    yamcam_x = text_x + c.stringWidth(text_prefix)
    c.setFillColor("blue")
    c.drawString(yamcam_x, 0.5 * inch, yamcam_text)
    c.linkURL(yamcam_url, (yamcam_x, 0.5 * inch, yamcam_x + c.stringWidth(yamcam_text), 0.6 * inch), relative=0)

    # Draw separator and ysp link
    c.setFillColor("black")
    separator_x = yamcam_x + c.stringWidth(yamcam_text)
    c.drawString(separator_x, 0.5 * inch, " or ")
    ysp_x = separator_x + c.stringWidth(" or ")
    c.setFillColor("blue")
    c.drawString(ysp_x, 0.5 * inch, ysp_text)
    c.linkURL(ysp_url, (ysp_x, 0.5 * inch, ysp_x + c.stringWidth(ysp_text), 0.6 * inch), relative=0)

    # Reset fill color to black
    c.setFillColor("black")


def add_images_to_pdf(c, image_paths, df, rows=4, cols=2):
    """Insert images to build PDF report file."""
    log_start_date = df['datetime'].min().strftime('%Y-%m-%d %H:%M')
    log_end_date = df['datetime'].max().strftime('%Y-%m-%d %H:%M')

    # Calculate layout positioning and scaling
    images_per_page = rows * cols
    for i in range(0, len(image_paths), images_per_page):
        c.setPageSize(portrait(letter))
        page_images = image_paths[i:i + images_per_page]

        for idx, image_path in enumerate(page_images):
            try:
                img = Image.open(image_path)
            except OSError as e:
                logging.error(f"Error: Cannot open '{image_path}': {e}")
                raise SystemExit

            img_width, img_height = img.size

            # Calculate scale and position for each image based on rows and columns
            max_width = (letter[0] - 2 * inch) / cols
            max_height = (letter[1] - 2 * inch) / rows
            scale = min(max_width / img_width, max_height / img_height)
            new_width = img_width * scale
            new_height = img_height * scale

            col = idx % cols
            row = idx // cols
            x = inch + col * max_width + (max_width - new_width) / 2
            y = letter[1] - inch - (row + 1) * max_height + (max_height - new_height) / 2

            c.drawImage(image_path, x, y, width=new_width, height=new_height)

        draw_footer(c, log_start_date, log_end_date)
        c.showPage()


def make_pdf(output_pdf_path, df, total_classification_items):
    """Create the final PDF file."""
    logging.info(f"Creating PDF report at {output_pdf_path}.")

    # Create canvas for the PDF
    c = canvas.Canvas(output_pdf_path)
    c.setPageSize(portrait(letter))

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(letter[0] / 2, 10.5 * inch, "Sound Classification Report")

    # Date Range
    date_start = df['datetime'].min().strftime('%Y-%m-%d %H:%M')
    date_end = df['datetime'].max().strftime('%Y-%m-%d %H:%M')
    c.setFont("Helvetica", 16)
    c.drawCentredString(letter[0] / 2, 9.75 * inch, f"Period: {date_start} to {date_end}")

    # Total Classifications
    c.drawCentredString(letter[0] / 2, 9.25 * inch, f"Total Classifications Analyzed: {total_classification_items:,}")

    # Insert Pie Chart and Legend
    classification_pie_path = os.path.join(plot_dir, 'classification_distribution_pie.png')
    classification_legend_path = os.path.join(plot_dir, 'legend_classification_distribution.png')
    c.drawImage(classification_pie_path, 1 * inch, 6.00 * inch, width=3 * inch, height=3 * inch)
    c.drawImage(classification_legend_path, 4.5 * inch, 6.00 * inch, width=3 * inch, height=3 * inch)

    # Section Descriptions with 1-inch margins on each side
    # Define TextObject with the starting position
    text = c.beginText(1 * inch, 5.25 * inch)
    text.setFont("Helvetica", 12)
    text.setLeading(14)  # line spacing

    # Define the wrapping width (7.5 inches) based on page width minus margins
    wrap_width = letter[0] - 2 * inch

    # Split and wrap text manually for each line in section_text
    section_text = """
    Section 1: Timelines with stacked columns showing the mix of sound events per hour for each camera (sound source).
    Section 2: Pie charts showing the overall distribution of sound event types for each camera (sound source).
    Section 3: Pie charts for each sound group, showing the distribution of individual yamnet classes within that group.

    Note: For short durations (< several hours) Section 1 will not be very interesting as each column is an entire hour.
    """

    for line in section_text.splitlines():
        words = line.split()
        line_text = ""
        for word in words:
            # Check width of line with the new word added
            if c.stringWidth(line_text + " " + word, "Helvetica", 12) < wrap_width:
                line_text += " " + word
            else:
                # Add the current line to the text object and start a new line
                text.textLine(line_text.strip())
                line_text = word  # Start a new line with the current word
        text.textLine(line_text.strip())  # Add the remaining text for the last line

    c.drawText(text)

    draw_footer(c, date_start, date_end)
    # Report Prepared By Line
    #url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"
    #c.setFont("Helvetica", 12)
    #prepared_by_text = "Report prepared using sound logs from the Yamcam Home Assistant add-on."

    # Draw "Report prepared using sound logs from the" part in black
    #initial_text = "Report prepared using sound logs from the "
    #initial_text_x = (letter[0] / 2) - (c.stringWidth(prepared_by_text) / 2)
    #c.drawString(initial_text_x, 2 * inch, initial_text)

    # Draw "Yamcam" as a colored, clickable link
    #yamcam_text_x = initial_text_x + c.stringWidth(initial_text)
    #c.setFillColor("blue")  # Make link text blue
    #c.drawString(yamcam_text_x, 2 * inch, "Yamcam")
    #c.linkURL(url, (yamcam_text_x, 2 * inch, yamcam_text_x + c.stringWidth("Yamcam"), 2.1 * inch), relative=1)
    #c.setFillColor("black")  # Reset color

    # Draw the rest of the text
    #addon_text_x = yamcam_text_x + c.stringWidth("Yamcam")
    #c.drawString(addon_text_x, 2 * inch, " Home Assistant add-on.")

    # Finalize Cover Page
    c.showPage()

    # Remaining Sections: Timelines, Camera Pies, Group Pies
    # Section 1: Timelines (2 per page)
    timeline_paths = sorted(glob.glob(f"{plot_dir}/{prefix_timeline}*.png"))
    add_images_to_pdf(c, timeline_paths, df, rows=2, cols=1)

    # Section 2: Camera pies and legend
    legend_path = os.path.join(plot_dir, f"{cam_pie_legend}.png")
    camera_pie_paths = [legend_path] + sorted(glob.glob(f"{plot_dir}/{prefix_camera_pie}*.png"))
    add_images_to_pdf(c, camera_pie_paths, df, rows=4, cols=2)

    # Section 3: Group pies and legends
    group_pie_files = sorted([
        p for p in glob.glob(f"{plot_dir}/{prefix_group_pie}*.png")
        if group_pie_legend not in os.path.basename(p)
    ])
    group_names = [
        os.path.basename(p).replace(prefix_group_pie, '').replace('.png', '')
        for p in group_pie_files
    ]

    # Add pie charts and legends for groups
    group_pie_and_legend_paths = []
    for group in group_names:
        pie_path = os.path.join(plot_dir, f"{prefix_group_pie}{group}.png")
        legend_path = os.path.join(plot_dir, f"{group_pie_legend}{group}.png")
        group_pie_and_legend_paths.extend([pie_path, legend_path])
    add_images_to_pdf(c, group_pie_and_legend_paths, df, rows=4, cols=2)

    # Save PDF
    c.save()

