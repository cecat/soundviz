
# Camera-sounds add-on Log Visualizer

This is a simple python code to visualize sound characteristics over time
using sound log files from the
[Yamcam](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
Home Assistant add-on.

The tool produces a report that includes:
1. A pie graph showing the distribution of sound groups detected (above 
the *noise_threshold* set for yamcam).
2. Stacked column timelines showing the number and type of sound events
detected by each camera (sound source).
3. Pie graphs showing distribution of event types for each camera (sound source).
4. Pie graphs showing the distribution of individual yamnet *classes* for each
*group*.

## Reqirements

This tool is written in Python and requires Python 3.7+ and the following libraries:
* pandas
* matplotlib
* seaborn
* reportlab
* Pillow

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

3. Install dependencies
```
pip install -r requirements.txt
```

4. Create a ./logs directory for log files to be analyzed.
```
mkdir ./logs
```

5. If using this tool to analyze logs from Home Assistant Yamcam add-on.  
Move copies of logs of interest into ./logs.

From your Home Assistant server running Yamcam, copy a log file to ./logs.
(log into Home Assistant using *SSH* or *Terminal*)

**FROM HOME ASSISTANT CLI:**
```
cd /media/yamcam
ls -lt
scp *.csv <your_username>@<yourhost>:/<path to>/soundviz/logs/
```

6. If using this tool to analyze logs from the command line SVP tool, move or
copy logs from the directory where you ran the SVP tool, within its *logs*
subdirectory.  

## Example Usage

### Select a logfile from ./logs to use as input, then run the tool.
```
python sv.py -i *input.csv* -o *output.pdf*
```
Default input is *./logs/log.csv* and default output is *./plots/Sound_viz.pdf*.

The tool will create a ./plots directory (if not alread there) within which it
will place png images and a report, *Sound_viz.pdf*.

## More Information

This tool is desiged specifically for sound log files produced by Yamcam, which 
uses the Yamnet model to classify sounds, with scores reported, for each
sample, for each of the 521 sound classes Yamnet is trained to detect.  The 
Yamcam add-on uses a modified class map file which prepends each class with a *group* 
name (people, animals, birds, vehicles, etc.).

Yamcam continuously analyzes 0.975s sound samples from RTSP feed audio channels, 
producing scores (0.0 to 1.0. Yamcam sound logs have the form:
```
datetime,camera,group,group_score,class,class_score,group_start,group_end
```

All scores above Yamcam's *noise_threshold* setting
(default 0.1) are logged in the *class* and *class_score* columns.  Group
scores are also calculated based on the scores of yamnet classes categorized into
a set of several dozen *groups* (e.g., people, music, insects...), and these are
logged in the *group* and *group_score* columns. Yamcam also has settings to 
define *sound events* that persist over the scale of seconds or minutes (e.g., a
barking dog or siren), and the *group_start* and *group_end* columns are used to
log the start and end of a given event.


After running the Yamcam addon with *sound_log: true*, a log file is created
in */media/yamcam* on the Home Assistant system.  See the
[Yamcam README](https://github.com/cecat/CeC-HA-Addons/tree/main/yamcam3)
for more information about this log.

You can see an example report 
[here](https://github.com/cecat/soundviz/blob/main/example_report.pdf)
in this repo (note you can see the October 31 (Halloween) trick-or-treat activities especially
at the cameras named "front" and "entry").

Please report any issues
[here](https://github.com/cecat/CeC-HA-Addons/issues). 
