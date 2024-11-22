import re

from swebench.harness.constants import (
    TEST_CARGO,
    NON_OSDK_CRATES,
    OSDK_CRATES,
)
from swebench.harness.utils import findCrate

def arrow_rs_tests(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    # ban warnning
    cmds = ['export RUSTFLAGS="-Awarnings"']
    # run doc test
    docs = set()
    for paths in [test.split("/") for test in tests_changed]:
        paths.pop()
        while paths and paths[-1] in {"src", "tests", "examples", "benches"}:
            paths.pop()
        docs.add("/".join(paths))
    for dir in docs:
        dirs = dir.split("/")
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --doc")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    # run unit test
    for test_path in tests_changed:
        if not test_path.endswith("src/lib.rs"):
            continue
        dirs = test_path.replace("src/lib.rs", "").split("/")
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --lib")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    # run integration test
    for test_path in tests_changed:
        paths = test_path.split("/")
        dirs, file = paths[:-1], paths[-1]
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --test {file.replace('.rs','')}")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    return cmds


def asterinas_tests(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    DIFF_MODIFIED_FILE_REGEX = r"--- a/(.*)"
    test_files = re.findall(DIFF_MODIFIED_FILE_REGEX, test_patch)
    cmds = []
    test_crates = findCrate(test_files)
    for test_crate in test_crates:
        if test_crate in NON_OSDK_CRATES:
            cmds.append(f"cd {env_name}/{test_crate} & cargo test --no-fail-fast")
        if test_crate in OSDK_CRATES:
            cmds.append(
                f"export CARGO_TERM_COLOR=never && cd {env_name}/{test_crate} & cargo osdk test --no-fail-fast"
            )
    return cmds

AVAIL_REPOS = {
    "apache/arrow-rs": arrow_rs_tests,
    "asterinas/asterinas": asterinas_tests,
}

def make_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    repo = instance["repo"]
    if repo in AVAIL_REPOS:
        return AVAIL_REPOS[repo](
            instance,
            specs,
            env_name,
            repo_directory,
            base_commit,
            test_patch,
            tests_changed,
        )
    else:
        return None
