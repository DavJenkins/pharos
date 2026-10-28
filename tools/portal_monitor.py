#!/usr/bin/python3
"""Bounded portal discovery diagnostics, enabled only by the Ark Debug flag."""
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import selectors
import subprocess
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wifi_interfaces import interfaces

FLAG = Path('/var/lib/ark/debug_status')
PROBES = ('connectivitycheck.', 'captive.apple.com', 'msftconnecttest.com',
          'msftncsi.com', 'detectportal.firefox.com', 'dataark')
COMMAND = ['/usr/bin/tcpdump', '-i', 'wlan0', '-nn', '-tttt', '-l', '-s', '128', '-Z', 'root',
           'arp or (udp port 67 or udp port 68) or port 53 or (tcp port 80 and (tcp[tcpflags] & (tcp-syn|tcp-rst) != 0))']


def main():
    logger = logging.getLogger('portal-monitor')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('/var/log/dataark-portal-monitor/events.log',
                                  maxBytes=1048576, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    logger.info('Monitor follows Debug; four rotating 1 MiB logs; discovery DNS names only.')
    previous = None
    while True:
        enabled = FLAG.exists()
        if enabled != previous:
            logger.info('Debug %s; capture %s.', 'on' if enabled else 'off',
                        'enabled' if enabled else 'paused')
            previous = enabled
        if not enabled:
            time.sleep(0.5)
            continue
        command = COMMAND.copy()
        command[2] = interfaces()[0]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, bufsize=1) as process:
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            try:
                while FLAG.exists():
                    for key, _ in selector.select(timeout=0.5):
                        line = key.fileobj.readline()
                        if not line:
                            raise RuntimeError('Packet capture exited unexpectedly')
                        if ('.53:' in line or '.53 >' in line) and not any(host in line.lower() for host in PROBES):
                            continue
                        logger.info('%s', line.strip()[:1500])
                    if process.poll() is not None:
                        raise RuntimeError('Packet capture exited unexpectedly')
            finally:
                selector.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == '__main__':
    main()
