import sys

from pathlib import Path

__version__ = "1.0.0a0"

__vendor_site__ = (Path(__file__).parent / "_vendor").as_posix()

if __vendor_site__ not in sys.path:
    sys.path.insert(0, __vendor_site__)
