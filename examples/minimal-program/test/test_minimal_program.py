import subprocess
import os

def test_run_program():
    res = subprocess.run(["minimal_program"], stdout=subprocess.PIPE)
    assert res.stdout.decode("utf-8") == "Hello, world!" + os.linesep
