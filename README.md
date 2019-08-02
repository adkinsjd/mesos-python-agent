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
