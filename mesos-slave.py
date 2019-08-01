#!/usr/bin/env python3

import sys
import argparse
from os.path import abspath
sys.path.append(abspath('protobufs'))

from compactor import install, spawn, Process, Context
from compactor.process import ProtobufProcess
from compactor.pid import PID
import messages.messages_pb2 as internal
import mesos.mesos_pb2

parser = argparse.ArgumentParser(description='Apache Mesos Agent.')
parser.add_argument('--master', type=str, help='URI of the Mesos Master', required=True)
parser.add_argument('--port', type=int, help='Port to run Mesos Agent', required=False, default=5051)
args = parser.parse_args()

class AgentProcess(ProtobufProcess):
    @ProtobufProcess.install(internal.PingSlaveMessage)
    def ping(self, from_pid, message):
        print()
        print('Ping')
        pong = internal.PongSlaveMessage()
        print('Pong')
        print()
        self.send(from_pid, pong)

    @ProtobufProcess.install(internal.SlaveRegisteredMessage)
    def slaveRegistered(self, from_pid, message):
        print()
        print("Slave registered with: ", message)
        print()

if __name__ == '__main__':

    print("Starting agent context")
    agentContext = Context(ip="127.0.1.1", port=args.port)
    agentContext.start()

    agentProcess = AgentProcess('slave(1)')

    print("Spawning agent process")
    agentPID = agentContext.spawn(agentProcess)

    #now spawn a client context to send a slave registration message to the master
    print("Creating slave registration protobuf")
    registerSlave = internal.RegisterSlaveMessage()
    #add optional slave resources
    #add optional slave attributes
    #add optional slaveID
    registerSlave.slave.hostname = "127.0.1.1"
    registerSlave.slave.port = args.port
    registerSlave.version = "1.8.0"

    print("Sending slave registration message")
    masterPID = PID.from_string('master@' + args.master)
    agentProcess.send(masterPID, registerSlave)

    agentContext.join()

