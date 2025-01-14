import base64
import os
import re
from typing import Optional

import requests
from ghapi.all import GhApi


class RepoArchitecture:

    def __init__(self, name: Optional[str] = None, parent=None):
        self.name = name
        self.parent: Optional[RepoArchitecture] = parent
        self.files: set[str] = set()
        self.dirs: dict[str, RepoArchitecture] = dict()
        self.cargo_toml: Optional[str] = None

    def has_dir(self, name: str) -> bool:
        return name in self.dirs

    def get_dir(self, name: str):
        return self.dirs[name]

    def has_file(self, name: str):
        return name in self.files

    def find_dir(self, paths: list[str], create_dir: bool = True):
        current = self
        for path in paths:
            if path in current.dirs:
                current = current.dirs[path]
            else:
                if create_dir:
                    current.dirs[path] = RepoArchitecture(path, current)
                    current = current.dirs[path]
                else:
                    return None
        return current

    def get_full_path(self):
        current, path = self.parent, self.name
        while current:
            if current.name:
                path = f"{current.name}/{path}"
            current = current.parent
        return path


def _ghapi(token: str) -> GhApi:
    session = requests.Session()
    session.request = lambda *args, **kwargs: requests.request(
        *args, timeout=4, **kwargs
    )
    return GhApi(token=token, session=session)


def _ghapi_info(
    api: GhApi, owner: str, repo: str, path: str, commit: Optional[str] = None
):
    while True:
        try:
            return api.repos.get_content(owner, repo, path, ref=commit)
        except (KeyboardInterrupt, SystemExit) as e:
            raise e
        except:
            pass


def _ghapi_file(
    api: GhApi, owner: str, repo: str, path: str, commit: Optional[str] = None
):
    return base64.b64decode(
        _ghapi_info(api, owner, repo, path, commit)["content"]
    ).decode()


def _ghapi_tree(api: GhApi, owner: str, repo: str, commit: str = "HEAD"):
    while True:
        try:
            return api.git.get_tree(owner, repo, commit, recursive=True)["tree"]
        except (KeyboardInterrupt, SystemExit) as e:
            raise e
        except:
            pass


def get_repo_arch(
    token: str, owner: str, repo: str, commit: Optional[str] = None
) -> RepoArchitecture:
    api = _ghapi(token)

    root = RepoArchitecture(None)

    for item in _ghapi_tree(api, owner, repo, commit):
        print(item)
        item_type, item_path = item["type"], item["path"]

        paths = item_path.split("/")

        if item_type == "tree":
            root.find_dir(paths)

        elif item["type"] == "blob":
            paths = item["path"].split("/")
            paths, name = paths[:-1], paths[-1]
            arch = root.find_dir(paths)
            if name == "Cargo.toml":
                arch.cargo_toml = _ghapi_file(api, owner, repo, item_path, commit)
            elif name.endswith(".rs"):
                arch.files.add(name)

    return root


def get_repo_version(
    repo: str,
    root: RepoArchitecture,
    default_version: Optional[str] = None,
) -> str:
    def _extract_version(_content: Optional[str]):
        if not _content:
            return None
        m = re.search(r'^\s*version\s*=\s*"\s*(\S*)\s*"\s*$', _content)
        if m:
            return m.group(1)
        else:
            return None

    version = _extract_version(root.cargo_toml)
    if version:
        return version
    queue: list[RepoArchitecture] = [root]
    while queue:
        arch = queue.pop(0)
        if arch.name == repo:
            version = _extract_version(arch.cargo_toml)
            if version:
                return version
        queue.extend(arch.dirs.values())
    return default_version


def get_cargo_test_cmd(
    root: RepoArchitecture, tests: list[str], flags: Optional[str] = None
) -> list[str]:
    submodule_test_dict = dict()
    for test in tests:
        # assert .rs file
        if not test.endswith(".rs"):
            continue
        paths = test.split("/")
        paths, name = paths[:-1], paths[-1]
        # find nearest cargo submodule
        module = root.find_dir(paths, create_dir=False)
        while not module.cargo_toml:
            module = module.parent
        module_path = module.get_full_path()
        # init submodule tests
        if module_path not in submodule_test_dict:
            submodule_test_dict[module_path] = list()
        # try integration test
        if module.has_dir("tests") and f"{module_path}/tests/{name}" == test:
            if isinstance(submodule_test_dict[module_path], list):
                submodule_test_dict[module_path].append(
                    f'cargo test --no-fail-fast --all-features --test "{name}"'
                )
        # try bin test
        elif (
            module.has_dir("src")
            and module.get_dir("src").has_dir("bin")
            and f"{module_path}/src/bin/{name}" == test
        ):
            if isinstance(submodule_test_dict[module_path], list):
                submodule_test_dict[module_path].append(
                    f'cargo test --no-fail-fast --all-features --bin "{name}"'
                )
        # try example test
        elif module.has_dir("examples") and f"{module_path}/examples/{name}" == test:
            if isinstance(submodule_test_dict[module_path], list):
                submodule_test_dict[module_path].append(
                    f'cargo test --no-fail-fast --all-features --example "{name}"'
                )
        # try bench test
        elif module.has_dir("benches") and f"{module_path}/benches/{name}" == test:
            if isinstance(submodule_test_dict[module_path], list):
                submodule_test_dict[module_path].append(
                    f'cargo test --no-fail-fast --all-features --bench "{name}"'
                )
        # test all
        else:
            submodule_test_dict[module_path] = None
    cmds = list()
    if flags:
        cmds.append(f'export RUSTFLAGS="{flags}"')
        cmds.append(f'export RUSTDOCFLAGS="{flags}"')
    for module_path in submodule_test_dict:
        if module_path:
            cmds.append(f'cd "{module_path}"')
        if submodule_test_dict[module_path]:
            cmds.extend(submodule_test_dict[module_path])
        else:
            cmds.append(f"cargo test --no-fail-fast --all-features")
        if module_path:
            cmds.append(f'cd {"../" * (module_path.count("/") + 1)}')
    return cmds


def test_bitflags_1(root):
    print(
        get_cargo_test_cmd(
            root,
            ["tests/basic.rs"],
        )
    )


def test_bitflags_2(root):
    print(
        get_cargo_test_cmd(
            root,
            ["tests/basic.rs", "tests/compile-fail/redefined.rs"],
        )
    )


def test_bitflags_3(root):
    print(
        get_cargo_test_cmd(
            root,
            [
                "tests/basic.rs",
                "tests/compile-fail/redefined.rs",
                "tests/compile-fail/trait/custom_impl.rs",
            ],
        )
    )


def test_bitflags_4(root):
    print(
        get_cargo_test_cmd(
            root,
            [
                "tests/basic.rs",
                "tests/compile-fail/redefined.rs",
                "tests/compile-fail/trait/custom_impl.rs",
                "tests/smoke-test/src/main.rs",
            ],
        )
    )


def test_bitflags_5(root):
    print(
        get_cargo_test_cmd(
            root,
            [
                "tests/basic.rs",
                "tests/compile-fail/redefined.rs",
                "tests/compile-fail/trait/custom_impl.rs",
                "tests/smoke-test/src/main.rs",
                "src/lib.rs",
            ],
        )
    )


def test_bitflags():
    root = get_repo_arch(
        os.environ["GITHUB_TOKENS"],
        "bitflags",
        "bitflags",
        "dc971042c8132a5381ab3e2165983ee7f9d44c63",
    )
    print(get_repo_version("bitflags", root, "0.0.0"))
    test_bitflags_1(root)
    test_bitflags_2(root)
    test_bitflags_3(root)
    test_bitflags_4(root)
    test_bitflags_5(root)


def test_arrow_1(root):
    print(get_cargo_test_cmd(root, ["arrow-flight/tests/flight_sql_client.rs"]))


def test_arrow_2(root):
    print(
        get_cargo_test_cmd(
            root,
            [
                "arrow-flight/tests/flight_sql_client.rs",
                "arrow-flight/examples/server.rs",
            ],
        )
    )


def test_arrow_3(root):
    print(
        get_cargo_test_cmd(
            root,
            [
                "arrow-flight/tests/flight_sql_client.rs",
                "arrow-flight/examples/server.rs",
                "testing/data/csv/README.md",
            ],
        )
    )


def test_arrow():
    root = get_repo_arch(
        os.environ["GITHUB_TOKENS"],
        "apache",
        "arrow-rs",
        "9ffa06543be51613ea1f509e63f6e7405b7d9989",
    )
    print(get_repo_version("arrow", root, "0.0.0"))
    test_arrow_1(root)
    test_arrow_2(root)
    test_arrow_3(root)


if __name__ == "__main__":
    # test_bitflags()
    test_arrow()
