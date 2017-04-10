# V-REP as tethered robotics simulation environment
# Python Wrapper
# Qin Yongliang 20170410

# 0. import the vrep library
try:
    print('trying to import vrep...')
    import vrep
    print('vrep imported.')
except:
    print ('--------------------------------------------------------------')
    print ('"vrep.py" could not be imported. This means very probably that')
    print ('either "vrep.py" or the remoteApi library could not be found.')
    print ('Make sure both are in the same folder as this file,')
    print ('or appropriately adjust the file "vrep.py"')
    print ('--------------------------------------------------------------')
    print ('')
    raise

# 1. start vrep in a sub process
# vrep.exe -gREMOTEAPISERVERSERVICE_PORT_DEBUG_PREENABLESYNC
# where PORT -> 19997, DEBUG -> FALSE, PREENABLESYNC -> TRUE
# by default the server will start at 19997,
# use the -g argument if you want to start the server on a different port.

dir_bindings = "C:/Program Files/V-REP3/V-REP_PRO_EDU/programming/remoteApiBindings/python/python"
dir_vrep = "C:/Program Files/V-REP3/V-REP_PRO_EDU"

import subprocess as sp

# the class holding a subprocess instance.
class instance():
    def __init__(self,args):
        self.args = args
    def start(self):
        print('(instance) starting...')
        self.inst = sp.Popen(self.args)
        return self
    def end(self):
        print('(instance) terminating...')
        if self.inst.poll() is None:
            self.inst.terminate()
            retcode = self.inst.wait()
        else:
            retcode = self.inst.returncode
        print('(instance) retcode:',retcode)
        return self

# class holding a v-rep simulation environment.
import time
class vrepper():
    def __init__(self,port_num=19997):
        self.port_num = port_num

        path_vrep = dir_vrep + '/vrep'
        args = [path_vrep, '-gREMOTEAPISERVERSERVICE_'+str(self.port_num)+'_FALSE_TRUE']

        self.instance = instance([path_vrep])
        self.cid = -1
        # clientID of the instance,
        # to differentiate between instances in the driver

        self.started = False
        
    def start(self):
        if self.started == True:
            raise RuntimeError('you should not call start() more than once')

        print('(vrepper)starting an instance of V-REP...')
        self.instance.start()

        retries = 0
        while True:
            print ('(vrepper)trying to connect to server on port',self.port_num,'retry:',retries)
            # vrep.simxFinish(-1) # just in case, close all opened connections
            self.cid = vrep.simxStart(
                '127.0.0.1',self.port_num,True,True,5000,5) # Connect to V-REP
            if self.cid != -1:
                print ('(vrepper)Connected to remote API server!')
                break
            else:
                print('(vrepper)sleep 1s to wait for v-rep initialization...')
                time.sleep(1)
                retries+=1
                if retries>10:
                    raise RuntimeError('(vrepper)Unable to connect to V-REP after 10 retries.')

        # Now try to retrieve data in a blocking fashion (i.e. a service call):
        res, objs = vrep.simxGetObjects(
            self.cid,
            vrep.sim_handle_all,
            vrep.simx_opmode_blocking)

        if res == vrep.simx_return_ok:
            print ('(vrepper)Number of objects in the scene: ',len(objs))
        else:
            raise RuntimeError('(vrepper)Remote API function call returned with error code: ',res)

        # Now send some data to V-REP in a non-blocking fashion:
        vrep.simxAddStatusbarMessage(self.cid, 'Hello V-REP!', vrep.simx_opmode_oneshot)
        print('(vrepper) V-REP instance started, remote API connection created. Everything seems to be ready.')
        self.started = True
        return self

    def end(self):
        print('(vrepper) shutting things down...')
        # Before closing the connection to V-REP, make sure that the last command sent out had time to arrive. You can guarantee this with (for example):
        #vrep.simxGetPingTime(clientID)

        # Now close the connection to V-REP:
        vrep.simxFinish(self.cid)
        self.instance.end()
        print('(vrepper) everything shut down.')
        return self

venv = vrepper()
venv.start()
time.sleep(30)
venv.end()
