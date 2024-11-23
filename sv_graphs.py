# 
# Create graphs by section
#
#
# sv_graphs.py

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

from svf import (
    plot_dir, check_for_plot_dir, autopct,
    make_pdf, label_threshold, percent_threshold, generate_pies,
    parse_args, prefix_timeline, prefix_camera_pie, prefix_group_pie,
    save_legend_as_png, cam_pie_legend, group_pie_legend, setup_logging
)


class SoundVisualizer:
    def __init__(self, df, total_classification_counts, hourly_event_counts, camera_event_counts, group_class_counts, plot_dir):
        self.df = df
        self.total_classification_counts = total_classification_counts
        self.hourly_event_counts = hourly_event_counts
        self.camera_event_counts = camera_event_counts
        self.group_class_counts = group_class_counts
        self.plot_dir = plot_dir

        # Initialize any other attributes if necessary
        self.custom_groups = ['environment', 'birds', 'animals', 'insects', 'weather',
                              'people', 'music', 'vehicles', 'alert']
        self.custom_colors = ['green', 'lightgreen', '#B6885C', '#FF55BC', 'lightblue',
                              '#3D02C5', '#05ABD7', 'gray', 'red']
        self.group_colors = dict(zip(self.custom_groups, self.custom_colors))

    def create_graphs(self):
        self.create_overall_classification_pie_chart()
        self.create_timelines()
        self.create_camera_pies()
        self.create_group_pies()


    def create_overall_classification_pie_chart(self):
        classification_counts = pd.Series(self.total_classification_counts).sort_values(ascending=False)
        total_classification_items = classification_counts.sum()
        logging.info(f"Total detections (class/class-score rows): {total_classification_items:,}")

        # Identify additional groups and map colors
        additional_groups = [g for g in classification_counts.index if g not in self.custom_groups]
        group_order = self.custom_groups + additional_groups
        additional_colors = sns.color_palette('deep', len(additional_groups))

        # Create a local copy of group_colors to avoid modifying the original
        group_colors = self.group_colors.copy()
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
        classification_pie_filename = f"{self.plot_dir}/classification_distribution_pie.png"
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

    def create_timelines(self):
        # Prepare the DataFrame for timelines
        events_list = []
        for hour, cameras_dict in self.hourly_event_counts.items():
            for camera, groups_dict in cameras_dict.items():
                for group_start, count in groups_dict.items():
                    events_list.append({
                        'hour': hour,
                        'camera': camera,
                        'group_start': group_start,
                        'count': count
                    })
        events_df = pd.DataFrame(events_list)

        # Pivot table for event counts by camera and hour
        if not events_df.empty:
            pivot_table = events_df.pivot_table(
                index=['camera', 'hour'],
                columns='group_start',
                values='count',
                fill_value=0
            )
            # Identify all groups in 'group_start' and map colors
            all_event_groups = events_df['group_start'].unique()
            additional_event_groups = [g for g in all_event_groups if g not in self.custom_groups]
            event_group_order = self.custom_groups + list(additional_event_groups)
            additional_event_colors = sns.color_palette('deep', len(additional_event_groups))

            # Create a local copy of group_colors
            group_colors = self.group_colors.copy()
            group_colors.update(zip(additional_event_groups, additional_event_colors))
            event_colors = [group_colors[group] for group in event_group_order]

            # Reindex pivot_table columns to match event_group_order
            pivot_table = pivot_table.reindex(columns=event_group_order, fill_value=0)

            # Ensure all cameras and hours are present
            cameras = pivot_table.index.get_level_values('camera').unique()
            start_hour = self.df['hour'].min()
            end_hour = self.df['hour'].max()
            hourly_range = pd.date_range(start=start_hour, end=end_hour, freq='h')
            index = pd.MultiIndex.from_product([cameras, hourly_range], names=['camera', 'hour'])
            pivot_table = pivot_table.reindex(index, fill_value=0)

            for idx, camera in enumerate(cameras):
                data = pivot_table.loc[camera]
                data = data[event_group_order]
                data.index = pd.to_datetime(data.index)
                data = data.sort_index()

                if data.sum().sum() == 0:
                    continue  # Skip cameras with no data

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
                plt.savefig(f"{self.plot_dir}/{prefix_timeline}{idx + 1}.png", dpi=300)
                plt.close()

        else:
            logging.warning("No event data available for timelines.")

    def create_camera_pies(self):
        logging.info("Creating png(s) with event mix pies for each camera.")

        if self.camera_event_counts:
            # Convert camera_event_counts to DataFrame
            camera_data = pd.DataFrame.from_dict(self.camera_event_counts, orient='index', columns=['count'])
            cameras = camera_data.index.tolist()

            # Prepare the DataFrame for events
            events_list = []
            for hour, cameras_dict in self.hourly_event_counts.items():
                for camera, groups_dict in cameras_dict.items():
                    for group_start, count in groups_dict.items():
                        events_list.append({
                            'hour': hour,
                            'camera': camera,
                            'group_start': group_start,
                            'count': count
                        })
            events_df = pd.DataFrame(events_list)

            # Identify all groups in 'group_start' and map colors
            all_event_groups = events_df['group_start'].unique()
            additional_event_groups = [g for g in all_event_groups if g not in self.custom_groups]
            event_group_order = self.custom_groups + list(additional_event_groups)
            additional_event_colors = sns.color_palette('deep', len(additional_event_groups))

            # Create a local copy of group_colors
            group_colors = self.group_colors.copy()
            group_colors.update(zip(additional_event_groups, additional_event_colors))

            # Prepare data for camera pies
            camera_data_list = []
            camera_titles = []
            camera_labels_list = []
            camera_colors_list = []

            for camera in cameras:
                # Get event counts per group_start for this camera
                camera_events = events_df[events_df['camera'] == camera]
                group_counts = camera_events.groupby('group_start')['count'].sum()
                data = group_counts.reindex(event_group_order, fill_value=0)
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

            # Generate camera pies
            generate_pies(
                data_list=camera_data_list,
                titles=camera_titles,
                labels_list=camera_labels_list,
                colors_list=camera_colors_list,
                output_prefix=prefix_camera_pie
            )

            # Generate legend for camera pies
            legend_filename = f'{cam_pie_legend}.png'
            save_legend_as_png(
                title='Event Types',
                colors=[group_colors[group] for group in event_group_order],
                labels=event_group_order,
                output_filename=legend_filename
            )
        else:
            logging.warning("No valid data for cameras. Skipping camera-specific pies.")

    def create_group_pies(self):
        logging.info("Creating png(s) with class mix pies for each group.")

        if self.group_class_counts:
            group_data_list = []
            group_titles = []
            group_labels_list = []
            group_colors_list = []

            for group, class_counts in self.group_class_counts.items():
                data = pd.Series(class_counts).sort_values(ascending=False)
                total_count = data.sum()
                data = data[data > 0]
                if data.empty:
                    continue  # Skip groups with no data

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

                # Generate legend for each group
                legend_filename = f'{group_pie_legend}{group}.png'
                save_legend_as_png(
                    title=group,
                    colors=data_colors,
                    labels=top_classes.index.tolist(),
                    output_filename=legend_filename
                )

            # Generate group pies
            generate_pies(
                data_list=group_data_list,
                titles=group_titles,
                labels_list=group_labels_list,
                colors_list=group_colors_list,
                output_prefix=prefix_group_pie
            )
        else:
            logging.warning("No valid data for groups. Skipping group-specific pies.")

