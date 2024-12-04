import re

from swebench.harness.constants import (
    MAP_REPO_ID_TO_FEATURES,
    NON_OSDK_CRATES,
    OSDK_CRATES,
)
from swebench.harness.utils import findCrate


def get_test_features(repo_name, instance_id, test_name):
    if not repo_name in MAP_REPO_ID_TO_FEATURES:
        return None
    if instance_id not in MAP_REPO_ID_TO_FEATURES[repo_name]:
        return None
    if test_name not in MAP_REPO_ID_TO_FEATURES[repo_name][instance_id]:
        return None
    return MAP_REPO_ID_TO_FEATURES[repo_name][instance_id][test_name]


def make_arrow_rs_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    # get instance basic info
    repo, instance_id = instance["repo"], instance["instance_id"]
    # ban cargo test warnning
    cmds = ['export RUSTFLAGS="-Awarnings"']
    # run doc test
    docs = set()
    for paths in [test.split("/") for test in tests_changed]:
        paths.pop()
        while paths and paths[-1] in {"src", "tests", "examples", "benches", "bin"}:
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
        dirs = [dir for dir in test_path.replace("src/lib.rs", "").split("/") if dir]
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --lib")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    # run integration test
    for test_path in tests_changed:
        paths = test_path.split("/")
        dirs, file = paths[:-1], paths[-1]
        name = file.replace(".rs", "")
        features = get_test_features(repo, instance_id, name)
        cmds.append(f"cd ./{'/'.join(dirs)}")
        if features:
            cmds.extend(features["install"] if "install" in features else [])
            cmds.append(
                f"cargo test --no-fail-fast --features=\"{' '.join(features['features'])}\" --test {name}"
            )
        else:
            cmds.append(f"cargo test --no-fail-fast --test {name}")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    # run bin test
    for test_path in tests_changed:
        if "src/bin/" not in test_path:
            continue
        dirs = [dir for dir in test_path.split("src/bin/")[0].split("/") if dir]
        files = test_path.split("src/bin/")[1].split("/")
        if len(files) != 1:
            continue
        file = files[0]
        name = file.replace(".rs", "")
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --bin {name}")
        cmds.append(f"cd ./{'../'*len(dirs)}")
    return cmds


def make_asterinas_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
) :
    DIFF_MODIFIED_FILE_REGEX = r"--- a/(.*)"
    test_files = re.findall(DIFF_MODIFIED_FILE_REGEX, test_patch)
    cmds = []
    test_crates = findCrate(test_files)
    if instance["instance_id"] == "asterinas__asterinas-1073":
        cmds.append("make run AUTO_TEST=syscall ENABLE_KVM=1 BOOT_PROTOCOL=linux-efi-handover64 RELEASE=0")
        cmds.append("make run AUTO_TEST=syscall SYSCALL_TEST_DIR=/exfat  ENABLE_KVM=0 BOOT_PROTOCOL=multiboot2 RELEASE=1")
        return cmds
    for test_crate in test_crates:
        if test_crate in NON_OSDK_CRATES:
            cmds.append(f"cd /{env_name}/{test_crate} ")
            cmds.append(f"cargo test --no-fail-fast ")
        if test_crate in OSDK_CRATES:
            cmds.append(f"cd /{env_name}/{test_crate} ")
            cmds.append("cargo osdk test ")
        if test_crate == "test/apps":
            cmds.append("make run AUTO_TEST=test")
    return cmds


MAP_REPO_TO_TESTS = {
    "apache/arrow-rs": make_arrow_rs_test_cmds,
    "asterinas/asterinas": make_asterinas_test_cmds,
}


def make_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    repo = instance["repo"]
    if repo not in MAP_REPO_TO_TESTS:
        return None
    return MAP_REPO_TO_TESTS[repo](
        instance,
        specs,
        env_name,
        repo_directory,
        base_commit,
        test_patch,
        tests_changed,
    )
