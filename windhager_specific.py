import json
import logging
import socket
import sys
import traceback
from typing import Any

import requests
from requests.auth import HTTPDigestAuth

from windhager import (GRAPHITE_HOST, GRAPHITE_TIMEOUT,
                       WINDHAGER_HOST, WINDHAGER_PASSWORD, WINDHAGER_USER,
                       init_logger, read_metrics_file)


def send_data_to_graphite_simple(metric_path: str, metric_value: Any, timestamp: int = -1):

    message = f'{metric_path} {metric_value} {timestamp}\n'

    sock = socket.create_connection((GRAPHITE_HOST, 2003), GRAPHITE_TIMEOUT)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    success = False
    try:
        sock.sendall(message.encode('UTF-8'))
        success = True
    except:
        print('Error sending data!\n%s', traceback.format_exc())
    finally:
        sock.close()

    return success


def main() -> int:
    oids_metrics = read_metrics_file()

    for oid, metric in oids_metrics.items():
        value = -99.0
        if oid == 'unbekannt' or 'unbekannt' in metric:
            continue
        try:
            logging.info('Request: %s', metric)
            response = requests.get(f'http://{WINDHAGER_HOST}/api/1.0/datapoint{oid}', auth=HTTPDigestAuth(WINDHAGER_USER, WINDHAGER_PASSWORD), timeout=5)

            datapoint = json.loads(response.content)
            if 'value' in datapoint:
                try:
                    value = float(datapoint['value'])
                except ValueError:
                    pass

                send_data_to_graphite_simple(metric, value)

        except:
            logging.error('Request failed!')
            print(traceback.format_exc())

        else:
            if response.status_code != 200:
                logging.error('Error getting datapoints! Status Code: %d', response.status_code)
            else:
                logging.info('Success! Code %d, Value: %f', response.status_code, value)


if __name__ == "__main__":
    init_logger()
    main()
    sys.exit(0)
