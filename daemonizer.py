#!/usr/bin/env python3.6

import argparse
from daemonizer import Daemon
import logging

parser = argparse.ArgumentParser(description='Daemonize processes.')
parser.add_argument('executable', help='executable to run')
parser.add_argument('arguments', nargs='*', help='arguments to pass to the executable')
parser.add_argument('--num', type=int, default=1, help='number of executables to keep running (default: %default)')
parser.add_argument('--outlog', type=argparse.FileType('w', encoding='UTF-8'), default='-',
                    help='stdout logging destination')
parser.add_argument('--errlog', type=argparse.FileType('w', encoding='UTF-8'), default='-',
                    help='stderr logging destination')

if __name__ == "__main__":

    try:
        args = parser.parse_args()

        errlogger = logging.getLogger('errlogger')
        errlogger.setLevel(logging.INFO)
        ch2 = logging.StreamHandler()
        ch2.setLevel(logging.INFO)
        errlogger.addHandler(ch2)

        outlogger = logging.getLogger('outlogger')
        outlogger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.terminator = ""
        ch.setLevel(logging.INFO)
        outlogger.addHandler(ch)

        Daemon.setlogger(outlogger, errlogger)

        # start processes
        for i in range(0, args.num):
            Daemon(args.executable, args.arguments, f"#{i}")

        # this will block until interrupt
        Daemon.wait()

    except Exception as e:
        print(f"Error: {e}, exiting!")
