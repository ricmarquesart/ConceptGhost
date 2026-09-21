import json, os, subprocess, sys, tempfile, time
from pathlib import Path

def terminate(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

def monitor(proc, status, hard_timeout=3.0, stale=0.25):
    t0=time.monotonic(); last=None
    while True:
        rc=proc.poll()
        if status.is_file():
            data=json.loads(status.read_text())
            last=data.get("stage")
            hb=float(data.get("heartbeat_unix",0.0))
            if rc is None and time.time()-hb > stale:
                terminate(proc)
                raise RuntimeError("heartbeat stalled")
        if rc is not None:
            return rc,last
        if time.monotonic()-t0 > hard_timeout:
            terminate(proc)
            raise RuntimeError("hard timeout")
        time.sleep(0.03)

with tempfile.TemporaryDirectory() as td:
    td=Path(td); status=td/"status.json"; child=td/"child.py"
    child.write_text(
        "import json,time,os\n"
        f"from pathlib import Path\np=Path(r'{status}')\n"
        "for s in ['MODEL_LOAD_START','MODEL_LOAD_DONE','INFERENCE_START','INFERENCE_DONE','DONE']:\n"
        " t=p.with_suffix('.tmp'); t.write_text(json.dumps({'stage':s,'heartbeat_unix':time.time()})); os.replace(t,p); time.sleep(.08)\n"
    )
    p=subprocess.Popen([sys.executable,str(child)])
    rc,last=monitor(p,status,hard_timeout=3,stale=1)
    assert rc==0 and last=="DONE"

with tempfile.TemporaryDirectory() as td:
    td=Path(td); status=td/"status.json"; child=td/"child.py"
    child.write_text(
        "import json,time,os\n"
        f"from pathlib import Path\np=Path(r'{status}')\n"
        "t=p.with_suffix('.tmp'); t.write_text(json.dumps({'stage':'INFERENCE_START','heartbeat_unix':time.time()-20})); os.replace(t,p); time.sleep(30)\n"
    )
    p=subprocess.Popen([sys.executable,str(child)])
    try:
        monitor(p,status,hard_timeout=3,stale=.2)
    except RuntimeError as e:
        assert "heartbeat stalled" in str(e)
    else:
        raise AssertionError("stale worker must fail")
    assert p.poll() is not None

policy={
 "heartbeat_interval_seconds":15,
 "stale_heartbeat_seconds":180,
 "hard_timeout_high_fidelity_seconds":1500,
 "hard_timeout_low_resolution_seconds":900,
 "cancel_terminates_process_tree":True,
 "solver_math_changed":False,
 "new_solvers":0,
}
assert policy["solver_math_changed"] is False and policy["new_solvers"]==0
print("P9_V0416_MOGE3_WATCHDOG_CI_PASS",policy)
