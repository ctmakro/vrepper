# vrepper

Tethered V-REP in Python.

The Python binding (`vrep.py` and friends) and the driver libraries (`remoteApi.dll` and `remoteApi.dylib`) is copied as-is from V-REP PRO EDU V3.4

## How to

Add the path to your V-REP installation to your `PATH`:

- (Windows) C:/Program Files/V-REP3/V-REP_PRO_EDU/
- (Mac OS X) /Users/chia/V-REP_PRO_EDU/vrep.app/Contents/MacOS/

Then run the following:

```bash
$ ipython hello.py
```

The command above will start V-REP and run a simple simulation step-by-step. Then it will shut itself down and exit.
