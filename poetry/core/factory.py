from __future__ import absolute_import
from __future__ import unicode_literals

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from .json import validate_object
from .packages.dependency import Dependency
from .packages.project_package import ProjectPackage
from .poetry import Poetry
from .spdx import license_by_id
from .utils._compat import Path
from .utils.toml_file import TomlFile


class Factory(object):
    """
    Factory class to create various elements needed by Poetry.
    """

    def create_poetry(self, cwd=None):  # type: (Optional[Path]) -> Poetry
        poetry_file = self.locate(cwd)

        local_config = TomlFile(poetry_file.as_posix()).read()
        if "tool" not in local_config or "poetry" not in local_config["tool"]:
            raise RuntimeError(
                "[tool.poetry] section not found in {}".format(poetry_file.name)
            )
        local_config = local_config["tool"]["poetry"]

        # Checking validity
        check_result = self.validate(local_config)
        if check_result["errors"]:
            message = ""
            for error in check_result["errors"]:
                message += "  - {}\n".format(error)

            raise RuntimeError("The Poetry configuration is invalid:\n" + message)

        # Load package
        name = local_config["name"]
        version = local_config["version"]
        package = self.get_package(name, version)
        package = self.configure_package(package, local_config, poetry_file.parent)

        return Poetry(poetry_file, local_config, package)

    @classmethod
    def get_package(cls, name, version):  # type: (str, str) -> ProjectPackage
        return ProjectPackage(name, version, version)

    @classmethod
    def configure_package(
        cls, package, config, root
    ):  # type: (ProjectPackage, Dict[str, Any], Path) -> ProjectPackage
        package.root_dir = root

        for author in config["authors"]:
            package.authors.append(author)

        for maintainer in config.get("maintainers", []):
            package.maintainers.append(maintainer)

        package.description = config.get("description", "")
        package.homepage = config.get("homepage")
        package.repository_url = config.get("repository")
        package.documentation_url = config.get("documentation")
        try:
            license_ = license_by_id(config.get("license", ""))
        except ValueError:
            license_ = None

        package.license = license_
        package.keywords = config.get("keywords", [])
        package.classifiers = config.get("classifiers", [])

        if "readme" in config:
            package.readme = root / config["readme"]

        if "platform" in config:
            package.platform = config["platform"]

        if "dependencies" in config:
            for name, constraint in config["dependencies"].items():
                if name.lower() == "python":
                    package.python_versions = constraint
                    continue

                if isinstance(constraint, list):
                    for _constraint in constraint:
                        package.add_dependency(name, _constraint)

                    continue

                package.add_dependency(name, constraint)

        if "dev-dependencies" in config:
            for name, constraint in config["dev-dependencies"].items():
                if isinstance(constraint, list):
                    for _constraint in constraint:
                        package.add_dependency(name, _constraint, category="dev")

                    continue

                package.add_dependency(name, constraint, category="dev")

        extras = config.get("extras", {})
        for extra_name, requirements in extras.items():
            package.extras[extra_name] = []

            # Checking for dependency
            for req in requirements:
                req = Dependency(req, "*")

                for dep in package.requires:
                    if dep.name == req.name:
                        dep.in_extras.append(extra_name)
                        package.extras[extra_name].append(dep)

                        break

        if "build" in config:
            build = config["build"]
            if not isinstance(build, dict):
                build = {"script": build}
            package.build_config = build or {}

        if "include" in config:
            package.include = []

            for include in config["include"]:
                if not isinstance(include, dict):
                    include = {"path": include}

                formats = include.get("format", [])
                if formats and not isinstance(formats, list):
                    formats = [formats]
                include["format"] = formats

                package.include.append(include)

        if "exclude" in config:
            package.exclude = config["exclude"]

        if "packages" in config:
            package.packages = config["packages"]

        # Custom urls
        if "urls" in config:
            package.custom_urls = config["urls"]

        return package

    @classmethod
    def validate(
        cls, config, strict=False
    ):  # type: (dict, bool) -> Dict[str, List[str]]
        """
        Checks the validity of a configuration
        """
        result = {"errors": [], "warnings": []}
        # Schema validation errors
        validation_errors = validate_object(config, "poetry-schema")

        result["errors"] += validation_errors

        if strict:
            # If strict, check the file more thoroughly
            if "dependencies" in config:
                python_versions = config["dependencies"]["python"]
                if python_versions == "*":
                    result["warnings"].append(
                        "A wildcard Python dependency is ambiguous. "
                        "Consider specifying a more explicit one."
                    )

                for name, constraint in config["dependencies"].items():
                    if not isinstance(constraint, dict):
                        continue

                    if "allows-prereleases" in constraint:
                        result["warnings"].append(
                            'The "{}" dependency specifies '
                            'the "allows-prereleases" property, which is deprecated. '
                            'Use "allow-prereleases" instead.'.format(name)
                        )

            # Checking for scripts with extras
            if "scripts" in config:
                scripts = config["scripts"]
                for name, script in scripts.items():
                    if not isinstance(script, dict):
                        continue

                    extras = script["extras"]
                    for extra in extras:
                        if extra not in config["extras"]:
                            result["errors"].append(
                                'Script "{}" requires extra "{}" which is not defined.'.format(
                                    name, extra
                                )
                            )

        return result

    @classmethod
    def locate(cls, cwd):  # type: (Path) -> Path
        candidates = [Path(cwd)]
        candidates.extend(Path(cwd).parents)

        for path in candidates:
            poetry_file = path / "pyproject.toml"

            if poetry_file.exists():
                return poetry_file

        else:
            raise RuntimeError(
                "Poetry could not find a pyproject.toml file in {} or its parents".format(
                    cwd
                )
            )
