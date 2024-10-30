import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker  
import seaborn as sns
from pathlib import Path
import numpy as np
import os
import glob
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import blue
from PIL import Image

url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"

def check_for_plot_dir():
    try:
        os.makedirs(plot_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create plot directory '{plot_dir}': {e}")
        sys.exit(1)

# Directories
sound_log_dir = './'
plot_dir = './plots'

# Filenames
log_filename = 'log.csv'
report_file = 'Sound_viz.pdf'
output_pdf_path = os.path.join(plot_dir, report_file)
log_file_path = Path(sound_log_dir) / log_filename

print(f"Report will go to {output_pdf_path}.")

# Check for (and if necessary, create) plot directory
print(f"Check for plot directory {plot_dir}.")
check_for_plot_dir()

# Read the CSV file without headers and assign column names
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
    print(f"No log file found")
    sys.exit(1)

############ Pre-Process and Prep the data

df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.floor('h')
events = df[df['group_start'].notna()]

# Calculate event counts
event_counts = events.groupby(['hour', 'camera', 'group_start']).size().reset_index(name='count')

# Create pivot table
pivot_table = event_counts.pivot_table(
    index=['camera', 'hour'],
    columns='group_start',
    values='count',
    fill_value=0
)

# These common groups will always go first and have the same colors
custom_groups = ['environment', 'birds', 'animals', 'people', 'vehicles']
custom_colors = ['lightblue', 'red', 'orange', 'green', 'yellow']

# Identify additional groups and map colors
all_groups = pivot_table.columns.tolist()
additional_groups = [g for g in all_groups if g not in custom_groups]
group_order = custom_groups + additional_groups
additional_colors = sns.color_palette('deep', len(additional_groups))
group_colors = dict(zip(custom_groups, custom_colors))
group_colors.update(zip(additional_groups, additional_colors))
colors = [group_colors[group] for group in group_order]

# Define hourly range and MultiIndex
start_time = df['hour'].min()
end_time = df['hour'].max()
hourly_range = pd.date_range(start=start_time, end=end_time, freq='h')
cameras = df['camera'].unique()
index = pd.MultiIndex.from_product([cameras, hourly_range], names=['camera', 'hour'])
pivot_table = pivot_table.reindex(index, fill_value=0).reset_index()
pivot_table = pivot_table.set_index(['camera', 'hour'])

############ Generate Stacked Column timelines for each camera, showing events by group

# Plot a stacked column timeline for each camera and save individually
for idx, camera in enumerate(cameras):
    data = pivot_table.loc[camera]
    data = data[group_order]
    data.index = pd.to_datetime(data.index)
    data = data.sort_index()

    ax = data.plot(kind='bar', stacked=True, color=colors, figsize=(15, 6), width=1.0)
    ax.set_title(f'Hourly Sound Events by Group for "{camera}"')
    ax.set_xlabel('Date and Hour')
    ax.set_ylabel('Number of Events')
    # only integers in the y-axis
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax.legend(
        title='Group',
        bbox_to_anchor=(0.5, -0.25),  # Centered at the bottom
        loc='upper center',
        ncol=len(group_order),  # Adjust columns to fit all legend items horizontally
        frameon=False
    )

    tick_positions = np.arange(0, len(data), 4)
    tick_labels = data.index[tick_positions].strftime('%m/%d %H')
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45)

    print(f"Create png for source camera {idx+1}.")

    plt.tight_layout()
    plt.savefig(f"{plot_dir}/timeline_camera_{idx + 1}.png")
    plt.close()

############ Generate Pies for each camera, showing event distro

# Parameters for pie charts
label_threshold = 5
percent_threshold = 3

# Sum event counts by group for each camera
total_counts = pivot_table.groupby('camera').sum()
total_counts = total_counts[group_order]
log_start = df['datetime'].min().strftime('%Y/%m/%d %H:%M')
log_end = df['datetime'].max().strftime('%Y/%m/%d %H:%M')

# Generate camera pies and save in batches of up to 6 pies per png image
print("Create png(s) with event mix pies for each camera.")

num_cameras = len(total_counts.index)
pies_per_image = 6  # Max pies per image
num_batches = (num_cameras + pies_per_image - 1) // pies_per_image

for batch in range(num_batches):
    start_idx = batch * pies_per_image
    end_idx = min(start_idx + pies_per_image, num_cameras)
    batch_cameras = total_counts.index[start_idx:end_idx]
    num_pies = len(batch_cameras)
    num_cols = 3
    num_rows = (num_pies + num_cols - 1) // num_cols

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    for idx, camera in enumerate(batch_cameras):
        data = total_counts.loc[camera]
        data = data[data > 0]
        percentages = 100 * data / data.sum()
        data_colors = [group_colors[group] for group in data.index]
        # Truncate class names to 10 characters for labels
        labels = [
            (class_name[:11] if percent >= label_threshold else '')
            for class_name, percent in zip(data.index, percentages)
        ]


        def autopct(pct):
            return f'{pct:.1f}%' if pct >= percent_threshold else ''

        axes[idx].pie(
            data,
            labels=labels,
            colors=data_colors,
            autopct=autopct,
            startangle=90,
            counterclock=False
        )
        axes[idx].set_title(f'Sound Event Mix for {camera}')

    # Hide any unused subplots
    for idx in range(num_pies, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.savefig(f"{plot_dir}/camera_pies_{batch + 1}.png")
    plt.close()

############ Generate Pies for each group, showing class distro

# Parse and count occurrences by group and class
df[['group_name', 'class_name']] = df['class'].str.split('.', n=1, expand=True)
class_counts = df.groupby(['group_name', 'class_name']).size().reset_index(name='count')
groups = class_counts['group_name'].unique()

# Generate group pies and save in batches of up to 6 pies per image
print("Create png(s) with class mix pies for each group.")

num_groups = len(groups)
pies_per_image = 6  # Max pies per image
num_batches = (num_groups + pies_per_image - 1) // pies_per_image

for batch in range(num_batches):
    start_idx = batch * pies_per_image
    end_idx = min(start_idx + pies_per_image, num_groups)
    batch_groups = groups[start_idx:end_idx]
    num_pies = len(batch_groups)
    num_cols = 3
    num_rows = (num_pies + num_cols - 1) // num_cols

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(15, 5 * num_rows))
    axes = axes.flatten()

    for idx, group in enumerate(batch_groups):
        data = class_counts[class_counts['group_name'] == group].set_index('class_name')['count']
        percentages = 100 * data / data.sum()
        # Truncate group names to 10 characters for labels
        labels = [
            (group[:10] if percent >= label_threshold else '')
            for group, percent in zip(data.index, percentages)
        ]


        def autopct(pct):
            return f'{pct:.1f}%' if pct >= percent_threshold else ''

        num_classes = len(data)
        data_colors = sns.color_palette('pastel', num_classes)

        axes[idx].pie(
            data,
            labels=labels,
            colors=data_colors,
            autopct=autopct,
            startangle=90,
            counterclock=False
        )
        axes[idx].set_title(f'Class Distribution within Group: {group}')

    # Hide any unused subplots
    for idx in range(num_pies, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.savefig(f"{plot_dir}/group_pies_{batch + 1}.png")
    plt.close()

############ Generate PDF report

print(f"Creating PDF report at {output_pdf_path}.")

# URL and footer text definitions
url = "https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3"
log_start_date = df['datetime'].min().strftime('%Y-%m-%d %H:%M')
log_end_date = df['datetime'].max().strftime('%Y-%m-%d %H:%M')
footer_text_prefix = f"Sound visualization for the period of {log_start_date} through {log_end_date} using the Home Assistant add-on "
footer_text_yamcam = "Yamcam"
footer_text_suffix = "."

# Create PDF canvas
c = canvas.Canvas(output_pdf_path)

# Section 1: Stacked column timelines, one per page
timeline_paths = sorted(glob.glob(f"{plot_dir}/timeline_camera_*.png"))
for image_path in timeline_paths:
    c.setPageSize(landscape(letter))
    img = Image.open(image_path)
    img_width, img_height = img.size
    scale = min((letter[1] - 144) / img_width, (letter[0] - 144) / img_height)
    new_width = img_width * scale
    new_height = img_height * scale
    x = (letter[1] - new_width) / 2 + 0.5 * inch
    y = (letter[0] - new_height) / 2
    c.drawImage(image_path, x, y, width=new_width, height=new_height)

    # Add footer with visible clickable "Yamcam" link
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, 0.5 * inch, footer_text_prefix)
    yamcam_text_x = c.stringWidth(footer_text_prefix) + 0.75 * inch
    c.setFillColor(blue)
    c.drawString(yamcam_text_x, 0.5 * inch, footer_text_yamcam)
    c.setFillColor("black")
    c.drawString(yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.5 * inch, footer_text_suffix)
    c.linkURL(url, (yamcam_text_x, 0.5 * inch, yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.6 * inch), relative=1)
    c.showPage()

# Section 2: Camera pies, up to 6 per page, in rows of 3
camera_pie_paths = sorted(glob.glob(f"{plot_dir}/camera_pies_*.png"))
for image_path in camera_pie_paths:
    c.setPageSize(landscape(letter))
    img = Image.open(image_path)
    img_width, img_height = img.size
    scale = min((letter[1] - 144) / img_width, (letter[0] - 144) / img_height)
    new_width = img_width * scale
    new_height = img_height * scale
    x = (letter[1] - new_width) / 2
    y = (letter[0] - new_height) / 2
    c.drawImage(image_path, x, y, width=new_width, height=new_height)

    # Add footer with visible clickable "Yamcam" link
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, 0.5 * inch, footer_text_prefix)
    yamcam_text_x = c.stringWidth(footer_text_prefix) + 0.75 * inch
    c.setFillColor(blue)
    c.drawString(yamcam_text_x, 0.5 * inch, footer_text_yamcam)
    c.setFillColor("black")
    c.drawString(yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.5 * inch, footer_text_suffix)
    c.linkURL(url, (yamcam_text_x, 0.5 * inch, yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.6 * inch), relative=1)
    c.showPage()

# Section 3: Group pies, up to 6 per page, in rows of 3
group_pie_paths = sorted(glob.glob(f"{plot_dir}/group_pies_*.png"))
for image_path in group_pie_paths:
    c.setPageSize(landscape(letter))
    img = Image.open(image_path)
    img_width, img_height = img.size
    scale = min((letter[1] - 144) / img_width, (letter[0] - 144) / img_height)
    new_width = img_width * scale
    new_height = img_height * scale
    x = (letter[1] - new_width) / 2
    y = (letter[0] - new_height) / 2
    c.drawImage(image_path, x, y, width=new_width, height=new_height)

    # Add footer with visible clickable "Yamcam" link
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, 0.5 * inch, footer_text_prefix)
    yamcam_text_x = c.stringWidth(footer_text_prefix) + 0.75 * inch
    c.setFillColor(blue)
    c.drawString(yamcam_text_x, 0.5 * inch, footer_text_yamcam)
    c.setFillColor("black")
    c.drawString(yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.5 * inch, footer_text_suffix)
    c.linkURL(url, (yamcam_text_x, 0.5 * inch, yamcam_text_x + c.stringWidth(footer_text_yamcam), 0.6 * inch), relative=1)
    c.showPage()

# Save the PDF
c.save()

print(f"PDF report created at {output_pdf_path}")

