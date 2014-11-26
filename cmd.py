from fabric.api import *

def retrieve(filename):
    get(filename, "target/{}-{}".format(filename, env.host_string))

@task
def pprof():
    """
    Retrieve profiling data from NSQ nodes.
    """
    run("curl http://localhost:4151/debug/pprof/profile -o profile")
    run("curl http://localhost:4151/debug/pprof/goroutine -o goroutine")
    run("curl http://localhost:4151/debug/pprof/heap -o heap")
    run("curl http://localhost:4151/debug/pprof/block -o block")
    run("curl http://localhost:4151/debug/pprof/threadcreate -o threadcreate")
    local("mkdir -p target")
    retrieve("profile")
    retrieve("goroutine")
    retrieve("heap")
    retrieve("block")
    retrieve("threadcreate")

