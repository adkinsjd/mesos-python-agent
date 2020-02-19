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

1. Clone this repository

> git clone --recursive https://github.com/adkinsjd/mesos-python-agent.git  
> cd mesos-python-agent

2. Install protobuf

> sudo apt-get install protobuf-compiler

3. Install a modified version of compactor

> git clone https://github.com/adkinsjd/compactor.git
> python3 setup.py install

4. Make the protobufs modules

> make all

5. Setup external IP (optional)

If you have a public IP address, but you cannot bind to, let the receiver
of your messages know where to respond (currently libprocess does not work through a NAT)

> export LIBPORCESS_ADVERTIS_IP=<your_public_IP>
> export LIBPORCESS_ADVERTIS_PORT=<your_public_port>

5. Run the Mesos slave (MPORT is Mesos Master port, LPORT is Local Slave port)

> ./mesos-slave.py --master=IP.OF.MS.TR:MPORT --port=LPORT

## Todo

- Copy (or script to pull) Mesos Protobuf files to prevent having to clone entire repo
- Modify Compactor to allow for devices behind NAT (i.e. differing local + public IPs)
