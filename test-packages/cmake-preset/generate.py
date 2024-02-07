import sys
from pathlib import Path

with Path("__init__.py").open("w") as f:
    f.write('secret = "' + sys.argv[1] + '"')
