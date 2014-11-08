#!/usr/bin/env python3

"""
A tiny daemon that monitors a network connection and triggers a user-defined
command once network connectivity has been lost and once it has later been
re-established.

Configuration is done through the following environment variables:

TARGET:
    The IPv4 address of the target to ping for connectivity checks.
INTERVAL:
    Interval (in seconds) between pings.
HEALTHY_AFTER:
    Number of times ping needs to succeed before connection is considered
    healthy again.
ON_DOWN:
    Command to run when connection goes down.
ON_UP:
    Command to run when connection comes back up.
LOGLEVEL:
    Loglevel to log at (CRITICAL, WARNING, INFO, DEBUG).
"""

import logging
import os
from subprocess import call, DEVNULL
from time import sleep


class Monitor(object):
    """
    The Monitor is responsible for pinging a given
    host in order to determine it's state and trigger
    actions when the state changes.
    """

    def __init__(self, target, interval, healthy_after):
        """
        :param target:
            The address of the target to monitor.
        :param interval:
            The interval between checks.
        :param healthy_after:
            The amount of checks that should pass after marking a connection
            as bad before it will be considered healthy again.
        """
        self.logger = logging.getLogger(__class__.__name__)

        self.healthy = True
        self.target = target
        self.interval = interval
        self.healthy_after = healthy_after
        self.successful_checks_since_down = 0

    def start(self, block=True):
        """
        Start monitoring.
        """
        if not block:
            raise NotImplementedError("Non-blocking mode is not implemented")

        self.logger.info("Monitor starting")
        self._monitor()

    def stop(self):
        """
        Stop monitoring.
        """
        raise NotImplementedError("Stopping the Monitor is not implemented")

    def _monitor(self):
        """
        This is the loop which does the actual monitoring and triggering
        of associated actions.
        """
        while True:
            self.logger.debug("Pinging {}".format(self.target))
            alive = self._is_alive(self.target)
            if alive:
                self.logger.debug("{} responded to pings".format(self.target))
            else:
                self.logger.debug("{} unresponsive to pings".format(self.target))

            if self.healthy and not alive:
                logging.info("Connection is unhealthy")
                self._shellexec(os.environ["ON_DOWN"])
                self.healthy = False
                self.successful_checks_since_down = 0
            elif not self.healthy and alive:
                self.logger.debug("Successful ping while connection is unhealthy")
                self.successful_checks_since_down += 1
                if self.successful_checks_since_down >= self.healthy_after:
                    self.logger.info("Connection is now healthy")
                    self.healthy = True
                    self._shellexec(os.environ["ON_UP"])
            elif not self.healthy and not alive:
                self.logger.debug("Unsuccessful ping while connection is unhealthy")
                self.successful_checks_since_down = 0
            else:
                self.logger.debug("Successful ping while connection is healthy")
            sleep(self.interval)

    def _is_alive(self, host):
        """Determine if a given host is alive or not."""
        returncode = call(
            ["ping", "-c", "3", "-i", "0.333", host],
            timeout=30,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
        if returncode == 0:
            return True
        else:
            return False

    def _shellexec(self, command):
        """Execute a command in a shell"""
        self.logger.info("Executing: {}".format(command))
        returncode = call(command, shell=True)
        if returncode != 0:
            self.logger.warning("Command exited with status {}".format(returncode))
        return returncode


def main():
    loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, loglevel))

    m = Monitor(
            target=os.environ["TARGET"],
            interval=float(os.environ.get("INTERVAL", 10)),
            healthy_after=float(os.environ.get("HEALTHY_AFTER", 12))
    )
    m.start()


if __name__ == "__main__":
    main()
