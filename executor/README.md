Default Executor
================

Mesos has a notion of a default executor which performs baseline mesos 
operations (like registering the executor, shutting down the executor,
passing messages).

This is a python implementation of the default executor.

It will be primarily geared toward supporting the spark executor at 
first and might not be fully featured (spark seems to use the command executor).
