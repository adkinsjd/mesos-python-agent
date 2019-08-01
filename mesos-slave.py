#!/usr/bin/env python3

import sys
import argparse
from flask import Flask, request
app = Flask(__name__)
import requests
from os.path import abspath
sys.path.append(abspath('protobufs'))
import messages.messages_pb2
import mesos.mesos_pb2
from threading import Thread
from werkzeug.serving import WSGIRequestHandler

parser = argparse.ArgumentParser(description='Apache Mesos Agent.')
parser.add_argument('--master', type=str, help='URI of the Mesos Master', required=True)
parser.add_argument('--port', type=int, help='Port to run Mesos Agent', required=False, default=5051)
args = parser.parse_args()

#start a global requests session
s = requests.Session()

def send_to_master(protobuf):
    #now we should send a register slave message
    print("Sending: ", protobuf)
    print("To: " + '/master/mesos.internal.' + protobuf.DESCRIPTOR.full_name.split('.')[-1])

    headers = {'User-Agent':'libprocess/slave(1)@127.0.1.1:' + str(args.port),
                'Libprocess-From':'slave(1)@127.0.1.1:' + str(args.port)}

    s.post('http://' + args.master + '/master/mesos.internal.' + protobuf.DESCRIPTOR.full_name.split('.')[-1],
                    data=protobuf.SerializeToString(), headers=headers, stream=True)

def respond_to_ping(request):
    agent = request.headers['Libprocess-From'].split('@')[0]
    host  = request.headers['Libprocess-From'].split('@')[1]

    headers = {'User-Agent':'libprocess/slave(1)@127.0.1.1:' + str(args.port),
                'Libprocess-From':'slave(1)@127.0.1.1:' + str(args.port)}

    pongSlaveMesssage = messages.messages_pb2.PongSlaveMessage()

    print('Responding to ping')

    s.post('http://' + host + '/' + agent + '/mesos.internal.' +  pongSlaveMessage.DESCRIPTOR.full_name.split('.')[-1],
                    data=pongSlaveMessage.SerializeToString(), headers=headers, stream=True)


# Throw in a default handler because it feels like it should be there
@app.route("/")
def default_route_handler():
    return 'OK'

#Slave Registered Message
@app.route('/slave(<int:agent_id>)/mesos.internal.SlaveRegisteredMessage', methods=['POST'])
def slave_registered_message(agent_id):
    #print(request)
    return 'Accepted', 202

#Slave Ping Message
@app.route('/slave(<int:agent_id>)/mesos.internal.PingSlaveMessage', methods=['POST'])
def ping_slave_message(agent_id):
    #respond_to_ping(request)
    return 'Accepted', 202

def runFlaskServer():
    print("Starting Agent server on port", args.port)
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='127.0.1.1', port = args.port, debug=True, use_reloader=False)

if __name__ == '__main__':

    #spawn the server thread
    serverThread = Thread(target=runFlaskServer)
    serverThread.start()

    #build a protobuf for the register slave message
    print("Creating slave registration protobuf")
    registerSlave = messages.messages_pb2.RegisterSlaveMessage()

    #slaveInfo = mesos.mesos_pb2.SlaveInfo()
    #slaveInfo.hostname = "127.0.1.1"
    #slaveInfo.port = args.port
    #add optional slave resources
    #add optional slave attributes
    #add optional slaveID

    registerSlave.slave.hostname = "127.0.1.1"
    registerSlave.slave.port = args.port
    registerSlave.version = "1.8.0"
    #add slaveinfo capabilities

    send_to_master(registerSlave)

    #From here everything should just operate out of our asynchronous thread
    serverThread.join()
