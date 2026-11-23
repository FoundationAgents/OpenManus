# Python version check: 3.11-3.13
import sys


if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    print(
        "Warning: Unsupported Python version {ver}, please use 3.11-3.13".format(
            ver=".".join(map(str, sys.version_info))
        )
    )
