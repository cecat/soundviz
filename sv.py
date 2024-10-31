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

from svf import (
    plot_dir, check_for_plot_dir, autopct,
    make_pdf, label_threshold, percent_threshold, generate_pies,
    parse_args, prefix_timeline, prefix_camera_pie, prefix_group_pie,
    save_legend_as_png, cam_pie_legend, group_pie_legend
)

def main():
    args = parse_args()

    # Set up output PDF path
    if args.output:
        output_pdf_path = args.output
        if not output_pdf_path.lower().endswith('.pdf'):
            output_pdf_path += '.pdf'
    else:
        output_pdf_path = os.path.join(plot_dir, "Sound_viz.pdf")

    # Set input log file path
    log_file_path = args.input

    print(f"Report will go to {output_pdf_path}.")
    print(f"Check for plot directory {plot_dir}.")
    check_for_plot_dir(plot_dir)

    # Read the CSV file and assign column names
    try:
        df = pd.read_csv(
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
            ]
        )
    except FileNotFoundError:
        print(f"No log file found at {log_file_path}")
        sys.exit(1)

    # Pre-process data
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.floor('h')

    ### Section: Overall Classification Distribution Pie Chart ###
    print("Creating a pie chart for the distribution of all classifications across groups.")

    # Extract group names from 'class' column
    df[['group_name', 'class_name']] = df['class'].str.split('.', n=1, expand=True)
    classification_counts = df['group_name'].value_counts()

    # Define custom groups and colors
    custom_groups = ['environment', 'birds', 'animals', 'people', 'vehicles', 'insects', 'weather']
    custom_colors = ['lightblue', 'red', 'orange', 'green', 'yellow', 'navy', 'brown']

    # Identify additional groups and map colors
    additional_groups = [g for g in classification_counts.index if g not in custom_groups]
    group_order = custom_groups + additional_groups
    additional_colors = sns.color_palette('deep', len(additional_groups))
    group_colors = dict(zip(custom_groups, custom_colors))
    group_colors.update(zip(additional_groups, additional_colors))
    colors = [group_colors[group] for group in group_order]

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
    classification_pie_filename = f"{plot_dir}/classification_distribution_pie.png"
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

    ### Section 1: Stacked Column timelines for each camera ###
    print("Creating png(s) with event count timelines for each camera.")
    cameras = df['camera'].unique()
    events = df[df['group_start'].notna()]
    event_counts = events.groupby(['hour', 'camera', 'group_start']).size().reset_index(name='count')

    # Pivot table for event counts by camera and hour
    pivot_table = event_counts.pivot_table(
        index=['camera', 'hour'],
        columns='group_start',
        values='count',
        fill_value=0
    )

    # Identify all groups in 'group_start' and map colors
    all_event_groups = events['group_start'].unique()
    additional_event_groups = [g for g in all_event_groups if g not in custom_groups]
    event_group_order = custom_groups + list(additional_event_groups)
    additional_event_colors = sns.color_palette('deep', len(additional_event_groups))
    group_colors.update(zip(additional_event_groups, additional_event_colors))
    event_colors = [group_colors[group] for group in event_group_order]

    # Reindex pivot table columns to match event_group_order
    pivot_table = pivot_table.reindex(columns=event_group_order, fill_value=0)

    # Ensure all cameras and hours are present
    start_time = df['hour'].min()
    end_time = df['hour'].max()
    hourly_range = pd.date_range(start=start_time, end=end_time, freq='h')
    index = pd.MultiIndex.from_product([cameras, hourly_range], names=['camera', 'hour'])
    pivot_table = pivot_table.reindex(index, fill_value=0)

    for idx, camera in enumerate(cameras):
        data = pivot_table.loc[camera]
        data = data[event_group_order]
        data.index = pd.to_datetime(data.index)
        data = data.sort_index()

        fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
        data.plot(
            kind='bar',
            stacked=True,
            color=event_colors,
            ax=ax,
            width=1.0
        )
        ax.set_title(f'Hourly Sound Events by Group for "{camera}"', fontsize=12)
        ax.set_xlabel('mm/dd hh', fontsize=10)
        ax.set_ylabel('Number of Events', fontsize=10)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        ax.legend(
            bbox_to_anchor=(0.5, -0.3),
            loc='upper center',
            ncol=min(len(event_group_order), 5),
            frameon=False,
            fontsize='small',
            title_fontsize='small'
        )

        tick_positions = np.arange(0, len(data), max(1, len(data)//10))
        tick_labels = data.index[tick_positions].strftime('%m/%d %H')
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)

        plt.tight_layout(rect=[0, 0.1, 1, 1])
        plt.savefig(f"{plot_dir}/{prefix_timeline}{idx + 1}.png", dpi=300)
        plt.close()

    ### Section 2: Individual pies for each camera ###
    print("Creating png(s) with event mix pies for each camera.")
    total_counts = pivot_table.groupby('camera').sum()

    camera_data_list = []
    camera_titles = []
    camera_labels_list = []
    camera_colors_list = []

    for camera in total_counts.index:
        data = total_counts.loc[camera]
        data = data[data > 0]
        if data.empty:
            continue  # Skip cameras with no data
        percentages = 100 * data / data.sum()
        data_colors = [group_colors[group] for group in data.index]
        labels = [
            (group[:10] if percent >= label_threshold else '')
            for group, percent in zip(data.index, percentages)
        ]
        camera_data_list.append(data)
        camera_titles.append(f'Sound Event Mix for {camera}')
        camera_labels_list.append(labels)
        camera_colors_list.append(data_colors)

    generate_pies(
        data_list=camera_data_list,
        titles=camera_titles,
        labels_list=camera_labels_list,
        colors_list=camera_colors_list,
        output_prefix=prefix_camera_pie
    )

    legend_filename = f'{cam_pie_legend}.png'
    save_legend_as_png(
        title='Event Types',
        colors=[group_colors[group] for group in event_group_order],
        labels=event_group_order,
        output_filename=legend_filename
    )

    ### Section 3: Individual pies for each group, showing class distribution ###
    print("Create png(s) with class mix pies for each group.")
    class_counts = df.groupby(['group_name', 'class_name']).size().reset_index(name='count')
    groups = class_counts['group_name'].unique()

    group_data_list = []
    group_titles = []
    group_labels_list = []
    group_colors_list = []

    for group in groups:
        data = class_counts[class_counts['group_name'] == group].set_index('class_name')['count']
        total_count = data.sum()
        data = data.sort_values(ascending=False)

        top_k = 6  # Number of top classes to display
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

        legend_filename = f'{group_pie_legend}{group}.png'
        save_legend_as_png(
            title=group,
            colors=data_colors,
            labels=top_classes.index.tolist(),
            output_filename=legend_filename
        )

    generate_pies(
        data_list=group_data_list,
        titles=group_titles,
        labels_list=group_labels_list,
        colors_list=group_colors_list,
        output_prefix=prefix_group_pie
    )

    ### Generate the PDF Report ###
    make_pdf(output_pdf_path, df)

if __name__ == "__main__":
    main()

