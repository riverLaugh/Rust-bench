import re
from typing import Optional

from swebench.harness.constants import (
    NON_OSDK_CRATES,
    OSDK_CRATES,
)
from swebench.harness.utils import findCrate


def _default_test_commands(
    tests_changed: list[str],
    rust_flags: Optional[str],
    features: list[str] = None,
    use_all_features: bool = False,
    **kwargs,
):
    submodule_tests: dict[str, list | None] = {}
    for test_path in tests_changed:
        match = re.match(r"([\w\-]+)/tests/([\w\-]+)\.rs", test_path)
        # integration test
        if match:
            submodule, test_name = match.group(1), match.group(2)
            if submodule not in submodule_tests:
                submodule_tests[submodule] = [test_name]
            elif isinstance(submodule_tests[submodule], list):
                submodule_tests[submodule].append(test_name)
        # other test
        else:
            submodule_tests[test_path.split("/")[0]] = None
    # generate specific str
    features_str = f'--features="{" ".join(features)}"' if features else ""
    use_all_features_str = "--all-features" if use_all_features else ""
    # generate cmds
    cmds: list[str] = (
        [f'export RUSTFLAGS="{rust_flags}"'] if rust_flags is not None else []
    )
    for submodule, test_names in submodule_tests.items():
        cmds.append(f"cd ./{submodule}")
        if isinstance(test_names, list):
            cmds.extend(
                f"cargo test --no-fail-fast {features_str}{use_all_features_str}--test {test_name}"
                for test_name in test_names
            )
        else:
            cmds.append(
                f"cargo test --no-fail-fast {features_str}{use_all_features_str}"
            )
        cmds.append(f"cd ../")
    return cmds


def make_arrow_rs_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
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
        cmds.append(f"cargo test --no-fail-fast --all-features --doc")
        cmds.append(f"cd ./{'../' * len(dirs)}")
    # run unit test
    for test_path in tests_changed:
        if not test_path.endswith("src/lib.rs"):
            continue
        dirs = [dir for dir in test_path.replace("src/lib.rs", "").split("/") if dir]
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --all-features --lib")
        cmds.append(f"cd ./{'../' * len(dirs)}")
    # run integration test
    for test_path in tests_changed:
        paths = test_path.split("/")
        dirs, file = paths[:-1], paths[-1]
        name = file.replace(".rs", "")
        cmds.append(f"cd ./{'/'.join(dirs)}")
        cmds.append(f"cargo test --no-fail-fast --all-features --test {name}")
        cmds.append(f"cd ./{'../' * len(dirs)}")
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
        cmds.append(f"cargo test --no-fail-fast --all-features --bin {name}")
        cmds.append(f"cd ./{'../' * len(dirs)}")
    return cmds


def make_asterinas_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    cmds = []
    test_crates = findCrate(tests_changed)
    print(test_crates)
    if instance["instance_id"] == "asterinas__asterinas-1073":
        cmds.append(
            "make run AUTO_TEST=syscall ENABLE_KVM=1 BOOT_PROTOCOL=linux-efi-handover64 RELEASE=0"
        )
        cmds.append(
            "make run AUTO_TEST=syscall SYSCALL_TEST_DIR=/exfat  ENABLE_KVM=0 BOOT_PROTOCOL=multiboot2 RELEASE=1"
        )
        return cmds
    for test_crate in test_crates:
        if test_crate in NON_OSDK_CRATES:
            cmds.append(f"cd /{env_name}/{test_crate} ")
            cmds.append(f"cargo test --no-fail-fast --all-features")
            cmds.append(f"cd ..")
        if test_crate in OSDK_CRATES:
            cmds.append(f"cd /{env_name}/{test_crate} ")
            cmds.append("cargo osdk test ")
            cmds.append(f"cd ..")
        if test_crate == "test/apps":
            cmds.append("make run AUTO_TEST=test")
    return cmds


def make_tokio_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    # add allow lint deny
    options = [
        "-Awarnings",
        "-Aunused_must_use",
        "-Aundropped_manually_drops",
        "-Ainvalid_doc_attributes",
        "-Auseless_deprecated",
        "-Aintra_doc_link_resolution_failure",
        "-Alet_underscore_lock",
        "-Arenamed_and_removed_lints",
        "-Abroken_intra_doc_links",
    ]
    return _default_test_commands(
        tests_changed=tests_changed, rust_flags=" ".join(options), use_all_features=True
    )


def make_crossbeam_test_cmds(
    instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
):
    return _default_test_commands(
        tests_changed=tests_changed,
        rust_flags="-Awarnings",
    )


MAP_REPO_TO_TESTS = {
    "apache/arrow-rs": make_arrow_rs_test_cmds,
    "asterinas/asterinas": make_asterinas_test_cmds,
    "tokio-rs/tokio": make_tokio_test_cmds,
    "crossbeam-rs/crossbeam": make_crossbeam_test_cmds,
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
