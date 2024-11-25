import os
import subprocess


def test_run_program():
    res = subprocess.run(["minimal_program"], capture_output=True, check=True)
    assert res.stdout.decode("utf-8") == "Hello, world!" + os.linesep
