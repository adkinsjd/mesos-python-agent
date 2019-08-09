#!/usr/bin/env python3

import sys
import argparse
from os.path import abspath
sys.path.append(abspath('./protobufs'))
import os

from compactor import install, spawn, Process, Context
from compactor.process import ProtobufProcess
from compactor.pid import PID
import messages.messages_pb2 as internal
import mesos.mesos_pb2 as mesos
import psutil
import subprocess
import uuid
import socket
hostname = socket.gethostname()

parser = argparse.ArgumentParser(description='Apache Mesos default executor.')
args = parser.parse_args()

class ExecutorProcess(ProtobufProcess):
    def __init__(self):
        #get the executor ID and slave PID from environment variables
        if(os.environ.get("MESOS_EXECUTOR_ID") is None):
            print("MESOS_EXECUTOR_ID must be defined")
            sys.exit(1)
        else:
            self.executorID = os.environ.get("MESOS_EXECUTOR_ID")

        if(os.environ.get("MESOS_FRAMEWORK_ID") is None):
            print("MESOS_FRAMEWORK_ID must be defined")
            sys.exit(1)
        else:
            self.frameworkID = os.environ.get("MESOS_FRAMEWORK_ID")

        if(os.environ.get("MESOS_SLAVE_PID") is None):
            print("MESOS_SLAVE_PID must be defined")
            sys.exit(1)
        else:
            self.slavePID = os.environ.get("MESOS_SLAVE_PID")

        if(os.environ.get("MESOS_SLAVE_ID") is None):
            print("MESOS_SLAVE_ID must be defined")
            sys.exit(1)
        else:
            self.slaveID = os.environ.get("MESOS_SLAVE_ID")

        super(ExecutorProcess, self).__init__(executorID)

    @ProtobufProcess.install(internal.RunTaskMessage)
    def runTask(self, from_pid, message):
        pass

    @ProtobufProcess.install(internal.ExecutorRegisteredMessage)
    def executorRegistered(self, from_pid, message):
        pass

    def register(self):
        pass

if __name__ == '__main__':
    print("Starting executor context")
    executorContext = Context(ip="127.0.1.1")
    executorContext.start()

    executorProcess = ExecutorProcess()

    print("Spawning executor process")
    executorPID = Context.spawn(executorProcess)


    print("Sending executor registration message")
    executorProcess.register()

    executorContext.join()
