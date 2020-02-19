# Mesos Python Agent

This is a python implementation of a very basic Apache Mesos agent. 
It's mainly practice to better understand the minimal API that could 
be implemented for an embedded C mesos-mini agent meant to run on ultra resource
constrained platforms. 

It currently is able to handle the executor lifecyle (spawn an executor, forward tasks,
manage task state, kill the executor), but it doesn't actually limit the resources
of the executor or tasks.

Down the road this could transition to a more complete example of a mini agent,
which will probably use COAP instead of HTTP (requiring an HTTP-COAP proxy) and
will need to back off ping timings and such for energy savings (still unclear how to accomplish this). 

Then we will need a new default executor that can execute and communicate with
code on embedded nodes.

Mocking this all up in python as opposed to diving in on embedded C would significantly
speed up architecture exploration. Once something is working then it can be implemented
in embedded C.

## Getting Started

1. Install protobuf 3.11

If you are running on a newer system then:
> sudo apt-get install protobuf-compiler  
> pip3 install protobuf

Otherwise download a binary from https://github.com/protocolbuffers/protobuf/releases

2. Install a modified version of compactor

> git clone https://github.com/adkinsjd/compactor.git  
> cd compactor  
> sudo python3 setup.py install  
> cd ..

3. Clone this repository

> git clone --recursive https://github.com/adkinsjd/mesos-python-agent.git  
> cd mesos-python-agent

4. Make the protobufs modules

> make all

5. Setup external IP (optional)

If you have a public IP address, but you cannot bind to, let the receiver
of your messages know where to respond (currently libprocess does not work through a NAT)

> export LIBPROCESS_ADVERTISE_IP=<your_public_IP>  
> export LIBPROCESS_ADVERTISE_PORT=<your_public_port>

5. Run the Mesos slave (substitute the command with Mesos Master IP, Mesos Master port, and Local Slave port)

> ./mesos-slave.py --master=<mesos_master_ip>:<mesos_master_port> --port=<local_port_to_bind>

## Todo

- Copy (or script to pull) Mesos Protobuf files to prevent having to clone entire repo
