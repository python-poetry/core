import sys

from typing import List


PY36 = sys.version_info >= (3, 6)
PY37 = sys.version_info >= (3, 7)

WINDOWS = sys.platform == "win32"


try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError  # noqa


def list_to_shell_command(cmd: List[str]) -> str:
    executable = cmd[0]

    if " " in executable:
        executable = '"{}"'.format(executable)
        cmd[0] = executable

    return " ".join(cmd)
