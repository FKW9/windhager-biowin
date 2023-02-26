# Windhager BioWIN2 Monitoring
#### This project is inspired by the project **[windhager](https://github.com/sessl3r/windhager)** from [sessl3r](https://github.com/sessl3r). Please check him out first!

### Windhager BioWIN2 Logger with Graphite and Grafana on an Synology NAS.
This script is executed every minute on my NAS via the task scheduler.
Requests data from BioWin2 and sends it to graphite, a time-series database.
This data is then visualized with Grafana.

### Setup

1. Fill in your Host IPs, passwords and ports for your host machines in the three python files. ALso you must change the paths for the debug files.

2. Replace the file [```EbenenTexte_de.xml```](EbenenTexte_de.xml) and [```VarIdentTexte_de.xml```](VarIdentTexte_de.xml) with your own. You find them under [http://<WINDHAGER_IP>/res/xml/](http://<WINDHAGER_IP>/res/xml/).

3. To get all OIDS and convert them to a usable graphite metric path, you have to execute the script [```get_all_metrics.py```](get_all_metrics.py) once. This creates/updates the file [```oids_metrics.txt```](oids_metrics.txt), which will be read from the main script.

4. Execute the main script [windhager.py](windhager.py)

### Loki
Here I also use Loki to get my logs into Grafana.
