
# Camera-sounds add-on Log Visualizer

This is a simple python code to visualize sound characteristics over time
using sound log files from the
[Yamcam](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
Home Assistant add-on.

Please report any issues
[here](https://github.com/cecat/CeC-HA-Addons/issues). 

## To use this tool

*python sv -i <input_file> -o <output_file>*

After running the Yamcam addon with *sound_log: true*, a log file is created
in */media/yamcam* on the Home Assistant system.  See the
[Yamcam README](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
for more information about this log.

Yamcam uses the Yamnet model to classify sounds, with scores reported, for each
sample, for each of the 521 sound classes Yamnet is trained to detect.  The 
Yamcam add-on uses a modified class map file which prepends each class with a *group* 
name (people, animals, birds, vehicles, etc.)..

A subdirectory *./plots* will be created to hold individual
png graphs. If *<output_file>* is not specified, a PDF report
will also be placed in the ./plots subdirectory.

The report presently includes:
1. A pie graph showing the distribution of sound groups detected (above 
the *noise_threshold* set for yamcam).
2. Stacked column timelines showing the number and type of sound events
detected by each camera (sound source).
3. Pie graphs showing distribution of event types for each camera (sound source).
4. Pie graphs showing the distribution of individual yamnet *classes* for each
*group*.

You can see an example report 
[here](https://github.com/cecat/soundviz/blob/main/example_report.pdf)
in this repo.
