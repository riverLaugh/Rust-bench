from enum import Enum
from pathlib import Path
from typing import TypedDict

# Constants - Evaluation Log Directories
BASE_IMAGE_BUILD_DIR = Path("logs/build_images/base")
ENV_IMAGE_BUILD_DIR = Path("logs/build_images/env")
INSTANCE_IMAGE_BUILD_DIR = Path("logs/build_images/instances")
RUN_EVALUATION_LOG_DIR = Path("logs/run_validation")


NON_OSDK_CRATES = [
    "osdk",
    "ostd/libs/align_ext",
    "ostd/libs/id-alloc",
    "ostd/libs/linux-bzimage/builder",
    "ostd/libs/linux-bzimage/boot-params",
    "ostd/libs/ostd-macros",
    "ostd/libs/ostd-test",
    "kernel/libs/cpio-decoder",
    "kernel/libs/int-to-c-enum",
    "kernel/libs/int-to-c-enum/derive",
    "kernel/libs/aster-rights",
    "kernel/libs/aster-rights-proc",
    "kernel/libs/keyable-arc",
    "kernel/libs/typeflags",
    "kernel/libs/typeflags-util",
    "kernel/libs/atomic-integer-wrapper",
]

OSDK_CRATES = [
    "osdk/test-kernel",
    "ostd",
    "ostd/libs/linux-bzimage/setup",
    "kernel",
    "kernel/comps/block",
    "kernel/comps/console",
    "kernel/comps/framebuffer",
    "kernel/comps/input",
    "kernel/comps/network",
    "kernel/comps/softirq",
    "kernel/comps/time",
    "kernel/comps/virtio",
    "kernel/libs/aster-util",
    "kernel/libs/aster-bigtcp",
]


# Constants - Task Instance Class
class SWEbenchInstance(TypedDict):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: str
    PASS_TO_PASS: str
    environment_setup_commit: str


# Constants - Test Types, Statuses, Commands
FAIL_TO_PASS = "FAIL_TO_PASS"
FAIL_TO_FAIL = "FAIL_TO_FAIL"
PASS_TO_PASS = "PASS_TO_PASS"
PASS_TO_FAIL = "PASS_TO_FAIL"


class ResolvedStatus(Enum):
    NO = "RESOLVED_NO"
    PARTIAL = "RESOLVED_PARTIAL"
    FULL = "RESOLVED_FULL"


class TestStatus(Enum):
    FAILED = "FAILED"
    PASSED = "PASSED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


# TEST_PYTEST = "pytest --no-header -rA --tb=no -p no:cacheprovider"
# TEST_PYTEST_VERBOSE = "pytest -rA --tb=long -p no:cacheprovider"

TEST_CARGO = "cargo test --no-fail-fast --all-features"

# Constants - Installation Specifications
SPECS_RUSTLINGS = {}

SPECS_SERDE = {"test_cmd": TEST_CARGO}

SPECS_BITFLAGS = {
    k: {"rustc": "1.81.0", "test_cmd": TEST_CARGO}
    for k in ["2.5", "2.4", "2.3", "2.2", "2.1","2.0","1.2"]
}
SPECS_BITFLAGS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            #     "pre_install":[
            #         "cargo upgrade"
            # ]
            "pre_install": [
                r"""sed -i '/\[dependencies\]/a serde = { version = "1.0.210", features = ["derive"] }' Cargo.toml""",
                r"""sed -i 's/serde_json = "1.0"/serde_json = "1.0.69"/' Cargo.toml""",
                r"""sed -i 's/default = \[\]/default = ["derive"]/' Cargo.toml""",
                r"""sed -i '/example_generated = \[\]/i derive = ["serde/derive"]' Cargo.toml""",
            ],
        }
        for k in ["1.3"]
    }
)

SPECS_ARROW = {
    k: {
        "rustc": "1.81.0",
        "test_cmd": TEST_CARGO,
        "pre_install": [
            r"""git submodule update --init""",
        ],
    }
    for k in ["53.2", "53.0", "52.2", "52.1", "52.0", "51.0", "50.0"]
}
SPECS_ARROW.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "env_setup": [
                r"""sed -i 's/ahash = { version = "0.8"/ahash = { version = "0.8.8"/' ./arrow/Cargo.toml""",
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/gen/Cargo.toml""",
            ],
            "pre_install": [
                r"""sed -i 's/ahash = { version = "0.8"/ahash = { version = "0.8.8"/' ./arrow/Cargo.toml""",
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/gen/Cargo.toml""",
                r"""git submodule update --init""",
            ],
        }
        for k in ["49.0", "48.0", "47.0"]
    }
)
SPECS_ARROW.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "env_setup": [
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/gen/Cargo.toml""",
            ],
            "pre_install": [
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/gen/Cargo.toml""",
                r"""git submodule update --init""",
            ],
        }
        for k in ["46.0", "45.0", "40.0", "39.0", "38.0", "37.0", "36.0", "35.0"]
    }
)
SPECS_ARROW.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "env_setup": [
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/Cargo.toml""",
            ],
            "pre_install": [
                r"""sed -i 's/proc-macro2 = { version = "=1\.0\.[0-9]\+"/proc-macro2 = { version = "=1.0.75"/' ./arrow-flight/Cargo.toml""",
                r"""git submodule update --init""",
            ],
        }
        for k in [
            "34.0",
            "33.0",
            "32.0",
            "31.0",
            "30.0",
            "29.0",
            "28.0",
            "27.0",
            "26.0",
            "25.0",
            "24.0",
            "21.0",
            "20.0",
            "19.0",
            "18.0",
            "17.0",
            "16.0",
            "15.0",
            "14.0",
            "13.0",
            "11.1",
            "11.0",
            "10.0",
            "9.0",
            "8.0",
            "7.0",
        ]
    }
)
SPECS_ARROW.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "env_setup": [
                r"""sed -i 's/proc-macro2 = "=1\.0\.[0-9]\+"/proc-macro2 = "=1.0.75"/' ./arrow-flight/Cargo.toml""",
            ],
            "pre_install": [
                r"""sed -i 's/proc-macro2 = "=1\.0\.[0-9]\+"/proc-macro2 = "=1.0.75"/' ./arrow-flight/Cargo.toml""",
                r"""git submodule update --init""",
            ],
        }
        for k in [
            "0.8",
            "0.6",
            "0.3"
        ]
    }
)




SPECS_ASTERINAS = {
    k: {
        "rustc": "1.81.0",
        "test_cmd": TEST_CARGO,
        "image_tag": "0.8.3",
        "pre_install": [
            r"""
            git fetch origin pull/1666/head:pr-1666
            git checkout main
            git cherry-pick -X theirs pr-1666
            git branch -D pr-1666
            sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml
            """
        ],
        # env level
        "env_setup": [
            r"""
            git fetch origin pull/1666/head:pr-1666
            git checkout main
            git cherry-pick -X theirs pr-1666
            git branch -D pr-1666
            """
        ],
    }
    for k in ["0.8"]
}

SPECS_ASTERINAS.update(
    {
        k:{
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.9.4",
            "env_setup":[
                "git fetch origin pull/1666/head:pr-1666",
                "git checkout main",
                "git cherry-pick -X theirs pr-1666",
                # "git cherry-pick pr-1666",
                "git branch -D pr-1666",
                
            ],
            "pre_install":[
                # r"""sed -i 's/channel = "nightly-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}"/channel = "nightly-2024-10-12"/' rust-toolchain.toml"""
                # "git fetch origin pull/1666/head:pr-1666",
                # "git checkout main",
                # "git cherry-pick pr-1666",
                # "git branch -D pr-1666"
            ]
        }
        for k in ["0.9"]
    }
)


SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.7.0",
            # repo level
            "pre_install": [
                r"""
            sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml
            """
            ],
            # env level
            "env_setup": [
                r"""
            sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml

            """
            ],
        }
        for k in ["0.7"]
    }
)
SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.6.2",
            # repo level
            "pre_install": [
                r"""
            git fetch origin pull/1666/head:pr-1666
            git checkout main
            git cherry-pick -X theirs pr-1666
            git branch -D pr-1666
            sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
            sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml
            sed -i 's/target_arch == "x86_64-unknown-none"/target_arch == "x86_64-unknown-linux-gnu"/' ostd/libs/linux-bzimage/setup/build.rs
            cargo update -p unwinding
            sed '/^\[target\.x86_64-unknown-none\.dependencies\]$/d' ostd/libs/linux-bzimage/setup/Cargo.toml
            """
            ],
            # env level
            "env_setup": [
                r"""
            git fetch origin pull/1666/head:pr-1666
            git checkout main
            git cherry-pick -X theirs pr-1666
            git branch -D pr-1666
            sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
            sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml
            sed -i 's/target_arch == "x86_64-unknown-none"/target_arch == "x86_64-unknown-linux-gnu"/' ostd/libs/linux-bzimage/setup/build.rs
            cargo update -p unwinding
            """
            ],
        }
        for k in ["0.6"]
    }
)
SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.5.1",
            "pre_install": [
                r"""
            # sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
            # sed -i 's/multiboot2 = "0.20.2"/multiboot2 = "0.23.1"/' ostd/Cargo.toml
            # cargo update -p unwinding

            """
            ],
            # env level
            "env_setup": [
                r"""
export CFLAGS="-DSECOMP FILTER FLAG WAIT KILLABLE RECV=32 -DMFD NOEXEC SEAL=8 -DMFD EXEC=16 -DNF NETDEV EGRESS=1"
echo $CFLAGS

            """
            ],
        }
        for k in ["0.5"]
    }
)
SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.4.2",
            # #repo level
            "pre_install":[
                r"""
                # git fetch origin pull/1666/head:pr-1666
                # git checkout main
                # git cherry-pick -X theirs pr-1666
                # git branch -D pr-1666
                sed -i 's/channel = "nightly-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
                sed -i 's/multiboot2 = "[0-9]*\.[0-9]*\.[0-9]*"/multiboot2 = "0.23.1"/' framework/aster-frame/Cargo.toml
                sed -i 's/x86_64 = "[0-9]*\.[0-9]*\.[0-9]*"/x86_64 = "0.14.13"/' kernel/Cargo.toml
                cargo update -p unwinding
        
                """
            ],
            #env level
            "env_setup":[
                r"""
                # git fetch origin pull/1666/head:pr-1666
                # git checkout main
                # git cherry-pick -X theirs pr-1666
                # git branch -D pr-1666
                # sed -i 's/channel = "nightly-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
                # sed -i 's/channel = "nightly-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}"/channel = "nightly-2024-11-29"/' rust-toolchain.toml
                sed -i 's/multiboot2 = "[0-9]*\.[0-9]*\.[0-9]*"/multiboot2 = "0.23.1"/' framework/aster-frame/Cargo.toml
                # sed -i 's/x86_64 = "[0-9]*\.[0-9]*\.[0-9]*"/x86_64 = "0.14.13"/' kernel/Cargo.toml
                # sed -i 's#multiboot2 = "[0-9]*\.[0-9]*\.[0-9]*"#multiboot2 = {path="multiboot2-multiboot2-v0.16.0/multiboot2-multiboot2-v0.16.0/multiboot2"}#' framework/aster-frame/Cargo.toml

                """
            ]
        }
        for k in ["0.4"]
    }
)
SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.2.2",
            # #repo level
            # "pre_install":[
            #     r"""
            #     sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-10-12"/' rust-toolchain.toml
            #     """
            # ],
            # #env level
            # "env_setup":[
            #     r"""sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-10-12"/' rust-toolchain.toml"""
            # ]
        }
        for k in ["0.2"]
    }
)
SPECS_ASTERINAS.update(
    {
        k: {
            "rustc": "1.81.0",
            "test_cmd": TEST_CARGO,
            "image_tag": "0.1.1",
            # #repo level
            # "pre_install":[
            #     r"""
            #     sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-10-12"/' rust-toolchain.toml
            #     """
            # ],
            # #env level
            # "env_setup":[
            #     r"""sed -i 's/channel = "nightly-2024-06-20"/channel = "nightly-2024-10-12"/' rust-toolchain.toml"""
            # ]
        }
        for k in ["0.1"]
    }
)

SPECS_TOKIO = {
    k: {
        "rustc": "1.81.0",
        "pre_install": [
            r"sed -i 's/#!\[deny(unused_must_use)\]/#![warn(unused_must_use)]/' ./tokio/src/lib.rs",
        ]
    }
    for k in
    ["1.9", "1.8", "1.7", "1.6", "1.5", "1.41", "1.40", "1.4", "1.39", "1.38", "1.37", "1.36", "1.35", "1.34", "1.33",
     "1.32", "1.31", "1.3", "1.29", "1.28", "1.26", "1.25", "1.24", "1.23", "1.22", "1.21", "1.20", "1.17", "1.16",
     "1.15", "1.14", "1.12", "1.11", "1.1", "1.0", "0.3"]
}

SPECS_TOKIO.update({
    k: {
        "rustc": "1.81.0",
        "pre_install": [
            r"sed -i 's/#!\[deny(unused_must_use)\]/#![warn(unused_must_use)]/' ./tokio/src/lib.rs",
            "set +e",
            r"sed -E -i 's/nightly-2019[a-zA-Z0-9_\-]+/1.81.0/' ./rust-toolchain",
            "sed -i 's/security-framework = \"0.2\"/security-framework = \"3.0.0-beta.2\"/' ./tokio-tls/Cargo.toml",
            "set -e",
        ]
    }
    for k in
    ["0.2"]
})


# Constants - Repo Test Features
FEATURES_ARROW = {
    # instance id
    "apache__arrow-rs-6368": {
        # integration test file name(without extension)
        "pyarrow": {
            # install feature dependencies
            "install": [
                "pip install pyarrow",
            ],
            # cargo test feature names(in Cargo.toml or in error text)
            "features": ["pyarrow"],
        }
    },
    "apache__arrow-rs-5319": {"arithmetic": {"features": ["chrono-tz"]}},
    **{
        instance_id: {"array_cast": {"features": ["chrono-tz"]}}
        for instance_id in [
            "apache__arrow-rs-3673",
            "apache__arrow-rs-3238",
            "apache__arrow-rs-3542",
            "apache__arrow-rs-3222",
        ]
    },
    **{
        instance_id: {"array_cast": {"features": ["chrono-tz", "prettyprint"]}}
        for instance_id in [
            "apache__arrow-rs-6453",
            "apache__arrow-rs-5769",
            "apache__arrow-rs-5065",
            "apache__arrow-rs-4201",
            "apache__arrow-rs-3994",
            "apache__arrow-rs-3961",
        ]
    },
    **{
        instance_id: {
            "flight_sql_client_cli": {
                "features": ["cli", "flight-sql-experimental", "tls"]
            }
        }
        for instance_id in [
            "apache__arrow-rs-6332",
            "apache__arrow-rs-5474",
            "apache__arrow-rs-4797",
            "apache__arrow-rs-4250",
            "apache__arrow-rs-4055",
            "apache__arrow-rs-3816",
        ]
    },
    **{
        instance_id: {"csv": {"features": ["csv", "chrono-tz"]}}
        for instance_id in ["apache__arrow-rs-4909", "apache__arrow-rs-3514"]
    },
}

# Constants - Task Instance Test Features
MAP_REPO_ID_TO_FEATURES = {"apache/arrow-rs": FEATURES_ARROW}

# Constants - Task Instance Instllation Environment
MAP_REPO_VERSION_TO_SPECS = {
    "rust-lang/rustlings": SPECS_RUSTLINGS,
    "serde-rs/serde": SPECS_SERDE,
    "bitflags/bitflags": SPECS_BITFLAGS,
    "apache/arrow-rs": SPECS_ARROW,
    "asterinas/asterinas": SPECS_ASTERINAS,
}

# Constants - Repository Specific Installation Instructions
MAP_REPO_TO_INSTALL = {}


# Constants - Task Instance Requirements File Paths
MAP_REPO_TO_REQS_PATHS = {
    "bitflags/bitflags": "Cargo.toml",
    "apache/arrow-rs": "Cargo.toml",
    "asterinas/asterinas": "Cargo.toml",
    "tokio-rs/tokio": "Cargo.toml",
}


# Constants - Task Instance environment.yml File Paths
MAP_REPO_TO_ENV_YML_PATHS = {
    "matplotlib/matplotlib": ["environment.yml"],
    "pydata/xarray": ["ci/requirements/environment.yml", "environment.yml"],
}

# Constants - Evaluation Keys
KEY_INSTANCE_ID = "instance_id"
KEY_MODEL = "model_name_or_path"
KEY_PREDICTION = "model_patch"


# Constants - Logging
APPLY_PATCH_FAIL = ">>>>> Patch Apply Failed"
APPLY_PATCH_PASS = ">>>>> Applied Patch"
INSTALL_FAIL = ">>>>> Init Failed"
INSTALL_PASS = ">>>>> Init Succeeded"
INSTALL_TIMEOUT = ">>>>> Init Timed Out"
RESET_FAILED = ">>>>> Reset Failed"
TESTS_ERROR = ">>>>> Tests Errored"
TESTS_FAILED = ">>>>> Some Tests Failed"
TESTS_PASSED = ">>>>> All Tests Passed"
TESTS_TIMEOUT = ">>>>> Tests Timed Out"


# Constants - Patch Types
class PatchType(Enum):
    PATCH_GOLD = "gold"
    PATCH_PRED = "pred"
    PATCH_PRED_TRY = "pred_try"
    PATCH_PRED_MINIMAL = "pred_minimal"
    PATCH_PRED_MINIMAL_TRY = "pred_minimal_try"
    PATCH_TEST = "test"

    def __str__(self):
        return self.value


# Constants - Miscellaneous
NON_TEST_EXTS = [
    ".json",
    ".png",
    "csv",
    ".txt",
    ".md",
    ".jpg",
    ".jpeg",
    ".pkl",
    ".yml",
    ".yaml",
    ".toml",
]
SWE_BENCH_URL_RAW = "https://raw.githubusercontent.com/"
USE_X86 = {
    "astropy__astropy-7973",
    "django__django-10087",
    "django__django-10097",
    "django__django-10213",
    "django__django-10301",
    "django__django-10316",
    "django__django-10426",
    "django__django-11383",
    "django__django-12185",
    "django__django-12497",
    "django__django-13121",
    "django__django-13417",
    "django__django-13431",
    "django__django-13447",
    "django__django-14155",
    "django__django-14164",
    "django__django-14169",
    "django__django-14170",
    "django__django-15180",
    "django__django-15199",
    "django__django-15280",
    "django__django-15292",
    "django__django-15474",
    "django__django-15682",
    "django__django-15689",
    "django__django-15695",
    "django__django-15698",
    "django__django-15781",
    "django__django-15925",
    "django__django-15930",
    "django__django-5158",
    "django__django-5470",
    "django__django-7188",
    "django__django-7475",
    "django__django-7530",
    "django__django-8326",
    "django__django-8961",
    "django__django-9003",
    "django__django-9703",
    "django__django-9871",
    "matplotlib__matplotlib-13983",
    "matplotlib__matplotlib-13984",
    "matplotlib__matplotlib-13989",
    "matplotlib__matplotlib-14043",
    "matplotlib__matplotlib-14471",
    "matplotlib__matplotlib-22711",
    "matplotlib__matplotlib-22719",
    "matplotlib__matplotlib-22734",
    "matplotlib__matplotlib-22767",
    "matplotlib__matplotlib-22815",
    "matplotlib__matplotlib-22835",
    "matplotlib__matplotlib-22865",
    "matplotlib__matplotlib-22871",
    "matplotlib__matplotlib-22883",
    "matplotlib__matplotlib-22926",
    "matplotlib__matplotlib-22929",
    "matplotlib__matplotlib-22931",
    "matplotlib__matplotlib-22945",
    "matplotlib__matplotlib-22991",
    "matplotlib__matplotlib-23031",
    "matplotlib__matplotlib-23047",
    "matplotlib__matplotlib-23049",
    "matplotlib__matplotlib-23057",
    "matplotlib__matplotlib-23088",
    "matplotlib__matplotlib-23111",
    "matplotlib__matplotlib-23140",
    "matplotlib__matplotlib-23174",
    "matplotlib__matplotlib-23188",
    "matplotlib__matplotlib-23198",
    "matplotlib__matplotlib-23203",
    "matplotlib__matplotlib-23266",
    "matplotlib__matplotlib-23267",
    "matplotlib__matplotlib-23288",
    "matplotlib__matplotlib-23299",
    "matplotlib__matplotlib-23314",
    "matplotlib__matplotlib-23332",
    "matplotlib__matplotlib-23348",
    "matplotlib__matplotlib-23412",
    "matplotlib__matplotlib-23476",
    "matplotlib__matplotlib-23516",
    "matplotlib__matplotlib-23562",
    "matplotlib__matplotlib-23563",
    "matplotlib__matplotlib-23573",
    "matplotlib__matplotlib-23740",
    "matplotlib__matplotlib-23742",
    "matplotlib__matplotlib-23913",
    "matplotlib__matplotlib-23964",
    "matplotlib__matplotlib-23987",
    "matplotlib__matplotlib-24013",
    "matplotlib__matplotlib-24026",
    "matplotlib__matplotlib-24088",
    "matplotlib__matplotlib-24111",
    "matplotlib__matplotlib-24149",
    "matplotlib__matplotlib-24177",
    "matplotlib__matplotlib-24189",
    "matplotlib__matplotlib-24224",
    "matplotlib__matplotlib-24250",
    "matplotlib__matplotlib-24257",
    "matplotlib__matplotlib-24265",
    "matplotlib__matplotlib-24334",
    "matplotlib__matplotlib-24362",
    "matplotlib__matplotlib-24403",
    "matplotlib__matplotlib-24431",
    "matplotlib__matplotlib-24538",
    "matplotlib__matplotlib-24570",
    "matplotlib__matplotlib-24604",
    "matplotlib__matplotlib-24619",
    "matplotlib__matplotlib-24627",
    "matplotlib__matplotlib-24637",
    "matplotlib__matplotlib-24691",
    "matplotlib__matplotlib-24749",
    "matplotlib__matplotlib-24768",
    "matplotlib__matplotlib-24849",
    "matplotlib__matplotlib-24870",
    "matplotlib__matplotlib-24912",
    "matplotlib__matplotlib-24924",
    "matplotlib__matplotlib-24970",
    "matplotlib__matplotlib-24971",
    "matplotlib__matplotlib-25027",
    "matplotlib__matplotlib-25052",
    "matplotlib__matplotlib-25079",
    "matplotlib__matplotlib-25085",
    "matplotlib__matplotlib-25122",
    "matplotlib__matplotlib-25126",
    "matplotlib__matplotlib-25129",
    "matplotlib__matplotlib-25238",
    "matplotlib__matplotlib-25281",
    "matplotlib__matplotlib-25287",
    "matplotlib__matplotlib-25311",
    "matplotlib__matplotlib-25332",
    "matplotlib__matplotlib-25334",
    "matplotlib__matplotlib-25340",
    "matplotlib__matplotlib-25346",
    "matplotlib__matplotlib-25404",
    "matplotlib__matplotlib-25405",
    "matplotlib__matplotlib-25425",
    "matplotlib__matplotlib-25430",
    "matplotlib__matplotlib-25433",
    "matplotlib__matplotlib-25442",
    "matplotlib__matplotlib-25479",
    "matplotlib__matplotlib-25498",
    "matplotlib__matplotlib-25499",
    "matplotlib__matplotlib-25515",
    "matplotlib__matplotlib-25547",
    "matplotlib__matplotlib-25551",
    "matplotlib__matplotlib-25565",
    "matplotlib__matplotlib-25624",
    "matplotlib__matplotlib-25631",
    "matplotlib__matplotlib-25640",
    "matplotlib__matplotlib-25651",
    "matplotlib__matplotlib-25667",
    "matplotlib__matplotlib-25712",
    "matplotlib__matplotlib-25746",
    "matplotlib__matplotlib-25772",
    "matplotlib__matplotlib-25775",
    "matplotlib__matplotlib-25779",
    "matplotlib__matplotlib-25785",
    "matplotlib__matplotlib-25794",
    "matplotlib__matplotlib-25859",
    "matplotlib__matplotlib-25960",
    "matplotlib__matplotlib-26011",
    "matplotlib__matplotlib-26020",
    "matplotlib__matplotlib-26024",
    "matplotlib__matplotlib-26078",
    "matplotlib__matplotlib-26089",
    "matplotlib__matplotlib-26101",
    "matplotlib__matplotlib-26113",
    "matplotlib__matplotlib-26122",
    "matplotlib__matplotlib-26160",
    "matplotlib__matplotlib-26184",
    "matplotlib__matplotlib-26208",
    "matplotlib__matplotlib-26223",
    "matplotlib__matplotlib-26232",
    "matplotlib__matplotlib-26249",
    "matplotlib__matplotlib-26278",
    "matplotlib__matplotlib-26285",
    "matplotlib__matplotlib-26291",
    "matplotlib__matplotlib-26300",
    "matplotlib__matplotlib-26311",
    "matplotlib__matplotlib-26341",
    "matplotlib__matplotlib-26342",
    "matplotlib__matplotlib-26399",
    "matplotlib__matplotlib-26466",
    "matplotlib__matplotlib-26469",
    "matplotlib__matplotlib-26472",
    "matplotlib__matplotlib-26479",
    "matplotlib__matplotlib-26532",
    "pydata__xarray-2905",
    "pydata__xarray-2922",
    "pydata__xarray-3095",
    "pydata__xarray-3114",
    "pydata__xarray-3151",
    "pydata__xarray-3156",
    "pydata__xarray-3159",
    "pydata__xarray-3239",
    "pydata__xarray-3302",
    "pydata__xarray-3305",
    "pydata__xarray-3338",
    "pydata__xarray-3364",
    "pydata__xarray-3406",
    "pydata__xarray-3520",
    "pydata__xarray-3527",
    "pydata__xarray-3631",
    "pydata__xarray-3635",
    "pydata__xarray-3637",
    "pydata__xarray-3649",
    "pydata__xarray-3677",
    "pydata__xarray-3733",
    "pydata__xarray-3812",
    "pydata__xarray-3905",
    "pydata__xarray-3976",
    "pydata__xarray-3979",
    "pydata__xarray-3993",
    "pydata__xarray-4075",
    "pydata__xarray-4094",
    "pydata__xarray-4098",
    "pydata__xarray-4182",
    "pydata__xarray-4184",
    "pydata__xarray-4248",
    "pydata__xarray-4339",
    "pydata__xarray-4356",
    "pydata__xarray-4419",
    "pydata__xarray-4423",
    "pydata__xarray-4442",
    "pydata__xarray-4493",
    "pydata__xarray-4510",
    "pydata__xarray-4629",
    "pydata__xarray-4683",
    "pydata__xarray-4684",
    "pydata__xarray-4687",
    "pydata__xarray-4695",
    "pydata__xarray-4750",
    "pydata__xarray-4758",
    "pydata__xarray-4759",
    "pydata__xarray-4767",
    "pydata__xarray-4802",
    "pydata__xarray-4819",
    "pydata__xarray-4827",
    "pydata__xarray-4879",
    "pydata__xarray-4911",
    "pydata__xarray-4939",
    "pydata__xarray-4940",
    "pydata__xarray-4966",
    "pydata__xarray-4994",
    "pydata__xarray-5033",
    "pydata__xarray-5126",
    "pydata__xarray-5131",
    "pydata__xarray-5180",
    "pydata__xarray-5187",
    "pydata__xarray-5233",
    "pydata__xarray-5362",
    "pydata__xarray-5365",
    "pydata__xarray-5455",
    "pydata__xarray-5580",
    "pydata__xarray-5662",
    "pydata__xarray-5682",
    "pydata__xarray-5731",
    "pydata__xarray-6135",
    "pydata__xarray-6386",
    "pydata__xarray-6394",
    "pydata__xarray-6400",
    "pydata__xarray-6461",
    "pydata__xarray-6548",
    "pydata__xarray-6598",
    "pydata__xarray-6599",
    "pydata__xarray-6601",
    "pydata__xarray-6721",
    "pydata__xarray-6744",
    "pydata__xarray-6798",
    "pydata__xarray-6804",
    "pydata__xarray-6823",
    "pydata__xarray-6857",
    "pydata__xarray-6882",
    "pydata__xarray-6889",
    "pydata__xarray-6938",
    "pydata__xarray-6971",
    "pydata__xarray-6992",
    "pydata__xarray-6999",
    "pydata__xarray-7003",
    "pydata__xarray-7019",
    "pydata__xarray-7052",
    "pydata__xarray-7089",
    "pydata__xarray-7101",
    "pydata__xarray-7105",
    "pydata__xarray-7112",
    "pydata__xarray-7120",
    "pydata__xarray-7147",
    "pydata__xarray-7150",
    "pydata__xarray-7179",
    "pydata__xarray-7203",
    "pydata__xarray-7229",
    "pydata__xarray-7233",
    "pydata__xarray-7347",
    "pydata__xarray-7391",
    "pydata__xarray-7393",
    "pydata__xarray-7400",
    "pydata__xarray-7444",
    "pytest-dev__pytest-10482",
    "scikit-learn__scikit-learn-10198",
    "scikit-learn__scikit-learn-10297",
    "scikit-learn__scikit-learn-10306",
    "scikit-learn__scikit-learn-10331",
    "scikit-learn__scikit-learn-10377",
    "scikit-learn__scikit-learn-10382",
    "scikit-learn__scikit-learn-10397",
    "scikit-learn__scikit-learn-10427",
    "scikit-learn__scikit-learn-10428",
    "scikit-learn__scikit-learn-10443",
    "scikit-learn__scikit-learn-10452",
    "scikit-learn__scikit-learn-10459",
    "scikit-learn__scikit-learn-10471",
    "scikit-learn__scikit-learn-10483",
    "scikit-learn__scikit-learn-10495",
    "scikit-learn__scikit-learn-10508",
    "scikit-learn__scikit-learn-10558",
    "scikit-learn__scikit-learn-10577",
    "scikit-learn__scikit-learn-10581",
    "scikit-learn__scikit-learn-10687",
    "scikit-learn__scikit-learn-10774",
    "scikit-learn__scikit-learn-10777",
    "scikit-learn__scikit-learn-10803",
    "scikit-learn__scikit-learn-10844",
    "scikit-learn__scikit-learn-10870",
    "scikit-learn__scikit-learn-10881",
    "scikit-learn__scikit-learn-10899",
    "scikit-learn__scikit-learn-10908",
    "scikit-learn__scikit-learn-10913",
    "scikit-learn__scikit-learn-10949",
    "scikit-learn__scikit-learn-10982",
    "scikit-learn__scikit-learn-10986",
    "scikit-learn__scikit-learn-11040",
    "scikit-learn__scikit-learn-11042",
    "scikit-learn__scikit-learn-11043",
    "scikit-learn__scikit-learn-11151",
    "scikit-learn__scikit-learn-11160",
    "scikit-learn__scikit-learn-11206",
    "scikit-learn__scikit-learn-11235",
    "scikit-learn__scikit-learn-11243",
    "scikit-learn__scikit-learn-11264",
    "scikit-learn__scikit-learn-11281",
    "scikit-learn__scikit-learn-11310",
    "scikit-learn__scikit-learn-11315",
    "scikit-learn__scikit-learn-11333",
    "scikit-learn__scikit-learn-11346",
    "scikit-learn__scikit-learn-11391",
    "scikit-learn__scikit-learn-11496",
    "scikit-learn__scikit-learn-11542",
    "scikit-learn__scikit-learn-11574",
    "scikit-learn__scikit-learn-11578",
    "scikit-learn__scikit-learn-11585",
    "scikit-learn__scikit-learn-11596",
    "scikit-learn__scikit-learn-11635",
    "scikit-learn__scikit-learn-12258",
    "scikit-learn__scikit-learn-12421",
    "scikit-learn__scikit-learn-12443",
    "scikit-learn__scikit-learn-12462",
    "scikit-learn__scikit-learn-12471",
    "scikit-learn__scikit-learn-12486",
    "scikit-learn__scikit-learn-12557",
    "scikit-learn__scikit-learn-12583",
    "scikit-learn__scikit-learn-12585",
    "scikit-learn__scikit-learn-12625",
    "scikit-learn__scikit-learn-12626",
    "scikit-learn__scikit-learn-12656",
    "scikit-learn__scikit-learn-12682",
    "scikit-learn__scikit-learn-12704",
    "scikit-learn__scikit-learn-12733",
    "scikit-learn__scikit-learn-12758",
    "scikit-learn__scikit-learn-12760",
    "scikit-learn__scikit-learn-12784",
    "scikit-learn__scikit-learn-12827",
    "scikit-learn__scikit-learn-12834",
    "scikit-learn__scikit-learn-12860",
    "scikit-learn__scikit-learn-12908",
    "scikit-learn__scikit-learn-12938",
    "scikit-learn__scikit-learn-12961",
    "scikit-learn__scikit-learn-12973",
    "scikit-learn__scikit-learn-12983",
    "scikit-learn__scikit-learn-12989",
    "scikit-learn__scikit-learn-13010",
    "scikit-learn__scikit-learn-13013",
    "scikit-learn__scikit-learn-13017",
    "scikit-learn__scikit-learn-13046",
    "scikit-learn__scikit-learn-13087",
    "scikit-learn__scikit-learn-13124",
    "scikit-learn__scikit-learn-13135",
    "scikit-learn__scikit-learn-13142",
    "scikit-learn__scikit-learn-13143",
    "scikit-learn__scikit-learn-13157",
    "scikit-learn__scikit-learn-13165",
    "scikit-learn__scikit-learn-13174",
    "scikit-learn__scikit-learn-13221",
    "scikit-learn__scikit-learn-13241",
    "scikit-learn__scikit-learn-13253",
    "scikit-learn__scikit-learn-13280",
    "scikit-learn__scikit-learn-13283",
    "scikit-learn__scikit-learn-13302",
    "scikit-learn__scikit-learn-13313",
    "scikit-learn__scikit-learn-13328",
    "scikit-learn__scikit-learn-13333",
    "scikit-learn__scikit-learn-13363",
    "scikit-learn__scikit-learn-13368",
    "scikit-learn__scikit-learn-13392",
    "scikit-learn__scikit-learn-13436",
    "scikit-learn__scikit-learn-13439",
    "scikit-learn__scikit-learn-13447",
    "scikit-learn__scikit-learn-13454",
    "scikit-learn__scikit-learn-13467",
    "scikit-learn__scikit-learn-13472",
    "scikit-learn__scikit-learn-13485",
    "scikit-learn__scikit-learn-13496",
    "scikit-learn__scikit-learn-13497",
    "scikit-learn__scikit-learn-13536",
    "scikit-learn__scikit-learn-13549",
    "scikit-learn__scikit-learn-13554",
    "scikit-learn__scikit-learn-13584",
    "scikit-learn__scikit-learn-13618",
    "scikit-learn__scikit-learn-13620",
    "scikit-learn__scikit-learn-13628",
    "scikit-learn__scikit-learn-13641",
    "scikit-learn__scikit-learn-13704",
    "scikit-learn__scikit-learn-13726",
    "scikit-learn__scikit-learn-13779",
    "scikit-learn__scikit-learn-13780",
    "scikit-learn__scikit-learn-13828",
    "scikit-learn__scikit-learn-13864",
    "scikit-learn__scikit-learn-13877",
    "scikit-learn__scikit-learn-13910",
    "scikit-learn__scikit-learn-13915",
    "scikit-learn__scikit-learn-13933",
    "scikit-learn__scikit-learn-13960",
    "scikit-learn__scikit-learn-13974",
    "scikit-learn__scikit-learn-13983",
    "scikit-learn__scikit-learn-14012",
    "scikit-learn__scikit-learn-14024",
    "scikit-learn__scikit-learn-14053",
    "scikit-learn__scikit-learn-14067",
    "scikit-learn__scikit-learn-14087",
    "scikit-learn__scikit-learn-14092",
    "scikit-learn__scikit-learn-14114",
    "scikit-learn__scikit-learn-14125",
    "scikit-learn__scikit-learn-14141",
    "scikit-learn__scikit-learn-14237",
    "scikit-learn__scikit-learn-14309",
    "scikit-learn__scikit-learn-14430",
    "scikit-learn__scikit-learn-14450",
    "scikit-learn__scikit-learn-14458",
    "scikit-learn__scikit-learn-14464",
    "scikit-learn__scikit-learn-14496",
    "scikit-learn__scikit-learn-14520",
    "scikit-learn__scikit-learn-14544",
    "scikit-learn__scikit-learn-14591",
    "scikit-learn__scikit-learn-14629",
    "scikit-learn__scikit-learn-14704",
    "scikit-learn__scikit-learn-14706",
    "scikit-learn__scikit-learn-14710",
    "scikit-learn__scikit-learn-14732",
    "scikit-learn__scikit-learn-14764",
    "scikit-learn__scikit-learn-14806",
    "scikit-learn__scikit-learn-14869",
    "scikit-learn__scikit-learn-14878",
    "scikit-learn__scikit-learn-14890",
    "scikit-learn__scikit-learn-14894",
    "scikit-learn__scikit-learn-14898",
    "scikit-learn__scikit-learn-14908",
    "scikit-learn__scikit-learn-14983",
    "scikit-learn__scikit-learn-14999",
    "scikit-learn__scikit-learn-15028",
    "scikit-learn__scikit-learn-15084",
    "scikit-learn__scikit-learn-15086",
    "scikit-learn__scikit-learn-15094",
    "scikit-learn__scikit-learn-15096",
    "scikit-learn__scikit-learn-15100",
    "scikit-learn__scikit-learn-15119",
    "scikit-learn__scikit-learn-15120",
    "scikit-learn__scikit-learn-15138",
    "scikit-learn__scikit-learn-15393",
    "scikit-learn__scikit-learn-15495",
    "scikit-learn__scikit-learn-15512",
    "scikit-learn__scikit-learn-15524",
    "scikit-learn__scikit-learn-15535",
    "scikit-learn__scikit-learn-15625",
    "scikit-learn__scikit-learn-3840",
    "scikit-learn__scikit-learn-7760",
    "scikit-learn__scikit-learn-8554",
    "scikit-learn__scikit-learn-9274",
    "scikit-learn__scikit-learn-9288",
    "scikit-learn__scikit-learn-9304",
    "scikit-learn__scikit-learn-9775",
    "scikit-learn__scikit-learn-9939",
    "sphinx-doc__sphinx-11311",
    "sphinx-doc__sphinx-7910",
    "sympy__sympy-12812",
    "sympy__sympy-14248",
    "sympy__sympy-15222",
    "sympy__sympy-19201",
}
