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
    check_for_output_dir, autopct, make_pdf, label_threshold,
    generate_pies, parse_args, prefix_timeline, prefix_camera_pie,
    prefix_group_pie, save_legend_as_png, setup_logging,
    cam_pie_legend, group_pie_legend
)

# Common constants
custom_groups = ['environment', 'birds', 'animals', 'insects', 'weather',
                 'people', 'music', 'vehicles', 'alert']
custom_colors = ['green', 'lightgreen', '#B6885C', '#FF55BC', 'lightblue',
                 '#3D02C5', '#05ABD7', 'gray', 'red']


def get_group_colors(additional_groups=None):
    """Generate group-to-color mappings."""
    if additional_groups is None:
        additional_groups = []
    additional_colors = sns.color_palette('deep', len(additional_groups))
    group_colors = dict(zip(custom_groups, custom_colors))
    group_colors.update(zip(additional_groups, additional_colors))
    return group_colors


def get_event_group_order(all_event_groups):
    """Combine custom groups with additional groups for consistent ordering."""
    additional_event_groups = [g for g in all_event_groups if g not in custom_groups]
    return custom_groups + additional_event_groups


def create_section_0(df, total_classification_counts, output_dir):
    """Overall Classification Distribution Pie Chart."""
    logging.info("Creating a pie chart for the distribution of all classifications across groups.")
    classification_counts = pd.Series(total_classification_counts).sort_values(ascending=False)
    total_classification_items = classification_counts.sum()
    logging.info(f"Total detections: {total_classification_items:,}")
    additional_groups = [g for g in classification_counts.index if g not in custom_groups]
    group_order = custom_groups + additional_groups
    group_colors = get_group_colors(additional_groups)
    classification_counts = classification_counts.reindex(group_order, fill_value=0)
    classification_counts = classification_counts[classification_counts > 0]
    data_colors = [group_colors[group] for group in classification_counts.index]
    labels = [
        (group[:10] if percent >= label_threshold else '')
        for group, percent in zip(classification_counts.index, 100 * classification_counts / classification_counts.sum())
    ]

    # Save pie chart
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.pie(
        classification_counts, colors=data_colors, autopct=autopct,
        startangle=90, counterclock=False, textprops={'fontsize': 8}
    )
    ax.axis('equal')
    ax.set_title('Distribution of All Classifications Across Groups', fontsize=10)
    plt.tight_layout()
    classification_pie_filename = os.path.join(output_dir, "classification_distribution_pie.png")
    plt.savefig(classification_pie_filename)
    plt.close()

    # Save legend
    save_legend_as_png(
        title="Classification Distribution",
        colors=data_colors,
        labels=classification_counts.index.tolist(),
        output_filename= "classification_legend.png"
    )


def create_section_1(df, hourly_event_counts, output_dir):
    """Stacked Column Timelines for Each Camera."""
    logging.info("Creating png(s) with event count timelines for each camera.")
    events_list = [
        {'hour': hour, 'camera': camera, 'group_start': group, 'count': count}
        for hour, cameras_dict in hourly_event_counts.items()
        for camera, groups_dict in cameras_dict.items()
        for group, count in groups_dict.items()
    ]
    events_df = pd.DataFrame(events_list)

    if not events_df.empty:
        all_event_groups = events_df['group_start'].unique()
        event_group_order = get_event_group_order(all_event_groups)
        group_colors = get_group_colors([g for g in all_event_groups if g not in custom_groups])
        event_colors = [group_colors[group] for group in event_group_order]
        pivot_table = events_df.pivot_table(
            index=['camera', 'hour'], columns='group_start', values='count', fill_value=0
        )
        cameras = pivot_table.index.get_level_values('camera').unique()
        start_hour = df['hour'].min()
        end_hour = df['hour'].max()
        hourly_range = pd.date_range(start=start_hour, end=end_hour, freq='h')
        index = pd.MultiIndex.from_product([cameras, hourly_range], names=['camera', 'hour'])
        pivot_table = pivot_table.reindex(index, fill_value=0)

        for idx, camera in enumerate(cameras):
            # Reindex to include all groups in event_group_order, filling missing groups with 0
            data = pivot_table.loc[camera].reindex(columns=event_group_order, fill_value=0).sort_index()

            # Skip if the data for this camera is completely empty
            if data.sum().sum() == 0:
                continue  # Skip empty data

            # Generate the plot
            fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
            data.plot(kind='bar', stacked=True, color=event_colors, ax=ax, width=1.0)
            ax.set_title(f'Hourly Sound Events by Group for "{camera}"', fontsize=12)
            ax.set_xlabel('mm/dd hh', fontsize=10)
            ax.set_ylabel('Number of Events', fontsize=10)
            ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            plt.tight_layout(rect=[0, 0.1, 1, 1])

            # Save the plot
            timeline_filename = os.path.join(output_dir, f"{prefix_timeline}{idx + 1}.png")
            plt.savefig(timeline_filename, dpi=300)
            plt.close()


    return (events_df, pivot_table)


def create_section_2(pivot_table, camera_event_counts, events_df, output_dir):
    """Individual Pies for Each Camera."""
    logging.info("Creating png(s) with event mix pies for each camera.")
    if not camera_event_counts:
        logging.warning("No valid data for cameras. Skipping camera-specific pies.")
        return
    all_event_groups = events_df['group_start'].unique()
    event_group_order = get_event_group_order(all_event_groups)
    group_colors = get_group_colors([g for g in all_event_groups if g not in custom_groups])

    camera_data_list, camera_titles, camera_labels_list, camera_colors_list = [], [], [], []
    for camera in camera_event_counts:
        camera_events = events_df[events_df['camera'] == camera]
        group_counts = camera_events.groupby('group_start')['count'].sum()
        data = group_counts.reindex(event_group_order, fill_value=0)
        if data.sum() > 0:
            data_colors = [group_colors[group] for group in data.index]
            labels = [(group[:10] if percent >= label_threshold else '') for group, percent in zip(data.index, 100 * data / data.sum())]
            camera_data_list.append(data)
            camera_titles.append(f'Sound Event Mix for {camera}')
            camera_labels_list.append(labels)
            camera_colors_list.append(data_colors)

    generate_pies(
        data_list=camera_data_list,
        titles=camera_titles,
        labels_list=camera_labels_list,
        colors_list=camera_colors_list,
        output_prefix=os.path.join(output_dir, prefix_camera_pie)
    )
    save_legend_as_png(
        title="Event Types",
        colors=[group_colors[group] for group in event_group_order],
        labels=event_group_order,
        output_filename=f"{cam_pie_legend}.png"  
    )

def create_section_3(group_class_counts, output_dir):
    """Individual Pies for Each Group, Showing Class Distribution."""
    logging.info("Creating png(s) with class mix pies for each group.")

    if not group_class_counts:
        logging.warning("No valid data for groups. Skipping group-specific pies.")
        return

    group_data_list = []
    group_titles = []
    group_labels_list = []
    group_colors_list = []

    for group, class_counts in group_class_counts.items():
        data = pd.Series(class_counts).sort_values(ascending=False)
        total_count = data.sum()
        data = data[data > 0]
        if data.empty:
            continue  # Skip groups with no data

        # Top-k classes and other aggregation
        top_k = 6
        top_classes = data.head(top_k)
        other_count = data.iloc[top_k:].sum()
        if other_count > 0:
            top_classes['Other'] = other_count

        percentages = 100 * top_classes / total_count
        labels = [
            (class_name[:10] if percent >= label_threshold else '')
            for class_name, percent in zip(top_classes.index, percentages)
        ]

        data_colors = sns.color_palette('pastel', len(top_classes))

        group_data_list.append(top_classes)
        group_titles.append(f'{group}')
        group_labels_list.append(labels)
        group_colors_list.append(data_colors)

        # Generate legend for each group
        legend_filename = os.path.join(output_dir, f"{group_pie_legend}_{group}.png")
        save_legend_as_png(
            title=group,
            colors=data_colors,
            labels=top_classes.index.tolist(),
            output_filename=legend_filename
        )

    # Generate pies for groups
    generate_pies(
        data_list=group_data_list,
        titles=group_titles,
        labels_list=group_labels_list,
        colors_list=group_colors_list,
        output_prefix=os.path.join(output_dir, prefix_group_pie)
    )

