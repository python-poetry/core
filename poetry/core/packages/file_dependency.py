import hashlib
import io

from pathlib import Path
from typing import TYPE_CHECKING
from typing import FrozenSet
from typing import List
from typing import Optional
from typing import Union

from poetry.core.packages.utils.utils import path_to_url

from .dependency import Dependency


if TYPE_CHECKING:
    from .constraints import BaseConstraint


class FileDependency(Dependency):
    def __init__(
        self,
        name: str,
        path: Path,
        category: str = "main",
        optional: bool = False,
        base: Optional[Path] = None,
        extras: Optional[Union[List[str], FrozenSet[str]]] = None,
    ) -> None:
        self._path = path
        self._base = base or Path.cwd()
        self._full_path = path

        if not self._path.is_absolute():
            try:
                self._full_path = self._base.joinpath(self._path).resolve()
            except FileNotFoundError:
                raise ValueError("Directory {} does not exist".format(self._path))

        if not self._full_path.exists():
            raise ValueError("File {} does not exist".format(self._path))

        if self._full_path.is_dir():
            raise ValueError("{} is a directory, expected a file".format(self._path))

        super(FileDependency, self).__init__(
            name,
            "*",
            category=category,
            optional=optional,
            allows_prereleases=True,
            source_type="file",
            source_url=self._full_path.as_posix(),
            extras=extras,
        )

    @property
    def base(self) -> Path:
        return self._base

    @property
    def path(self) -> Path:
        return self._path

    @property
    def full_path(self) -> Path:
        return self._full_path

    def is_file(self) -> bool:
        return True

    def hash(self) -> str:
        h = hashlib.sha256()
        with self._full_path.open("rb") as fp:
            for content in iter(lambda: fp.read(io.DEFAULT_BUFFER_SIZE), b""):
                h.update(content)

        return h.hexdigest()

    def with_constraint(self, constraint: "BaseConstraint") -> "FileDependency":
        new = FileDependency(
            self.pretty_name,
            path=self.path,
            base=self.base,
            optional=self.is_optional(),
            category=self.category,
            extras=self._extras,
        )

        new._constraint = constraint
        new._pretty_constraint = str(constraint)

        new.is_root = self.is_root
        new.python_versions = self.python_versions
        new.marker = self.marker
        new.transitive_marker = self.transitive_marker

        for in_extra in self.in_extras:
            new.in_extras.append(in_extra)

        return new

    @property
    def base_pep_508_name(self) -> str:
        requirement = self.pretty_name

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        path = path_to_url(self.path) if self.path.is_absolute() else self.path
        requirement += " @ {}".format(path)

        return requirement

    def __str__(self) -> str:
        if self.is_root:
            return self._pretty_name

        return "{} ({} {})".format(
            self._pretty_name, self._pretty_constraint, self._path
        )

    def __hash__(self) -> int:
        return hash((self._name, self._full_path))
