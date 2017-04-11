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

import subprocess as sp

# the class holding a subprocess instance.
class instance():
    def __init__(self,args):
        self.args = args
    def start(self):
        print('(instance) starting...')
        try:
            self.inst = sp.Popen(self.args)
        except FileNotFoundError:
            print('(vrepper) Error: cannot find vrep executable at',self.args[0])
            raise

        return self
    def isAlive(self):
        return True if self.inst.poll() is None else False
    def end(self):
        print('(instance) terminating...')
        if self.isAlive():
            self.inst.terminate()
            retcode = self.inst.wait()
        else:
            retcode = self.inst.returncode
        print('(instance) retcode:',retcode)
        return self

# class holding a v-rep simulation environment.
import time, types, math, random
import inspect, platform

blocking = vrep.simx_opmode_blocking
class vrepper():
    def __init__(self,port_num=None,dir_vrep=''):
        if port_num is None:
            port_num = int(random.random()*1000 + 19999)

        self.port_num = port_num

        if dir_vrep=='':
            print('(vrepper) trying to find V-REP executable in your PATH')
            import distutils.spawn as dsp
            path_vrep = dsp.find_executable('vrep')
        else:
            path_vrep = dir_vrep + 'vrep'
        print('(vrepper) path to your V-REP executable is:',path_vrep)

        # start V-REP in a sub process
        # vrep.exe -gREMOTEAPISERVERSERVICE_PORT_DEBUG_PREENABLESYNC
        # where PORT -> 19997, DEBUG -> FALSE, PREENABLESYNC -> TRUE
        # by default the server will start at 19997,
        # use the -g argument if you want to start the server on a different port.
        args = [path_vrep, '-gREMOTEAPISERVERSERVICE_'+str(self.port_num)+'_FALSE_TRUE']

        # instance created but not started.
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

        # try to connect to V-REP instance via socket
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
        objs, = check_ret(self.simxGetObjects(
            vrep.sim_handle_all,
            blocking))

        print ('(vrepper)Number of objects in the scene: ',len(objs))

        # Now send some data to V-REP in a non-blocking fashion:
        self.simxAddStatusbarMessage(
            '(vrepper)Hello V-REP!',
            vrep.simx_opmode_oneshot)
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

    def load_scene(self,fullpathname):
        print('(vrepper) loading scene from',fullpathname)
        try:
            check_ret(self.simxLoadScene(fullpathname,
                0, # assume file is at server side
                blocking))
        except:
            print('(vrepper) scene loading failure')
            raise
        print('(vrepper) scene successfully loaded')

    def start_blocking_simulation(self):
        check_ret(venv.simxSynchronous(True))
        check_ret(venv.simxStartSimulation(blocking))

    def stop_blocking_simulation(self):
        check_ret(venv.simxStopSimulation(blocking))
        check_ret(venv.simxSynchronous(False))

    def step_blocking_simulation(self):
        check_ret(venv.simxSynchronousTrigger())

    def get_object_handle(self,name):
        handle, = check_ret(self.simxGetObjectHandle(name,blocking))
        return handle

    def get_object_by_handle(self,handle):
        return vrepobject(self,handle)

    def get_object_by_name(self,name):
        return self.get_object_by_handle(self.get_object_handle(name))

# check return tuple, raise error if retcode is not OK,
# return remaining data otherwise
def check_ret(ret_tuple):
    istuple = isinstance(ret_tuple,tuple)
    if not istuple:
        ret = ret_tuple
    else:
        ret = ret_tuple[0]
    if ret!=vrep.simx_return_ok:
        raise RuntimeError('retcode not OK, API call failed. Check the paramters!')

    return ret_tuple[1:] if istuple else None

class vrepobject():
    def __init__(self,env,handle):
        self.env = env
        self.handle = handle

    def get_orientation(self, relative_to=None):
        eulerAngles, = check_ret(self.env.simxGetObjectOrientation(
            self.handle,
            -1 if relative_to is None else relative_to.handle,
            blocking))
        return eulerAngles

    def get_position(self, relative_to=None):
        position, = check_ret(self.env.simxGetObjectPosition(
            self.handle,
            -1 if relative_to is None else relative_to.handle,
            blocking))
        return position

    def get_velocity(self):
        return check_ret(self.env.simxGetObjectVelocity(
            self.handle,
            # -1 if relative_to is None else relative_to.handle,
            blocking))
        # linearVel, angularVel

    def set_velocity(self,v):
        return check_ret(self.env.simxSetJointTargetVelocity(
            self.handle,
            v,
            blocking))

    def read_force_sensor(self):
        state,forceVector,torqueVector = check_ret(self.env.simxReadForceSensor(
            self.handle,
            blocking))

        if state & 1 == 1:
            return None # sensor data not ready
        else:
            return forceVector, torqueVector

if __name__ == '__main__':
    import os

    # # determine the platform we're running on
    # running_os = ''
    # if platform.system() == 'Windows' or platform.system() == 'cli':
    #     running_os = 'win'
    # elif platform.system() == 'Darwin':
    #     running_os = 'osx'
    # else:
    #     running_os = 'linux'
    #
    # print('(main) we are running on',running_os)
    #
    # # locate V-REP (Education Version)
    # if running_os == 'win':
    #     dir_vrep = "C:/Program Files/V-REP3/V-REP_PRO_EDU/"
    # elif running_os == 'osx':
    #     dir_vrep = '/Users/chia/V-REP_PRO_EDU/vrep.app/Contents/MacOS/'
    # else:
    #     raise RuntimeError('Current OS not supported by this piece of code.')
    #
    # venv = vrepper(dir_vrep=dir_vrep)

    venv = vrepper()
    venv.start()

    # load scene
    venv.load_scene(os.getcwd() + '/scenes/body_joint_wheel.ttt')

    body = venv.get_object_by_name('body')
    wheel = venv.get_object_by_name('wheel')
    joint = venv.get_object_by_name('joint')

    print(body.handle,wheel.handle,joint.handle)

    venv.start_blocking_simulation()

    for i in range(100):
        print('simulation step',i)
        print('body position',body.get_position())
        print('wheel orientation',wheel.get_orientation())

        joint.set_velocity(10 * math.sin(i/5))
        # you should see things moving back and forth

        venv.step_blocking_simulation() # forward 1 timestep
        time.sleep(.01)

    # stop the simulation and reset the scene:
    venv.stop_blocking_simulation()

    print('simulation ended. clean up in 5 seconds...')
    time.sleep(5)
    venv.end()
