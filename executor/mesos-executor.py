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
import time
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
            self.slavePID = PID.from_string(os.environ.get("MESOS_SLAVE_PID"))

        if(os.environ.get("MESOS_SLAVE_ID") is None):
            print("MESOS_SLAVE_ID must be defined")
            sys.exit(1)
        else:
            self.slaveID = os.environ.get("MESOS_SLAVE_ID")

        self.registered = False

        super(ExecutorProcess, self).__init__(self.executorID)

    @ProtobufProcess.install(internal.RunTaskMessage)
    def runTask(self, from_pid, message):

        print("Received run task message from framework", message.framework_id.value)

        # If I'm getting this it must be a command task. Check if that is true
        if(not message.task.command.IsInitialized()):
            print("Default executor only made to run command tasks!")
            print("Ignoring non command task")
            return

        #Now set up any environment variables for the command task
        if(message.task.command.environment.IsInitialized()):
            for var in message.task.command.environment.variables:
                os.environ[var.name] = var.value

        #construct task status update message
        update = internal.StatusUpdateMessage()
        update.pid = str(self.pid)
        update.update.framework_id.value = self.frameworkID
        update.update.executor_id.value = self.executorID
        update.update.slave_id.value = self.slaveID
        update.update.status.task_id.value = message.task.task_id.value
        update.update.status.state = mesos.TaskState.TASK_STARTING
        update.update.status.slave_id.value = self.slaveID
        time_now = time.time()
        update.update.status.timestamp = time_now
        update.update.status.executor_id.value = self.executorID
        update.update.status.source = mesos.TaskStatus.Source.SOURCE_EXECUTOR
        new_uuid = uuid.uuid1().bytes
        update.update.status.uuid = new_uuid
        update.update.uuid = new_uuid
        update.update.timestamp = time_now

        self.send(from_pid, update)

        #Now run the command specified in the task
        clist = message.task.command.value.strip().replace('"','').split(' ')
        print("Executing task command:", clist)
        pid = subprocess.Popen(clist)

        update.update.status.state = mesos.TaskState.TASK_RUNNING
        self.send(from_pid, update)

    @ProtobufProcess.install(internal.StatusUpdateAcknowledgementMessage)
    def statusUpdateAcknowledgement(self, from_pid, message):
        # for now just log these. Really there is probably some reliability process here
        print("Received status update acknowledgment from", from_pid)


    @ProtobufProcess.install(internal.ExecutorRegisteredMessage)
    def executorRegistered(self, from_pid, message):
        #catch the executor registered message
        print("Registration successful")
        self.registered = True

    def register(self):
        #build a registerExecutor message
        print("Registering executor with slave")
        registerExecutor = internal.RegisterExecutorMessage()
        registerExecutor.framework_id.value = self.frameworkID
        registerExecutor.executor_id.value = self.executorID

        #send register executor to slave
        self.send(self.slavePID, registerExecutor)

if __name__ == '__main__':
    print("Starting executor context")
    executorContext = Context(ip="127.0.1.1")
    executorContext.start()

    executorProcess = ExecutorProcess()

    print("Spawning executor process")
    executorPID = executorContext.spawn(executorProcess)


    print("Sending executor registration message")
    executorProcess.register()

    executorContext.join()
