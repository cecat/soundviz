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
output_file="./logs/combined.csv"

# Remove the output file if it exists
[ -f "$output_file" ] && rm "$output_file"

# Find all CSV files, sort them in reverse order, and prepend them to the output
for file in $(ls "$input_dir"/*.csv | sort -r); do
    echo "Processing $file"
    # Prepend the current file to the output
    cat "$file" > temp_combined.csv
    [ -f "$output_file" ] && cat "$output_file" >> temp_combined.csv
    mv temp_combined.csv "$output_file"
done

echo "Combined CSV saved to $output_file"

