#!/bin/bash
#
# A tool for combining multiple .csv log files (from ysp or the HA addon yamcam3)
# into a single .csv log chronologically ordered.  This is especially
# useful given a restart will create a new log (thus minimal gaps in timeline)
# but also good to use if there are gaps.  Note if you made changes to score
# thresholds or to the parameters defining sound events then the resulting log
# files will also result in differences (such as fewer or a greater number
# of events if you tightened or loosened the parameters).

# Directory containing the input CSV files
input_dir="./logs"

# Output file
#output_file="./logs/combined.csv"
# Remove the output file if it exists
#[ -f "$output_file" ] && rm "$output_file"
# Let's be safer and, if the file already exists, append date/time to the new file
# (and then ignore all csv files that begin with "combined"!)
# base_file="./logs/combined.csv"

# If the output file already exists, append date-time to the NEW output filename
if [ -f "$base_file" ]; then
    timestamp=$(date +"%Y%m%d-%H%M")
    output_file="./logs/combined-$timestamp.csv"
else
    output_file="$base_file"
fi

# Find all CSV files, sort them in reverse order, and prepend them to the output
for file in $(ls "$input_dir"/*.csv 2>/dev/null | sort -r); do
    filename=$(basename "$file")

    # Skip files that begin with "combined"
    if [[ $filename == combined* ]]; then
        echo "Skipping $file"
        continue
    fi

    echo "Processing $file"

    # Prepend the current file to the output
    # The logic here: we write the current file first, then append the existing output_file
    cat "$file" > temp_combined.csv
    [ -f "$output_file" ] && cat "$output_file" >> temp_combined.csv
    mv temp_combined.csv "$output_file"
done


echo "Output file:    $output_file"
line_count=$(wc -l < "$output_file")
echo "Number of rows: $line_count"
