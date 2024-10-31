# Functions for a utility for visualizing data from the sound log files produced
# by the Home Assistant (experimental) Yamcam add-on
# (see https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
#
# Charlie Catlett October 2024
#

# Functions in this file:
##      parse_args()
#       Parse optional input and output file args (-i, -o)
#
##     check_for_plot_dir(directory)
#      Make sure the output directory exists
#
##     autopct(pct)
#      Convert to percentages
#
##     generate_pies( data_list, titles, labels_list,
##                    colors_list, output_prefix,
##                    pies_per_image=6):
#      Create pie charts
#
##     add_images_to_pdf(c, image_paths, df, shift_x=0, shift_y=0)
#      Add images to PDF
#
##     make_pdf(plot_dir, output_pdf_path, df)
#      Create PDF
#

# svf.py

import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
from reportlab.lib.pagesizes import letter, portrait
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import blue
from PIL import Image

# Constants
url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"
label_threshold = 5
percent_threshold = 3

# Directories
log_dir = './logs'
plot_dir = './plots'

# Filenames
log_filename      = 'log.csv'        # default if not specified in command line
report_file       = 'Sound_viz.pdf'  # default if not specified in command line
# for graphics
prefix_timeline   = 'cam_timeline_'
prefix_camera_pie = 'cam_pie_'
prefix_group_pie  = 'group_pie_'
# for legends
cam_pie_legend    = 'legend_cams'
group_pie_legend  = 'legend_'

###### Functions

# Parse optional input and output file args (-i, -o)
def parse_args():
    parser = argparse.ArgumentParser(description="Generate a sound visualization PDF report.")
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Specify the output PDF file name (e.g., 'report.pdf'). If not provided, defaults to './plots/Sound_viz.pdf'"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="./logs/log.csv",  # Default input filename
        help="Specify the input CSV log file (e.g., './logs/log.csv')."
    )
    return parser.parse_args()

# Make sure the output directory exists
def check_for_plot_dir(directory):
    print(f"Checking for {directory}")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create plot directory '{directory}': {e}")
        sys.exit(1)

# Convert to percentages
def autopct(pct):
    return f'{pct:.1f}%' if pct >= percent_threshold else ''

# Create individual pie charts
def generate_pies(
    data_list, titles, labels_list, colors_list, output_prefix
):
    for idx, (data, title, labels, colors) in enumerate(
        zip(data_list, titles, labels_list, colors_list)
    ):
        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
        ax.pie(
            data,
            colors=colors,
            autopct=autopct,
            startangle=90,
            counterclock=False,
            textprops={'fontsize': 8}
        )
        ax.axis('equal')
        ax.set_title(title, fontsize=10)
        plt.tight_layout()

        filename = f"{plot_dir}/{output_prefix}{title}.png"

        plt.savefig(filename)
        plt.close()

# Generate legend as separate png
def save_legend_as_png(title, colors, labels, output_filename):
    fontsize = 8

    # Create a figure to hold only the legend
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.axis("off")

    # Create a dummy plot to generate the legend
    handles = [
        plt.Line2D(
            [0], [0],
            color=color,
            marker='o',
            linestyle='',
            markersize=8
        )
        for color in colors
    ]

    legend = ax.legend(
        handles,
        labels,
        loc="upper left",
        frameon=False,
        title= title,
        prop={'size': fontsize}
    )

    # Save the legend as a PNG
    legend_path = os.path.join(plot_dir, output_filename)
    plt.savefig(legend_path, bbox_inches="tight", dpi=300)
    plt.close(fig)

# Add images to PDF
def add_images_to_pdf(c, image_paths, df, rows=4, cols=2):
    # URL and footer text definitions
    log_start_date = df['datetime'].min().strftime('%Y-%m-%d %H:%M')
    log_end_date = df['datetime'].max().strftime('%Y-%m-%d %H:%M')
    footer_text_prefix = (
        f"Sound viz for {log_start_date} "
        f" -  {log_end_date} using the Home Assistant add-on "
    )
    footer_text_yamcam = "Yamcam"
    footer_text_suffix = "."

    # Calculate layout positioning and scaling
    images_per_page = rows * cols
    for i in range(0, len(image_paths), images_per_page):
        c.setPageSize(portrait(letter))
        page_images = image_paths[i:i + images_per_page]

        for idx, image_path in enumerate(page_images):
            try:
                img = Image.open(image_path)
            except:
                print(f"Cannot find {image_path}.")
                sys.exit(1)

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

        # Add footer with visible clickable "Yamcam" link
        c.setFont("Helvetica", 10)
        c.drawString(0.75 * inch, 0.5 * inch, footer_text_prefix)
        yamcam_text_x = c.stringWidth(footer_text_prefix) + 0.75 * inch
        c.setFillColor(blue)
        c.drawString(yamcam_text_x, 0.5 * inch, footer_text_yamcam)
        c.setFillColor("black")
        # Draw the suffix part of the footer
        c.drawString(
            yamcam_text_x + c.stringWidth(footer_text_yamcam),
            0.5 * inch,
            footer_text_suffix
        )

        # Add a clickable link for "Yamcam" with bounding box coordinates
        c.linkURL(
            url,
            (
                yamcam_text_x,
                0.5 * inch,
                yamcam_text_x + c.stringWidth(footer_text_yamcam),
                0.6 * inch
            ),
            relative=1
        )

        c.showPage()

# Create PDF
def make_pdf(output_pdf_path, df):
    print(f"Creating PDF report at {output_pdf_path}.")

    c = canvas.Canvas(output_pdf_path)

    # Section 0: Classification distribution pie chart and legend
    classification_pie_path = os.path.join(plot_dir, 'classification_distribution_pie.png')
    classification_legend_path = os.path.join(plot_dir, 'legend_classification_distribution.png')
    classification_paths = [classification_pie_path, classification_legend_path]
    add_images_to_pdf(c, classification_paths, df, rows=1, cols=2)

    # Section 1: Stacked column timelines (2 per page)
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

    # Build list of pie chart and legend paths
    group_pie_and_legend_paths = []
    for group in group_names:
        pie_path = os.path.join(plot_dir, f"{prefix_group_pie}{group}.png")
        legend_path = os.path.join(plot_dir, f"{group_pie_legend}{group}.png")
        group_pie_and_legend_paths.extend([pie_path, legend_path])

    # Add images to PDF with 2 columns per row
    add_images_to_pdf(c, group_pie_and_legend_paths, df, rows=4, cols=2)

    # Save the PDF
    c.save()

    print(f"PDF report created at {output_pdf_path}")

