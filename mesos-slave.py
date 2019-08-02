#!/usr/bin/env python3

import sys
import argparse
from os.path import abspath
sys.path.append(abspath('protobufs'))

from compactor import install, spawn, Process, Context
from compactor.process import ProtobufProcess
from compactor.pid import PID
import messages.messages_pb2 as internal
import mesos.mesos_pb2 as mesos
import psutil

parser = argparse.ArgumentParser(description='Apache Mesos Agent.')
parser.add_argument('--master', type=str, help='URI of the Mesos Master', required=True)
parser.add_argument('--port', type=int, help='Port to run Mesos Agent', required=False, default=5051)
args = parser.parse_args()

class AgentProcess(ProtobufProcess):

    def __init__(self, agentID, masterPID):
        self.masterPID = masterPID
        self.registeredExecutorList = []
        self.taskList = []
        self.slave_info.id = None
        self.slave_info = mesos.SlaveInfo()
        self.slave_info.hostname = "127.0.1.1"
        self.slave_info.port = args.port
        self.slave_info.version = "1.8.1"


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
        self.slave_info.id = message.slave_id
        print()
        print("Slave registered with: ", message)
        print()

    @ProtobufProcess.install(internal.RunTaskMessage)
    def runTask(self, from_pid, message):
        # This will start the executor and run the task

        if(message.launch_executor):
            #store information about this executor for after it is registered
            executorRegistered = internal.ExecutorRegisteredMessage()
            executorRegistered.framework_id.CopyFrom(message.framework_id)
            executorRegistered.framework_info.CopyFrom(message.framework)
            executorRegistered.executor_info.CopyFrom(message.task.executor)
            executorListItem = {}
            executorListItem.registered = False
            executorListItem.exeuctor = executorRegistered
            self.registeredExecutorList.append(executorListItem)

            # really the executor should be launched with resource limits relative to its task
            # for now I'm just going to spawn it to get the messaging right though
            # TODO

        for executor in self.registeredExecutorList:
            if(message.task.executor.executor_id == executor.executor.executor_info.executor_id and executor.registered == True):
                # Now we need to forward the task on to the executor
                self.send(executor.pid, message)
                taskListItem = {}
                taskListItem.task = message
                taskListItem.state = "DISPATCHED"
                self.taskList.append(taskListItem)
        else:
            # We can probably just wait until the executor is registered
            taskListItem = {}
            taskListItem.task = message
            taskListItem.state = "WAITING"
            self.taskList.append(taskListItem)

    @ProtobufProcess.install(internal.RegisterExecutorMessage)
    def registerExecutor(self, from_pid, message):
        # Find the executor with the same framework and ID)
        success = False
        for executor in self.registeredExecutorList:
            if(executor.executor.framework_id == message.framework_id and
               executor.executor.executor_info.executor_id == message.executor_id):
                # fill out the rest of the executor message
                success = True
                executor.executor.slave_id.CopyFrom(self.slave_info.id)
                executor.executor.slave_info.CopyFrom(self.slave_info)
                executor.registered = True
                executor.pid = from_pid

                self.send(from_pid, executor.executor)
                break

        if success == True:
            for task in self.taskList:
                if(task.state == "WAITING" and
                   task.task.task.executor.executor_id == message.executor_id and
                   task.framework_id == message.framework_id):

                    self.send(from_pid, task.task)
                    task.state = "DISPATCHED"
        else:
            print("ERROR: Did not find matching executor to register. Did not spawn this executor")

    @ProtobufProcess.install(internal.StatusUpdateMessage)
    def statusUpdate(self, from_pid, message):
        # The executor tells us status updates about the tasks which we acknowledge

    @ProtobufProcess.install(internal.FrameworkToExecutorMessage)
    def frameworkToExecutor(self, from_pid, message):
        # I think we need to send these on to the executor

    @ProtobufProcess.install(internal.ExecutorToFrameworkMessage)
    def executorToFramework(self, from_pid, message):
        # I think we need to send these on to the schedule - probably need to know the PID of that

    @ProtobufProcess.install(internal.ShutdownFrameworkMessage)
    def shutdownFramework(self, from_pid, message):
        #do something to shutdown the framework...or the executor??



    def register(self):
        #now spawn a client context to send a slave registration message to the master
        print("Creating slave registration protobuf")
        resources = self.getBasicResources()
        for resource in resources:
            r = self.slave_info.resources.add()
            r.CopyFrom(resource)

        registerSlave = internal.RegisterSlaveMessage()
        registerSlave.slave.CopyFrom(self.slave_info)
        registerSlave.version = self.slave_info.version

        self.send(self.masterPID, registerSlave)

    def reregister(self):
        resources = self.getBasicResources()
        for resource in resources:
            r = self.slave_info.resources.add()
            r.CopyFrom(resource)

        registerSlave = internal.RegisterSlaveMessage()
        registerSlave.slave.CopyFrom(self.slave_info)
        registerSlave.version = self.slave_info.version

        self.send(self.masterPID, registerSlave)

    def getBasicResources(self):
        resources = []
        resource = mesos.Resource()

        resource.name = "cpus"
        resource.type = mesos.Value.Type.SCALAR
        resource.scalar.value = psutil.cpu_count()
        resources.append(resource)

        resource = mesos.Resource()
        resource.name = "mem"
        resource.type = mesos.Value.Type.SCALAR
        resource.scalar.value = (psutil.virtual_memory().available)/1000000
        resources.append(resource)

        resource = mesos.Resource()
        resource.name = "disk"
        resource.type = mesos.Value.Type.SCALAR
        resource.scalar.value = (psutil.disk_usage('/').free)/1000000
        resources.append(resource)

        return resources


if __name__ == '__main__':

    print("Starting agent context")
    agentContext = Context(ip="127.0.1.1", port=args.port)
    agentContext.start()

    masterPID = PID.from_string('master@' + args.master)
    agentProcess = AgentProcess('slave(1)', masterPID)

    print("Spawning agent process")
    agentPID = agentContext.spawn(agentProcess)


    print("Sending slave registration message")
    agentProcess.register()

    agentContext.join()
