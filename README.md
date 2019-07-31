# Mesos Python Agent

This is a python implementation of a subset of the internal API for an apache
mesos agent. It's mainly practice to better understand the minimal API that could 
be implemented for an embedded C mesos-mini agent meant to run on ultra resource
constrained platforms. 

The plan is roughly to start with agent registration and pinging, then add
state and metrics calls (so that it can be viewed in the UI) then add the
most basic executor functionality (execute a shell command with message passing). 

Down the road this could transition to a more complete example of a mini agent,
which will probably use COAP instead of HTTP (requiring an HTTP-COAP proxy) and
will need to back off ping timings and such for energy savings (still unclear how to accomplish this). 

Then we will need a new default executor that can execute and communicate with
code on embedded nodes.

Mocking this all up in python as opposed to diving in on embedded C would significantly
speed up architecture exploration. Once something is working then it can be implemented
in embedded C.
