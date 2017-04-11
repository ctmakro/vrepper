# V-REP as tethered robotics simulation environment
# Python Wrapper
# Qin Yongliang 20170410

# import the vrep library
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

# start vrep in a sub process
# vrep.exe -gREMOTEAPISERVERSERVICE_PORT_DEBUG_PREENABLESYNC
# where PORT -> 19997, DEBUG -> FALSE, PREENABLESYNC -> TRUE
# by default the server will start at 19997,
# use the -g argument if you want to start the server on a different port.

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
import time, types, math, random
import inspect, platform
class vrepper():
    def __init__(self,port_num=None):
        if port_num is None:
            port_num = int(random.random()*1000 + 19999)

        self.port_num = port_num

        # 1. determine the platform we're running on
        running_os = ''
        if platform.system() == 'Windows' or platform.system() == 'cli':
            running_os = 'win'
        elif platform.system() == 'Darwin':
            running_os = 'osx'
        else:
            running_os = 'linux'

        print('(vrepper) we are running on',running_os)
        self.running_os = running_os

        # determine the location of V-REP (Education version)
        if running_os == 'win':
            dir_vrep = "C:/Program Files/V-REP3/V-REP_PRO_EDU/"
        elif running_os == 'osx':
            dir_vrep = '/Users/chia/V-REP_PRO_EDU/vrep.app/Contents/MacOS/'
        else:
            raise RuntimeError('Current OS not supported by this piece of code.')

        path_vrep = dir_vrep + 'vrep'
        args = [path_vrep, '-gREMOTEAPISERVERSERVICE_'+str(self.port_num)+'_FALSE_TRUE']

        self.instance = instance(args)
        self.cid = -1
        # clientID of the instance when connected to server,
        # to differentiate between instances in the driver

        self.started = False

        # assign every API function call from vrep to self
        vrep_methods = [a for a in dir(vrep) if not a.startswith('__') and  isinstance(getattr(vrep,a), types.FunctionType)]

        def assign_from_vrep_to_self(name):
            wrapee = getattr(vrep,name)
            arg0 = inspect.getfullargspec(wrapee)[0][0]
            if arg0 == 'clientID':
                def func(*args,**kwargs):
                    return wrapee(self.cid,*args,**kwargs)
            else:
                def func(*args,**kwargs):
                    return wrapee(*args,**kwargs)
            setattr(self,name,func)

        for name in vrep_methods:
            assign_from_vrep_to_self(name)

    # start everything
    def start(self):
        if self.started == True:
            raise RuntimeError('you should not call start() more than once')

        print('(vrepper)starting an instance of V-REP...')
        self.instance.start()

        retries = 0
        while True:
            print ('(vrepper)trying to connect to server on port',self.port_num,'retry:',retries)
            # vrep.simxFinish(-1) # just in case, close all opened connections
            self.cid = self.simxStart(
                '127.0.0.1', self.port_num,
                waitUntilConnected=True,
                doNotReconnectOnceDisconnected=True,
                timeOutInMs=1000,
                commThreadCycleInMs=5) # Connect to V-REP

            if self.cid != -1:
                print ('(vrepper)Connected to remote API server!')
                break
            else:
                retries+=1
                if retries>15:
                    self.end()
                    raise RuntimeError('(vrepper)Unable to connect to V-REP after 15 retries.')

        # Now try to retrieve data in a blocking fashion (i.e. a service call):
        res, objs = self.simxGetObjects(
            vrep.sim_handle_all,
            vrep.simx_opmode_blocking)

        if res == vrep.simx_return_ok:
            print ('(vrepper)Number of objects in the scene: ',len(objs))
        else:
            self.end()
            raise RuntimeError('(vrepper)Remote API function call returned with error code: ',res)

        # Now send some data to V-REP in a non-blocking fashion:
        self.simxAddStatusbarMessage('Hello V-REP!', vrep.simx_opmode_oneshot)
        print('(vrepper) V-REP instance started, remote API connection created. Everything seems to be ready.')
        self.started = True
        return self

    # kill everything, clean up
    def end(self):
        print('(vrepper) shutting things down...')
        # Before closing the connection to V-REP, make sure that the last command sent out had time to arrive. You can guarantee this with (for example):
        #vrep.simxGetPingTime(clientID)

        # Now close the connection to V-REP:
        self.simxFinish()
        self.instance.end()
        print('(vrepper) everything shut down.')
        return self

venv = vrepper()
venv.start()
# time.sleep(30)
# venv.end()
