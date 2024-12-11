
# Camera-sounds add-on Log Visualizer

This python code creates a report that visualizes sound characteristics detected
over time by microphones (typically on cameras) captured in sound log files 
created by the
[Yamcam](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
Home Assistant add-on or the command line utility
[Yamnet Sound Profiler (YSP)](https://github.com/cecat/ysp).

The tool produces a report that includes:
1. A pie graph showing the distribution of sound groups detected (above 
the *noise_threshold* set for yamcam).
2. Stacked column timelines showing the number and type of sound events
detected by each camera (sound source).
3. Pie graphs showing distribution of event types for each camera (sound source).
4. Pie graphs showing the distribution of individual yamnet *classes* for each
*group*.

This code has only been tested on MacOS (running Sequoia 15.1) with Apple M2
8-core processor.

## Reqirements

This tool is written in Python and requires Python 3.7+ and the following libraries,
which are included in requirements.txt::
* pandas
* matplotlib
* seaborn
* reportlab
* pillow
* tqdm
* multiprocessing (built-in module)

## Setup Instructions (from Linux command line)

1. Clone this repository
```
git clone git@github.com:cecat/soundviz.git
cd soundviz
```

2. Create a Virtual Environment (Recommended)
```
python3 -m venv viz_env
source viz_env/bin/activate
```

3. Install dependencies (first update pip for good measure)
```
pip install --upgrade pip
pip install -r requirements.txt
```

4. Create a ./logs directory for log files to be analyzed.
```
mkdir ./logs
```

5. Move log files into ./logs.

**To analyze logs from Home Assistant Yamcam add-on:**
Use scp to copy the logs from your Home Assistant server to the machine you are using to run the soundviz code. Log into your Home Assistant server vi ssh or use the Terminal window:

```
cd /media/yamcam
ls -lt
scp *.csv <your_username>@<yourhost>:/<path to>/soundviz/logs/
```

**To analyze logs from the command line SVP tool:**
Move or copy logs from the directory where you ran the SVP tool, within its *logs*
subdirectory.  From your soundviz directory:
```
cp <path_to_svp>/logs/*.csv ./logs
```

## Example Usage

### Select a logfile from ./logs to use as input, then run the tool.
```
python sv.py -i *input.csv* -o *output.pdf*
```
Default input is *./logs/log.csv* and default output is *./plots/Sound_viz.pdf*.

The tool will create a ./plots directory (if not alread there) within which it
will place png images and a report, *Sound_viz.pdf*.

### Options
Default logging output is ERROR, so running as above will produce a log message
when the report is prepared, indicating the pathname for the report, with two
exceptions.  If there are fatal errors (e.g., cannot find specified input
log file) these will be printed.  If the log file is large (>1M lines) a
courtesy message will be printed to let you know how 
many 50k-line chunks are going to be processed (i.e., that it might
take a few minutes). A progress bar will also be used to indicate progress.

The *-v* or *--verbose* option sets logging level to INFO, which will log messages 
indicating what is being done as well as displaying the progress bar to show progress.

The *-s* or *--silent* option will set logging level to WARNING, which will only
log messages if something went awry, such as not finding the specified log file
(i.e., a fatal error) or there is missing data (e.g., something that would cause
the report to be incomplete would not cause the tool to bail). If silent mode is
not specified, a progress bar will be displayed.

The *-c* or *--cores* option allows you to specify how many cores to use, up to the
number of cores available in your processor.

## More Information

This tool is desiged specifically for sound log files produced by Yamcam or
the command line tool Yamnet Sound Proviler (ysp), which can produce
log files -- csv files with millions of rows.  The tool processes these log files in 50k-row
chunks, each of which take 10-15s to process.  Using the built-in *multiprocessing*
Python module, chunks are processed in parallel
across either cores or fewer if set using the *-c* (or *--cores*) option.

ysp and yamcam3 close their logs upon exit and create new logs when starting up, so
a restart will mean a new log file. In case helpful, I've included
[combiner.sh](https://github.com/cecat/soundviz/blob/main/combiner.sh), 
a shell script that you can use to combine all of the files in your *./logs* directory.

Both Yamcam and the ysp use the Yamnet model to classify sounds, with scores reported, for each
sample, for each of the 521 sound classes Yamnet is trained to detect.  These 
use a modified class map file which prepends each class with a *group* 
name (people, animals, birds, vehicles, etc.).

The tools continuously analyze 0.975s sound samples from RTSP feed audio channels, 
producing scores (0.0 to 1.0. Yamcam sound logs have the form:
```
datetime,camera,group,group_score,class,class_score,group_start,group_end
```

All scores above the *noise_threshold* setting
(default 0.1) are logged in the *class* and *class_score* columns; those
below this threshold are ignored.  *Group*
scores are calculated based on the scores of yamnet classes categorized into
a set of several dozen *groups* (e.g., people, music, insects...), and these are
logged in the *group* and *group_score* columns.

*Sound events* (defined by three parameters in the microphones.yaml config file)
are repeated detections of a given class that persist over the scale of seconds
or minutes (e.g., a barking dog or siren). The *group_start* and *group_end* columns
are used to log the start and end of a given event.


After running the YSP command-line tool or the Yamcam addon with *sound_log: true*
(default for YSP as there is no other reason to run it!), a log file is created.
For the
[Yamnet Sound Profiler (YSP)](https://github.com/cecat/ysp)
command-line tool, the logs will be placed in *...(path-to-ysp)/ysp/logs*.
The 
[Yamcam Home Assistant Add-on](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
will place the logs in */media/yamcam* on the Home Assistant server. 

You can see an example report 
[here](https://github.com/cecat/soundviz/blob/main/example_report.pdf)
in this repo (note you can see the October 31 (Halloween) trick-or-treat activities especially
at the cameras named "front" and "entry").

Please report any issues
[here](https://github.com/cecat/soundviz/issues). 
