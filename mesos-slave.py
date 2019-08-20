#!/usr/bin/env python3

import sys
import argparse
from os.path import abspath
sys.path.append(abspath('protobufs'))
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

parser = argparse.ArgumentParser(description='Apache Mesos Agent.')
parser.add_argument('--master', type=str, help='URI of the Mesos Master', required=True)
parser.add_argument('--port', type=int, help='Port to run Mesos Agent', required=False, default=5051)
args = parser.parse_args()

class AgentProcess(ProtobufProcess):

    def __init__(self, agentID, masterPID):
        self.masterPID = masterPID
        self.registeredExecutorList = []
        self.taskList = []
        self.slave_info = mesos.SlaveInfo()
        self.slave_info.hostname = hostname
        self.slave_info.port = args.port

        super(AgentProcess, self).__init__(agentID)



    @ProtobufProcess.install(internal.PingSlaveMessage)
    def ping(self, from_pid, message):
        print()
        print('Ping')
        pong = internal.PongSlaveMessage()
        print('Pong')
        print()
        self.send(from_pid, pong)
        self.connected = message.connected

        if(message.connected == False):
            print("Slave marked as disconnected")
            print("Attempting reregistration")


    @ProtobufProcess.install(internal.SlaveRegisteredMessage)
    def slaveRegistered(self, from_pid, message):
        #save the slave UUID
        self.slave_info.id.CopyFrom(message.slave_id)
        print()
        print("Slave registered with: ", message)
        print()

    @ProtobufProcess.install(internal.RunTaskMessage)
    def runTask(self, from_pid, message):
        # This will start the executor and run the task
        print("Got task to run: ", message.task.task_id.value)

        if(message.launch_executor):
            if(message.task.executor.IsInitialized()):
                print("Task wants to launch executor: ", message.task.executor)
            else:
                print("Task wants to launch executor: ", message.task.command)

            print("Adding unregistered executor to known executor list")
            #store information about this executor for after it is registered
            executorRegistered = internal.ExecutorRegisteredMessage()

            executorRegistered.framework_id.CopyFrom(message.framework.id)
            executorRegistered.framework_info.CopyFrom(message.framework)

            if(message.task.executor.IsInitialized()):
                executorRegistered.executor_info.CopyFrom(message.task.executor)
            else:
                executorRegistered.executor_info.executor_id.value = message.task.task_id.value
                executorRegistered.executor_info.type = mesos.ExecutorInfo.Type.DEFAULT

            executorListItem = {}
            executorListItem['registered'] = False
            executorListItem['executor'] = executorRegistered

            # really the executor should be launched with resource limits relative to its task
            # for now I'm just going to spawn it to get the messaging right though

            print("setting environment variables for executor")
            os.environ["MESOS_SLAVE_PID"] = str(self.pid)
            os.environ["MESOS_SLAVE_ID"] = str(self.slave_info.id.value)
            os.environ["MESOS_FRAMEWORK_ID"] = str(message.framework.id.value)
            os.environ["MESOS_DIRECTORY"] = "./"

            if(message.task.executor.IsInitialized()):
                print("Task specifies executor")
                os.environ["MESOS_EXECUTOR_ID"] = str(message.task.executor.executor_id.value)

                if(message.task.executor.command.environment.IsInitialized()):
                    for variable in message.task.executor.command.environment.variables:
                        print("Setting environment variable", variable.name, "to", variable.value)
                        os.environ[variable.name] = variable.value

                print("Spawning executor with command: ", message.task.executor.command)
                pid = subprocess.Popen([message.task.executor.command.value],preexec_fn=os.setsid)
                executorListItem['processPID'] = pid

            elif(message.task.command.IsInitialized()):
                print("No executor specified. Using default executor. Setting executor_id to task id")
                os.environ["MESOS_EXECUTOR_ID"] = str(message.task.task_id.value)

                #if MESOS_DEFAULT_EXECUTOR is not an empty string use it
                pid = None
                if(os.environ.get('MESOS_EXECUTOR') is None):
                    print("Executor not set. Assuming mesos-executor in path")
                    pid = subprocess.Popen(['mesos-executor'], preexec_fn=os.setsid)
                else:
                    print("Using MESOS_EXECUTOR:", os.environ['MESOS_EXECUTOR'])
                    pid = subprocess.Popen([os.environ.get('MESOS_EXECUTOR')], preexec_fn=os.setsid)

                executorListItem['processPID'] = pid

            else:
                print("ERROR: Asked to launch executor, but no executor to launch")

            self.registeredExecutorList.append(executorListItem)

        for executor in self.registeredExecutorList:
            if(message.task.executor.executor_id == executor['executor'].executor_info.executor_id and executor['registered'] == True):
                # Now we need to forward the task on to the executor
                print("Executor registered for this task. Forwarding task to executor: ",
                        message.task.executor.executor_id,
                        " with pid ", executor['pid'])

                self.send(executor.pid, message)
                taskListItem = {}
                taskListItem['task'] = message
                taskListItem['state'] = "DISPATCHED"
                self.taskList.append(taskListItem)
        else:
            # We can probably just wait until the executor is registered
            print("Executor not registered for this task. Will forward task after registration")

            taskListItem = {}
            taskListItem['task'] = message
            taskListItem['state'] = "WAITING"
            self.taskList.append(taskListItem)

        print()

    @ProtobufProcess.install(internal.RegisterExecutorMessage)
    def registerExecutor(self, from_pid, message):
        # Find the executor with the same framework and ID)
        print(message)
        print("Request to register executor ", message.executor_id.value, " on framework ", message.framework_id.value)

        success = False
        for executor in self.registeredExecutorList:
            if(executor['executor'].framework_id.value == message.framework_id.value and
               executor['executor'].executor_info.executor_id.value == message.executor_id.value):
                # fill out the rest of the executor message
                success = True
                executor['executor'].slave_id.CopyFrom(self.slave_info.id)
                executor['executor'].slave_info.CopyFrom(self.slave_info)
                executor['registered'] = True
                executor['pid'] = from_pid

                self.send(from_pid, executor['executor'])
                break

        if success == True:
            for task in self.taskList:
                if(task['state'] == "WAITING" and
                   (task['task'].task.executor.executor_id.value == message.executor_id.value or
                    (not task['task'].task.executor.IsInitialized() and task['task'].task.task_id.value == message.executor_id.value))
                       and
                   task['task'].framework.id.value == message.framework_id.value):

                    print("Forwarding task ", task['task'].task.task_id.value, " to executor ", message.executor_id.value)

                    self.send(from_pid, task['task'])
                    task['state'] = "DISPATCHED"
                elif(task['state'] == 'WAITING'):
                    print("Task: ", task['task'].task.task_id.value, "still waiting to be dispatched")
        else:
            print("ERROR: Did not find matching executor to register. Did not spawn this executor")
        print()

    @ProtobufProcess.install(internal.StatusUpdateMessage)
    def statusUpdate(self, from_pid, message):
        # The executor tells us status updates about the tasks which we acknowledge

        # We also forward the status updates to the master

        print("Received status update for task ", message.update.status.task_id.value, "with state", message.update.status.state)
        ack = internal.StatusUpdateAcknowledgementMessage()
        ack.slave_id.CopyFrom(message.update.slave_id)
        ack.framework_id.CopyFrom(message.update.framework_id)
        ack.task_id.CopyFrom(message.update.status.task_id)
        ack.uuid = message.update.uuid

        #find the task in our task list
        for task in self.taskList:
            if(task['task'].task.executor.executor_id.value == message.update.executor_id.value and
               task['task'].framework.id.value == message.update.framework_id.value and
               task['task'].task.task_id.value == message.update.status.task_id.value):

                print("Found matching task. Updating state")
                task['state'] = str(message.update.status.state)

                #if it was in our task list send to maasterack the state update
                print("Forwarding status update to master")
                statusUpdate = internal.StatusUpdateMessage()
                statusUpdate.CopyFrom(message)
                statusUpdate.pid = str(self.pid)
                self.send(self.masterPID, statusUpdate)

                print("Acknowledging status update")
                self.send(from_pid, ack)

        print()

    @ProtobufProcess.install(internal.StatusUpdateAcknowledgementMessage)
    def statusUpdateAcknowledgement(self, from_pid, message):
        # We can probably just drop these for now. Eventually it will have to be implemented
        print("Received status update acknowledgment from", from_pid)
        print()


    @ProtobufProcess.install(internal.FrameworkToExecutorMessage)
    def frameworkToExecutor(self, from_pid, message):
        #Forward framework to executor messages on to the executor
        print("Received framework to executor message for executor ",
                message.executor_id.value, "framework", message.framework_id.value)

        for executor in self.registeredExecutorList:
            if(executor['executor'].framework_id.value == message.framework_id.value and
               executor['executor'].executor_info.executor_id.value == message.executor_id.value):
                # fill out the rest of the executor message

                print("Forwarding message to executor pid", executor['pid'])
                self.send(executor['pid'], message)

        print()

    @ProtobufProcess.install(internal.ExecutorToFrameworkMessage)
    def executorToFramework(self, from_pid, message):
        # I think we need to send these on to the scheduler - probably need to know the PID of that
        print("Received executor to framework message for executor ",
                message.executor_id.value, "framework", message.framework_id.value)

        print("Forwarding message to master")
        self.send(self.masterPID, message)
        print()

    @ProtobufProcess.install(internal.ShutdownFrameworkMessage)
    def shutdownFramework(self, from_pid, message):
        #send a shutdown executor message to the executor
        print("Received shutdown framework message for framework", message.framework_id.value)
        shutdownExecutor = internal.ShutdownExecutorMessage()
        shutdownExecutor.framework_id.CopyFrom(message.framework_id)

        print("Sending shutdown to executors in framework")
        for executor in self.registeredExecutorList:
            if(executor['executor'].framework_id.value == message.framework_id.value):
                shutdownExecutor.executor_id.CopyFrom(executor['executor'].executor_info.executor_id)
                print("Shutting down executor with PID",executor['pid'])
                pid = executor['pid']
                print(shutdownExecutor)
                self.send(pid, shutdownExecutor)

                #remove executor from registered list
                print("Removing executor from registered list")
                self.registeredExecutorList.remove(executor)

                #kill the executor subprocess
                executor['processPID'].kill()

        print()

    def register(self):
        #now spawn a client context to send a slave registration message to the master
        print("Creating slave registration protobuf")
        resources = self.getBasicResources()
        for resource in resources:
            r = self.slave_info.resources.add()
            r.CopyFrom(resource)

        registerSlave = internal.RegisterSlaveMessage()
        registerSlave.slave.CopyFrom(self.slave_info)
        registerSlave.version = "1.8.1"
        registerSlave.resource_version_uuid.value = uuid.uuid1().bytes

        print("Sending slave registration to master")
        self.send(self.masterPID, registerSlave)
        print()

    def reregister(self):
        resources = self.getBasicResources()
        for resource in resources:
            r = self.slave_info.resources.add()
            r.CopyFrom(resource)

        registerSlave = internal.RegisterSlaveMessage()
        registerSlave.slave.CopyFrom(self.slave_info)
        registerSlave.version = "1.8.1"
        registerSlave.resource_version_uuid.value = uuid.uuid1().bytes

        self.send(self.masterPID, registerSlave)

    def getBasicResources(self):
        resources = []
        resource = mesos.Resource()

        resource.name = "cpus"
        resource.type = mesos.Value.SCALAR
        resource.scalar.value = psutil.cpu_count()
        resources.append(resource)

        resource = mesos.Resource()
        resource.name = "mem"
        resource.type = mesos.Value.SCALAR
        resource.scalar.value = (psutil.virtual_memory().available)/1000000
        resources.append(resource)

        resource = mesos.Resource()
        resource.name = "disk"
        resource.type = mesos.Value.SCALAR
        resource.scalar.value = (psutil.disk_usage('/').free)/1000000
        resources.append(resource)

        return resources


if __name__ == '__main__':

    print("Starting agent context")
    agentContext = Context(ip="127.0.0.1", port=args.port)
    agentContext.start()

    masterPID = PID.from_string('master@' + args.master)
    agentProcess = AgentProcess('slave(1)', masterPID)

    print("Spawning agent process")
    agentPID = agentContext.spawn(agentProcess)


    print("Sending slave registration message")
    agentProcess.register()

    agentContext.join()
