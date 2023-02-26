# example of usage grafana/loki api when you need push any log/message from your python scipt
import logging
import sys
import requests
import json
import datetime
import logging.handlers as handlers


class LokiHandler(logging.Handler):

    def __init__(self, level, loki_host) -> None:
        super().__init__(level=level)
        loki.loki_host = loki_host

    def handleError(self, record):
        super().handleError(record)

    def emit(self, record):
        try:
            loki.push(f'[{logging._levelToName[record.levelno]}] {self.format(record)}')
        except:
            self.handleError(record)


class loki:
    host = '192.168.8.42'
    loki_host = "loki_host"
    # loki_source = None
    # loki_job = None

    @classmethod
    def push(cls, txt):
        curr_datetime = datetime.datetime.now()
        curr_datetime = curr_datetime.isoformat('T') + "+01:00"

        # push msg log into grafana-loki
        url = f'http://{cls.host}:3100/api/prom/push'
        headers = {
            'Content-type': 'application/json'
        }
        # 'labels': f'{"{"}source=\"{cls.loki_source}\",job=\"{cls.loki_job}\", host=\"{cls.loki_host}\"{"}"}',
        payload = {
            'streams': [
                {
                    'labels': f'{"{"}host=\"{cls.loki_host}\"{"}"}',
                    'entries': [
                        {
                            'ts': curr_datetime,
                            'line': txt
                        }
                    ]
                }
            ]
        }
        payload = json.dumps(payload)
        try:
            requests.post(url, data=payload, headers=headers, timeout=5)
        except:
            pass

# if __name__ == "__main__":
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)
#     logHandler = handlers.RotatingFileHandler(
#         "a.log",
#         maxBytes=1e8,
#         backupCount=1
#     )
#     formatter = logging.Formatter(
#         '%(asctime)s %(funcName)s %(lineno)d %(levelname)s : %(message)s')

#     lokiHandler = LokiHandler(logging.INFO, "TEST")
#     logHandler.setFormatter(formatter)
#     logger.addHandler(lokiHandler)
#     logger.addHandler(logHandler)

#     logging.warning("test waaaaaaarn")