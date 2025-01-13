import base64
import os
import re
from typing import Optional

import requests
from ghapi.all import GhApi


class RepoArchitecture:

    def __init__(self, parent=None):
        self.parent: Optional[RepoArchitecture] = parent
        self.files: list[str] = []
        self.dirs: dict[str, RepoArchitecture] = {}
        self.cargo_toml: Optional[str] = None


def _ghapi(token: str) -> GhApi:
    session = requests.Session()
    session.request = lambda *args, **kwargs: requests.request(*args, timeout=4, **kwargs)
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


def get_repo_arch(
        token: str, owner: str, repo: str, commit: Optional[str] = None
) -> RepoArchitecture:
    def _get_path_basename(path: str) -> str:
        return path.split("/")[-1]

    def _get_repo_arch(
            _api: GhApi,
            _owner: str,
            _repo: str,
            _commit: Optional[str] = None,
            _parent: Optional[RepoArchitecture] = None,
            _path: str = "",
    ):
        arch = RepoArchitecture(_parent)
        for content in _ghapi_info(_api, _owner, _repo, _path, _commit):
            if content["type"] == "dir":
                arch.dirs[_get_path_basename(content["path"])] = _get_repo_arch(
                    _api, _owner, _repo, _commit, arch, content["path"]
                )
            else:
                if content["name"].endswith(".rs"):
                    arch.files.append(_get_path_basename(content["path"]))
                elif content["name"] == "Cargo.toml":
                    arch.cargo_toml = _ghapi_file(
                        _api, _owner, _repo, content["path"], _commit
                    )
        return arch

    return _get_repo_arch(_ghapi(token), owner, repo, commit)



if __name__ == "__main__":
    repo_arch = get_repo_arch(
        os.environ["GITHUB_TOKENS"],
        "bitflags",
        "bitflags",
        "9c4b93c931e34a5104f50e20be1bdd15bc593b0e",
    )
    print(repo_arch.files)