# SoundViz: Functions to create report sections
#
# Charlie Catlett November 2024
#
# sv_reporting.py

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
    save_legend_as_png, cam_pie_legend, group_pie_legend, setup_logging,
    label_threshold, autopct
)


    ### Section: Overall Classification Distribution Pie Chart ###

def create_section_0(df, total_classification_counts, output_dir):

    logging.info("Creating a pie chart for the distribution of all classifications across groups.")

    # Convert total_classification_counts to a Series
    classification_counts = pd.Series(total_classification_counts).sort_values(ascending=False)

    total_classification_items = classification_counts.sum()
    logging.info(f"Total detections (class/class-score rows) used for Classification Distribution: {total_classification_items:,}")

    # Define custom groups and colors
    custom_groups = ['environment', 'birds', 'animals', 'insects', 'weather',
                     'people', 'music', 'vehicles', 'alert']
    custom_colors = ['green', 'lightgreen', '#B6885C', '#FF55BC', 'lightblue',
                     '#3D02C5', '#05ABD7', 'gray', 'red']

    # Identify additional groups and map colors
    additional_groups = [g for g in classification_counts.index if g not in custom_groups]
    group_order = custom_groups + additional_groups
    additional_colors = sns.color_palette('deep', len(additional_groups))
    group_colors = dict(zip(custom_groups, custom_colors))
    group_colors.update(zip(additional_groups, additional_colors))

    classification_counts = classification_counts.reindex(group_order, fill_value=0)
    classification_counts = classification_counts[classification_counts > 0]

    # Prepare colors and labels for the overall distribution chart
    data_colors = [group_colors[group] for group in classification_counts.index]
    percentages = 100 * classification_counts / classification_counts.sum()
    labels = [
        (group[:10] if percent >= label_threshold else '')
        for group, percent in zip(classification_counts.index, percentages)
    ]

    # Plot and save the overall classification distribution pie chart
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.pie(
        classification_counts,
        colors=data_colors,
        autopct=autopct,
        startangle=90,
        counterclock=False,
        textprops={'fontsize': 8}
    )
    ax.axis('equal')
    ax.set_title('Distribution of All Classifications Across Groups', fontsize=10)
    plt.tight_layout()
    classification_pie_filename = f"{output_dir}/classification_distribution_pie.png"
    plt.savefig(classification_pie_filename)
    plt.close()

    # Generate the legend for classification distribution
    legend_filename = 'legend_classification_distribution.png'
    save_legend_as_png(
        title="Classification Distribution",
        colors=data_colors,
        labels=classification_counts.index.tolist(),
        output_filename=legend_filename
    )
