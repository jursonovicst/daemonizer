from subprocess import Popen, PIPE, TimeoutExpired
import random
import select
from sys import platform
from logging import Logger


class Daemon:
    _daemons = {}
    _stdoutfds = {}
    _stderrfds = {}
    if platform == "linux" or platform == "linux2":
        _poller = select.epoll()
        POLLHUP = select.EPOLLHUP
        POLLIN = select.EPOLLIN
    elif platform == "darwin":
        _poller = select.poll()
        POLLHUP = select.POLLHUP
        POLLIN = select.POLLIN

    _stdoutlogger = None
    _stderrlogger = None

    @classmethod
    def setlogger(cls, stdoutlogger: Logger, stderrlogger: Logger):
        cls._stdoutlogger: Logger = stdoutlogger
        cls._stderrlogger: Logger = stderrlogger

    @classmethod
    def register(cls, daemon):
        cls._daemons[daemon.pid] = daemon
        cls._stdoutfds[daemon.outfd] = daemon.pid
        cls._stderrfds[daemon.errfd] = daemon.pid
        cls._poller.register(daemon.stdout, cls.POLLHUP | cls.POLLIN)
        cls._poller.register(daemon.stderr, cls.POLLHUP | cls.POLLIN)

    @classmethod
    def deregister(cls, daemon):
        cls._daemons.pop(daemon.pid)
        cls._stdoutfds.pop(daemon.outfd)
        cls._stderrfds.pop(daemon.errfd)

    @classmethod
    def terminateall(cls):
        for daemon in cls._daemons.values():
            daemon.terminate()

    @classmethod
    def info(cls, msg: str, id: str = 'global'):
        cls._stderrlogger.info(f"Daemon {id}: {msg}.")

    @classmethod
    def wait(cls):
        # subprocs = {}  # map stdout pipe's file descriptor to the Popen object

        # # spawn some processes
        # for i in xrange(5):
        #     subproc = subprocess.Popen(["mylongrunningproc"], stdout=subprocess.PIPE)
        #     subprocs[subproc.stdout.fileno()] = subproc

        # loop that polls until completion

        run = True
        while run:
            try:
                # poll only, if there is anything registered...
                if 0 < len(cls._daemons):

                    # check for read or exit
                    for fd, events in cls._poller.poll():
                        if fd in cls._stdoutfds:
                            if events & cls.POLLHUP == cls.POLLHUP:
                                # daemon crashed
                                daemon = cls._daemons[cls._stdoutfds[fd]]
                                daemon.poll()
                                cls.info(f"ended with {daemon.returncode} code (PID: {daemon.pid}), respawn", daemon.id)

                                # deregister
                                cls.deregister(daemon)

                                # recreate
                                daemon.create()
                            elif events & cls.POLLIN == cls.POLLIN:
                                # read and log
                                cls._stdoutlogger.info(cls._daemons[cls._stdoutfds[fd]].stdout.readline())

                        if fd in cls._stderrfds:
                            if events & cls.POLLHUP == cls.POLLHUP:
                                # daemon crashed
                                daemon = cls._daemons[cls._stderrfds[fd]]
                                daemon.poll()
                                cls.info(f"ended with {daemon.returncode} code (PID: {daemon.pid}), respawn", daemon.id)

                                # deregister
                                cls.deregister(cls._daemons[cls._stderrfds[fd]])

                                # recreate
                                daemon.create()
                            elif events & cls.POLLIN == cls.POLLIN:
                                # read and log
                                cls._stderrlogger.info(cls._daemons[cls._stderrfds[fd]].stderr.readline())
            except KeyboardInterrupt:
                # cls.info("terminate")
                cls.terminateall()
                run = False
        # done_proc = subprocs[fd]
        #                poller.unregister(fd)

    # @staticmethod
    # def reader(stdout: BufferedReader, stderr: BufferedReader, name):
    #     while not stdout.closed:
    #         if stdout.readable():
    #             print(f"Thread {name}: {stdout.readline()}")
    #         time.sleep(1)

    def __init__(self, executable: str, args: list, id: str = f"#{random.randint(0, 10000)}"):
        # save attributes
        self._executable = executable
        self._args = args
        self._id = id

        # no process at the beginning
        self._process: Popen = None

        # check logger
        if self._stdoutlogger is None or self._stderrlogger is None:
            raise Exception("Please set the logging facility before you create any instance!")

        # start and register process
        self.create()

    def create(self):
        # start process
        self._process = Popen([self._executable] + self._args, stdout=PIPE, stderr=PIPE, text=True)
        self.info(f"created (PID: {self._process.pid})", self.id)

        # register
        Daemon.register(self)

    def terminate(self):
        self._process.terminate()
        # wait max 5 sec
        try:
            self._process.wait(5)
        except TimeoutExpired:
            # kill it!
            self.info("timeout on terminate -- kill", self.id)
            self._process.kill()

    def poll(self):
        try:
            self._process.wait(5)
        except TimeoutExpired:
            self.info("hangs, kill it", self.id)
            self._process.kill()

    @property
    def id(self):
        return self._id

    @property
    def pid(self):
        return self._process.pid if self._process is not None else None

    @property
    def returncode(self):
        return self._process.returncode

    @property
    def outfd(self):
        return self.stdout.fileno()

    @property
    def errfd(self):
        return self.stderr.fileno()

    @property
    def stdout(self):
        return self._process.stdout

    @property
    def stderr(self):
        return self._process.stderr
