from pathlib import Path
from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

from .builders.sdist import SdistBuilder
from .builders.wheel import WheelBuilder


if TYPE_CHECKING:
    from poetry.core.poetry import Poetry  # noqa


class Builder:
    _FORMATS = {
        "sdist": SdistBuilder,
        "wheel": WheelBuilder,
    }

    def __init__(self, poetry: "Poetry") -> None:
        self._poetry = poetry

    def build(self, fmt: str, executable: Optional[Union[str, Path]] = None) -> None:
        if fmt in self._FORMATS:
            builders = [self._FORMATS[fmt]]
        elif fmt == "all":
            builders = self._FORMATS.values()
        else:
            raise ValueError("Invalid format: {}".format(fmt))

        for builder in builders:
            builder(self._poetry, executable=executable).build()
