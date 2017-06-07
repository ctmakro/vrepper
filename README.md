# vrepper

Tethered V-REP (using V-REP as a remote controlled multi-body simulator) in Python.

The Python binding (`vrep.py` and `vrepConst.py`) and the driver libraries (`remoteApi.dll`, `remoteApi.dylib`, and `remoteApi.so`) are copied as-is from V-REP PRO EDU V3.4

Thanks to Florian Golemo (https://github.com/fgolemo/vrepper) for help on the Linux side :)

> THIS IS A FORK FROM https://github.com/ctmakro/vrepper, WITH SOME ADDITIONAL FEATURES:
>
> (I created a pull request to the original repo, but the author hasn't accepted yet)
> - Linux support
> - versioned V-Rep libraries, so you don't get any weird version conflicts
> - Python 2.7 support
> - access to joint angles (reading/writing)
> - access to synchronous/non-synchronous simuation
> - PEP-8 conformity 

## Usage

Add the path to your V-REP installation to your `PATH`:

- (Windows) might be something like `C:/Program Files/V-REP3/V-REP_PRO_EDU/`

  ```bash
  $ set PATH=%PATH%;C:/Program Files/V-REP3/V-REP_PRO_EDU/
  ```

- (Mac OS X) might be something like `/Users/USERNAME/V-REP_PRO_EDU/vrep.app/Contents/MacOS/`

  ```bash
  $ export PATH=$PATH:"/Users/USERNAME/V-REP_PRO_EDU/vrep.app/Contents/MacOS/"
  ```

- (Linux) might be something like `/home/USERNAME/tools/V-REP_PRO_EDU_V3_4_0_Linux`

  ```bash
  $ export PATH="/home/USERNAME/tools/V-REP_PRO_EDU_V3_4_0_Linux":$PATH
  ```

Then run the following:

```bash
$ git clone https://github.com/ctmakro/vrepper
$ cd vrepper
$ pip install -e . #(install the vrepper package in edit mode)
$ ipython test_body_joint.py #(run the example)
```

The last command will start V-REP in headless mode (no GUI) and run a simple simulation step-by-step. Then it will shut itself down and exit.

## Why should you use V-REP

- build your model with its GUI tools
- simulate your model with whatever programming language you like

## Why should you use vrepper

If you are looking for:

- remote controlled simulation
- low overhead communication
- ability to start/stop simulation repeatedly to perform all kinds of experiment

Then vrepper has already paved the way for you. You should at least take a look at vrepper's source code.

## Known Issues

- On Linux after the end of the script the V-Rep process isn't killed properly. Workaround: run "killall vrep" manually after the script finishes.
