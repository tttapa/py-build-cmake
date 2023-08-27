import subprocess
import os

def test_run_program():
    res = subprocess.run(["minimal_program"], capture_output=True)
    assert res.stdout.decode("utf-8") == "Hello, world!" + os.linesep
