# Windhager BioWIN2 Monitoring
#### This project is inspired by the project **[windhager](https://github.com/sessl3r/windhager)** from [sessl3r](https://github.com/sessl3r). Please check him out first!

### Windhager BioWIN2 Logger with Graphite and Grafana on an Synology NAS.
This script is executed every minute on my NAS via the task scheduler.
Requests data from BioWin2 and sends it to graphite, a time-series database.
This data is then visualized with Grafana.

### OIDS
To get all OIDS and convert them to a usable graphite metric path, you have to execute the script [```get_all_metrics.py```](get_all_metrics.py) once. This creates/updates the file [```oids_metrics.txt```](oids_metrics.txt), which will be read from the main script.

### Loki
Here I also use Loki to get my logs into Grafana.
