# Remofile - Quick and easy-to-use alternative to FTP
#
# This file is distributed under the MIT License. See the LICENSE file
# in the root of this project for more information.
#
# Written by Jonathan De Wachter <dewachter.jonathan@gmail.com>, April 2018

""" Generic linux daemon base class for python 3.x. """

import sys
import os
import time
import atexit
import signal

class Daemon:
    def __init__(self, loop, pidfile):
        self.loop = loop
        self.pidfile = pidfile

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""

        # do first fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:

                # exit from second parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # redirect standard file descriptors
        #sys.stdout.flush()
        #sys.stderr.flush()
        si = open(os.devnull, 'r')
        #so = open(os.devnull, 'a+')
        #se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        #os.dup2(so.fileno(), sys.stdout.fileno())
        #os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        #self.loop.delpid = self.delpid
        #atexit.register(self.loop.delpid)

        pid = str(os.getpid())
        with open(self.pidfile,'w+') as f:
            f.write(pid + '\n')

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile,'r') as pf:

                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            message = "pidfile {0} already exist. " + \
                    "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.loop()

    @staticmethod
    def stop(pidfile):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            message = "pidfile {0} does not exist. " + "Daemon not running?\n"
            sys.stderr.write(message.format(pidfile))
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0 and os.path.exists(pidfile):
                os.remove(pidfile)
            else:
                print(str(err.args))
                sys.exit(1)

    #def restart(self):
        #"""Restart the daemon."""
        #self.stop()
        #self.start()

