import json
import logging
import logging.handlers as handlers
import pickle
import re
import socket
import struct
import subprocess
import sys
import time
from threading import Timer
from typing import List
from loki_client import LokiHandler

import requests
from requests.auth import HTTPDigestAuth

""" EXIT PROGRAM AFTER 50 SECONDS """
EXIT_TIMER = Timer(50, sys.exit)
EXIT_TIMER.start()

WINDHAGER_HOST     = "192.168.8.74"
WINDHAGER_PASSWORD = 'vw8LN7L76Qv?'
WINDHAGER_USER     = 'Service'

GRAPHITE_HOST = '192.168.8.42'  # IP address of the NAS
GRAPHITE_PORT = 2004            # port for carbon receiver, 2004 is for pickled data
GRAPHITE_TIMEOUT = 5

# units = ['%', '°C', '20', 'min', 'K', 'h', 't', '21', 's', 'U/min', 'kg', 'd']
# units/ids = [('%', 4), ('°C', 1), ('20', 20), ('min', 6), ('K', 2), ('h', 5), ('t', 46), ('21', 21), ('s', 7), ('U/min', 10), ('kg', 45), ('d', 19)]
ALLOWED_UNIT_IDS = [4, 1, 6, 2, 5, 46, 7, 10, 45, 19, 0]


def init_logger(file: str = '/volume1/docker/python/debug_windhager.log'):
    """ Init logger. """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logHandler = handlers.RotatingFileHandler(
        file,
        maxBytes=1e8,
        backupCount=1
    )
    formatter = logging.Formatter(
        '%(asctime)s %(funcName)s %(lineno)d %(levelname)s : %(message)s')

    lokiHandler = LokiHandler(logging.INFO, "windhager")
    logHandler.setFormatter(formatter)
    logger.addHandler(lokiHandler)
    logger.addHandler(logHandler)


def update_windhager_ip(file_path: str = "/volume1/docker/python/windhager.py") -> int:
    """
    Update the IP to the windhager.

    First approach was to use ARP table, but the arp table only updates when the IP gets pinged at least once.
    So, i just brute force it.

    Update: I assigned a static IP to windhager, so this function is obsolete.

    Parameters
    ----------
    file_path : str, optional
        path to THIS file, by default "/volume1/docker/python/windhager.py"
    """
    ips = []
    # mac = "e0-91-f5-0e-f3-ce"

    # logging.info("Trying to update IP...")

    # if sys.platform == "win32":
    #     cmd = f'arp -a | findstr "{mac}" '

    #     returned_output = str(subprocess.check_output((cmd), shell=True, stderr=subprocess.STDOUT))

    #     for m in re.finditer('192.168.8.', returned_output):
    #         ips.append(returned_output[m.start():m.end()+3].strip())

    # if sys.platform == "linux":

    #     # flush arp table
    #     # subprocess.check_call(("ip -s -s neigh flush all"), shell=True)

    #     mac = mac.replace("-", ".")
    #     cmd = f'arp -a | grep "{mac}" '

    #     returned_output = str(subprocess.check_output((cmd), shell=True, stderr=subprocess.STDOUT))

    #     for m in re.finditer('192.168.8.', returned_output):
    #         ips.append(returned_output[m.start():m.end()+3].replace(")", "").strip())


    # new_ip = None

    if len(ips) > 0:
        logging.info("Found possible IPs: %s", str(ips))
        for ip in ips:
            try:
                response = requests.get(f'http://{ip}/api/1.0/lookup', timeout=10)
                if response.status_code == 401:
                    new_ip = ip
            except:
                continue

    else:
        logging.info("Brute forcing IPs...")
        ips = [_ for _ in range(70, 201)] + [_ for _ in range(20, 70)] # dhcp range
        for i in ips:
            try:
                # logging.info('Try: 192.168.8.%d', i)
                response = requests.get(f'http://192.168.8.{i}/api/1.0/lookup', timeout=5)
                if response.status_code == 401:
                    new_ip = f'192.168.8.{i}'
                    break
            except:
                continue

    if new_ip is None:
        logging.error("Updating IP failed!")
        return 1

    logging.info('Updating Windhager IP to: %s', new_ip)

    file_contents = None
    with open(file_path, 'r') as f:
        file_contents = f.read()
        file_contents = file_contents.replace(WINDHAGER_HOST, new_ip, 1)

    with open(file_path, 'w') as f:
        f.write(file_contents)


def read_metrics_file(file_path: str = "/volume1/docker/python/oids_metrics.txt") -> dict:
    """
    Read the metrics which shall be read from windhager.

    Parameters
    ----------
    file_path : str, optional
        file to the metrics, by default "/volume1/docker/python/oids_metrics.txt"
        format: [metric.path];[datapoint_path];[oid]

    Returns
    -------
    dict
        the OIDS metrics
    """
    oids_metrics = dict()
    with open(file_path, "r", encoding="UTF-8") as file:
        lines = file.readlines()

        for line in lines:
            metric, _, oid = line.replace("\n", "").split(";")
            oids_metrics[oid] = metric

    return oids_metrics


def send_data_to_graphite(list_of_metric_tuples: List[tuple]) -> bool:
    """
    Send the data, which was converted to a certain format, to graphites carbon receiver.

    See Description here: https://graphite.readthedocs.io/en/latest/feeding-carbon.html#the-pickle-protocol

    Parameters
    ----------
    list_of_metric_tuples : list
        [(path, (timestamp, value)), ...], our measurement values

    Returns
    -------
    bool
        success?
    """
    payload = pickle.dumps(list_of_metric_tuples, protocol=2)
    header = struct.pack("!L", len(payload))
    message = header + payload

    sock = socket.create_connection(
        (GRAPHITE_HOST, GRAPHITE_PORT), GRAPHITE_TIMEOUT)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    success = False
    try:
        sock.sendall(message)
        success = True
    except:
        logging.error('Error sending data!\n%s', sys.exc_info())
    finally:
        sock.close()

    return success


def chunks(data: list, n):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), n):
        yield data[i:i + n]


def main() -> int:
    oids_metrics = read_metrics_file()
    graphite_data = []

    try:
        response = requests.get(f'http://{WINDHAGER_HOST}/api/1.0/datapoints', auth=HTTPDigestAuth(WINDHAGER_USER, WINDHAGER_PASSWORD), timeout=30)

    except requests.exceptions.ConnectionError:
        logging.error('Error connecting to given windhager IP! %s', sys.exc_info())
        update_windhager_ip()  # can be uncommented when using static IPs
        return 1

    except requests.exceptions.ConnectTimeout:
        logging.error('Connection timeout! %s', sys.exc_info())
        return 1

    except:
        logging.error('Unknown exception occured! %s', sys.exc_info())
        return 1

    else:
        if response.status_code != 200:
            logging.error('Error getting datapoints! Status Code: %d', response.status_code)
            return 1

    datapoints = json.loads(response.content)

    for datapoint in datapoints:
        if "value" in datapoint:
            if datapoint["OID"] in oids_metrics:

                if datapoint["unitId"] in ALLOWED_UNIT_IDS:

                    value = -99
                    try:
                        value = float(datapoint["value"])
                    except ValueError:
                        pass

                    graphite_data.append((
                        oids_metrics[datapoint["OID"]],
                        (
                            -1, float(value)
                        )
                    ))

    success = True
    for chunk in chunks(graphite_data, 10):
        success &= send_data_to_graphite(chunk)
        time.sleep(0.2)

    return success


if __name__ == "__main__":
    init_logger()
    main()
    EXIT_TIMER.cancel()
    sys.exit(0)
