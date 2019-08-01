#!/usr/bin/env python3

import sys
import argparse
from flask import Flask, request
app = Flask(__name__)
import requests
from os.path import abspath
sys.path.append(abspath('protobufs'))
import messages.messages_pb2

parser = argparse.ArgumentParser(description='Apache Mesos Agent.')
parser.add_argument('--master', type=str, help='URI of the Mesos Master', required=True)
parser.add_argument('--port', type=int, help='Port to run Mesos Agent', required=False, default=5051)
args = parser.parse_args()

def send_agent_message(data):
    #now we should send a register slave message
    headers = {'User-Agent':'libprocess/slave(1)@127.0.1.1:' + args.port,
                'Libprocess-From':'slave(1)@127.0.1.1:' + args.port}

    requests.post('http://' + args.master, data=data)

# Throw in a default handler because it feels like it should be there
@app.route("/")
def default_route_handler():
    return 'OK'

#Slave Registered Message
@app.route('/slave(<int:agent_id>)/mesos.internal.SlaveRegisteredMessage')
def slave_registered_message():
    print(request)
    return 'Accepted', 202

#Slave Ping Message
@app.route('/slave(<int:agent_id>)/mesos.internal.PingSlaveMessage')
def ping_slave_message():
    print(request)
    return 'Accepted', 202



if __name__ == '__main__':
    app.run(host='127.0.1.1', port = args.port, debug=True)
    print("Started Agent server on port", args.port)

    #build a protobuf for the register slave message
    registerSlave = messages_pb2.RegisterSlaveMessage
