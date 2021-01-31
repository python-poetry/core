from pathlib import Path
from typing import TYPE_CHECKING
from typing import FrozenSet
from typing import List
from typing import Optional
from typing import Union

from poetry.core.pyproject import PyProjectTOML


if TYPE_CHECKING:
    from .constraints import BaseConstraint  # noqa

from .dependency import Dependency


class DirectoryDependency(Dependency):
    def __init__(
        self,
        name: str,
        path: Path,
        category: str = "main",
        optional: bool = False,
        base: Optional[Path] = None,
        develop: bool = False,
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

        self._develop = develop
        self._supports_poetry = False

        if not self._full_path.exists():
            raise ValueError("Directory {} does not exist".format(self._path))

        if self._full_path.is_file():
            raise ValueError("{} is a file, expected a directory".format(self._path))

        # Checking content to determine actions
        setup = self._full_path / "setup.py"
        self._supports_poetry = PyProjectTOML(
            self._full_path / "pyproject.toml"
        ).is_poetry_project()

        if not setup.exists() and not self._supports_poetry:
            raise ValueError(
                "Directory {} does not seem to be a Python package".format(
                    self._full_path
                )
            )

        super(DirectoryDependency, self).__init__(
            name,
            "*",
            category=category,
            optional=optional,
            allows_prereleases=True,
            source_type="directory",
            source_url=self._full_path.as_posix(),
            extras=extras,
        )

    @property
    def path(self) -> Path:
        return self._path

    @property
    def full_path(self) -> Path:
        return self._full_path

    @property
    def base(self) -> Path:
        return self._base

    @property
    def develop(self) -> bool:
        return self._develop

    def supports_poetry(self) -> bool:
        return self._supports_poetry

    def is_directory(self) -> bool:
        return True

    def with_constraint(self, constraint: "BaseConstraint") -> "DirectoryDependency":
        new = DirectoryDependency(
            self.pretty_name,
            path=self.path,
            base=self.base,
            optional=self.is_optional(),
            category=self.category,
            develop=self._develop,
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

        requirement += " @ {}".format(self._path.as_posix())

        return requirement

    def __str__(self) -> str:
        if self.is_root:
            return self._pretty_name

        return "{} ({} {})".format(
            self._pretty_name, self._pretty_constraint, self._path.as_posix()
        )

    def __hash__(self) -> int:
        return hash((self._name, self._full_path.as_posix()))
