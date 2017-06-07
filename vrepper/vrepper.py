# V-REP as tethered robotics simulation environment
# Python Wrapper
# Qin Yongliang 20170410

# import the vrep library
try:
    print('trying to import vrep...')
    from . import vrep

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

import functools
import subprocess as sp
import warnings
from inspect import getargspec

from numpy import deg2rad, rad2deg

list_of_instances = []
import atexit


def cleanup():  # kill all spawned subprocesses on exit
    for i in list_of_instances:
        i.end()


atexit.register(cleanup)


def deprecated(msg=''):
    def dep(func):
        '''This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.'''

        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warnings.warn_explicit(
                "Call to deprecated function {}. {}".format(func.__name__, msg),
                category=DeprecationWarning,
                filename=func.func_code.co_filename,
                lineno=func.func_code.co_firstlineno + 1
            )
            return func(*args, **kwargs)

        return new_func

    return deprecated


# the class holding a subprocess instance.
class instance():
    def __init__(self, args):
        self.args = args
        list_of_instances.append(self)

    def start(self):
        print('(instance) starting...')
        try:
            self.inst = sp.Popen(self.args)
        except EnvironmentError:
            print('(instance) Error: cannot find executable at', self.args[0])
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
        print('(instance) retcode:', retcode)
        return self


# class holding a v-rep simulation environment.
import types, random
import numpy as np

blocking = vrep.simx_opmode_blocking
oneshot = vrep.simx_opmode_oneshot


class vrepper():
    def __init__(self, port_num=None, dir_vrep='', headless=False):
        if port_num is None:
            port_num = int(random.random() * 1000 + 19999)

        self.port_num = port_num

        if dir_vrep == '':
            print('(vrepper) trying to find V-REP executable in your PATH')
            import distutils.spawn as dsp
            path_vrep = dsp.find_executable('vrep.sh')  # fix for linux
            if path_vrep == None:
                path_vrep = dsp.find_executable('vrep')
        else:
            path_vrep = dir_vrep + 'vrep'
        print('(vrepper) path to your V-REP executable is:', path_vrep)

        # start V-REP in a sub process
        # vrep.exe -gREMOTEAPISERVERSERVICE_PORT_DEBUG_PREENABLESYNC
        # where PORT -> 19997, DEBUG -> FALSE, PREENABLESYNC -> TRUE
        # by default the server will start at 19997,
        # use the -g argument if you want to start the server on a different port.
        args = [path_vrep, '-gREMOTEAPISERVERSERVICE_' + str(self.port_num) + '_FALSE_TRUE']

        if headless:
            args.append('-h')

        # instance created but not started.
        self.instance = instance(args)

        self.cid = -1
        # clientID of the instance when connected to server,
        # to differentiate between instances in the driver

        self.started = False

        # is the simulation currently running (as far as we know)
        self.sim_running = False

        # assign every API function call from vrep to self
        vrep_methods = [a for a in dir(vrep) if
                        not a.startswith('__') and isinstance(getattr(vrep, a), types.FunctionType)]

        def assign_from_vrep_to_self(name):
            wrapee = getattr(vrep, name)
            arg0 = getargspec(wrapee)[0][0]
            if arg0 == 'clientID':
                def func(*args, **kwargs):
                    return wrapee(self.cid, *args, **kwargs)
            else:
                def func(*args, **kwargs):
                    return wrapee(*args, **kwargs)
            setattr(self, name, func)

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
            print ('(vrepper)trying to connect to server on port', self.port_num, 'retry:', retries)
            # vrep.simxFinish(-1) # just in case, close all opened connections
            self.cid = self.simxStart(
                '127.0.0.1', self.port_num,
                waitUntilConnected=True,
                doNotReconnectOnceDisconnected=True,
                timeOutInMs=1000,
                commThreadCycleInMs=0)  # Connect to V-REP

            if self.cid != -1:
                print ('(vrepper)Connected to remote API server!')
                break
            else:
                retries += 1
                if retries > 15:
                    self.end()
                    raise RuntimeError('(vrepper)Unable to connect to V-REP after 15 retries.')

        # Now try to retrieve data in a blocking fashion (i.e. a service call):
        objs, = check_ret(self.simxGetObjects(
            vrep.sim_handle_all,
            blocking))

        print ('(vrepper)Number of objects in the scene: ', len(objs))

        # Now send some data to V-REP in a non-blocking fashion:
        self.simxAddStatusbarMessage(
            '(vrepper)Hello V-REP!',
            vrep.simx_opmode_oneshot)

        # setup a useless signal
        self.simxSetIntegerSignal('asdf', 1, blocking)

        print('(vrepper) V-REP instance started, remote API connection created. Everything seems to be ready.')

        self.started = True
        return self

    # kill everything, clean up
    def end(self):
        print('(vrepper) shutting things down...')
        # Before closing the connection to V-REP, make sure that the last command sent out had time to arrive. You can guarantee this with (for example):
        # vrep.simxGetPingTime(clientID)

        # Now close the connection to V-REP:
        if self.sim_running:
            self.stop_simulation()
        self.simxFinish()
        self.instance.end()
        print('(vrepper) everything shut down.')
        return self

    def load_scene(self, fullpathname):
        print('(vrepper) loading scene from', fullpathname)
        try:
            check_ret(self.simxLoadScene(fullpathname,
                                         0,  # assume file is at server side
                                         blocking))
        except:
            print('(vrepper) scene loading failure')
            raise
        print('(vrepper) scene successfully loaded')

    def start_blocking_simulation(self):
        self.start_simulation(True)

    def start_nonblocking_simulation(self):
        self.start_simulation(False)

    def start_simulation(self, is_sync):
        # IMPORTANT
        # you should poll the server state to make sure
        # the simulation completely stops before starting a new one
        while True:
            # poll the useless signal (to receive a message from server)
            check_ret(self.simxGetIntegerSignal(
                'asdf', blocking))

            # check server state (within the received message)
            e = self.simxGetInMessageInfo(
                vrep.simx_headeroffset_server_state)

            # check bit0
            not_stopped = e[1] & 1

            if not not_stopped:
                break

        # enter sync mode
        check_ret(self.simxSynchronous(is_sync))
        check_ret(self.simxStartSimulation(blocking))
        self.sim_running = True

    def make_simulation_synchronous(self, sync):
        if not self.sim_running:
            print('(vrepper) simulation doesn\'t seem to be running. starting up')
            self.start_simulation(sync)
        else:
            check_ret(self.simxSynchronous(sync))

    def stop_simulation(self):
        check_ret(self.simxStopSimulation(oneshot), ignore_one=True)
        self.sim_running = False

    @deprecated('Please use method "stop_simulation" instead.')
    def stop_blocking_simulation(self):
        self.stop_simulation()

    def step_blocking_simulation(self):
        check_ret(self.simxSynchronousTrigger())

    def get_object_handle(self, name):
        handle, = check_ret(self.simxGetObjectHandle(name, blocking))
        return handle

    def get_object_by_handle(self, handle, is_joint=True):
        """
        Get the vrep object for a given handle

        :param int handle: handle code
        :param bool is_joint: True if the object is a joint that can be moved
        :returns: vrepobject
        """
        return vrepobject(self, handle, is_joint)

    def get_object_by_name(self, name, is_joint=True):
        """
        Get the vrep object for a given name

        :param str name: name of the object
        :param bool is_joint: True if the object is a joint that can be moved
        :returns: vrepobject
        """
        return self.get_object_by_handle(self.get_object_handle(name), is_joint)

    @staticmethod
    def create_params(ints=[], floats=[], strings=[], bytes=''):
        if bytes == '':
            bytes_in = bytearray()
        else:
            bytes_in = bytes
        return (ints, floats, strings, bytes_in)

    def call_script_function(self, function_name, params, script_name="remoteApiCommandServer"):
        """
        Calls a function in a script that is mounted as child in the scene

        :param str script_name: the name of the script that contains the function
        :param str function_name: the name of the function to call
        :param tuple params: the parameters to call the function with (must be 4 parameters: list of integers, list of floats, list of string, and bytearray

        :returns: tuple (res_ints, res_floats, res_strs, res_bytes)
            WHERE
            list res_ints is a list of integer results
            list res_floats is a list of floating point results
            list res_strs is a list of string results
            bytearray res_bytes is a bytearray containing the resulting bytes
        """
        assert type(params) is tuple
        assert len(params) == 4

        return check_ret(self.simxCallScriptFunction(
            script_name,
            vrep.sim_scripttype_childscript,
            function_name,
            params[0],  # integers
            params[1],  # floats
            params[2],  # strings
            params[3],  # bytes
            blocking
        ))


# check return tuple, raise error if retcode is not OK,
# return remaining data otherwise
def check_ret(ret_tuple, ignore_one=False):
    istuple = isinstance(ret_tuple, tuple)
    if not istuple:
        ret = ret_tuple
    else:
        ret = ret_tuple[0]

    if (not ignore_one and ret != vrep.simx_return_ok) or (ignore_one and ret > 1):
        raise RuntimeError('retcode(' + str(ret) + ') not OK, API call failed. Check the paramters!')

    return ret_tuple[1:] if istuple else None


class vrepobject():
    def __init__(self, env, handle, is_joint=True):
        self.env = env
        self.handle = handle
        self.is_joint = is_joint

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

    def set_velocity(self, v):
        self._check_joint()
        return check_ret(self.env.simxSetJointTargetVelocity(
            self.handle,
            v,
            blocking))

    def set_force(self, f):
        self._check_joint()
        return check_ret(self.env.simxSetJointForce(
            self.handle,
            f,
            blocking))

    def set_position_target(self, angle):
        """
        Set desired position of a servo

        :param int angle: target servo angle in degrees
        :return: None if successful, otherwise raises exception
        """
        self._check_joint()
        return check_ret(self.env.simxSetJointTargetPosition(
            self.handle,
            -deg2rad(angle),
            blocking))

    def get_joint_angle(self):
        self._check_joint()
        angle = check_ret(
            self.env.simxGetJointPosition(
                self.handle,
                blocking
            )
        )
        return -rad2deg(angle[0])

    def get_joint_force(self):
        self._check_joint()
        force = check_ret(
            self.env.simxGetJointForce(
                self.handle,
                blocking
            )
        )
        return force

    def read_force_sensor(self):
        state, forceVector, torqueVector = check_ret(self.env.simxReadForceSensor(
            self.handle,
            blocking))

        if state & 1 == 1:
            return None  # sensor data not ready
        else:
            return forceVector, torqueVector

    def get_vision_image(self):
        resolution, image = check_ret(self.env.simxGetVisionSensorImage(
            self.handle,
            0,  # options=0 -> RGB
            blocking,
        ))
        dim, im = resolution, image
        nim = np.array(im, dtype='uint8')
        nim = np.reshape(nim, (dim[1], dim[0], 3))
        nim = np.flip(nim, 0)  # LR flip
        nim = np.flip(nim, 2)  # RGB -> BGR
        return nim

    def _check_joint(self):
        if not self.is_joint:
            raise Exception("Trying to call a joint function on a non-joint object.")
