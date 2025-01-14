# IF you change the base image, you need to rebuild all images (run with --force_rebuild)
_DOCKERFILE_BASE = r"""
FROM --platform={platform} ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

ENV RUSTUP_DIST_SERVER=https://mirror.sjtu.edu.cn/rust-static
ENV RUSTUP_UPDATE_ROOT=https://mirror.sjtu.edu.cn/rust-static/rustup

RUN mkdir -p ~/.cargo && \
    cat <<EOF > ~/.cargo/config
[source.crates-io]
replace-with = "sjtu"

[source.tuna]
registry = "https://mirrors.tuna.tsinghua.edu.cn/crates.io-index"

# 中国科学技术大学
[source.ustc]
registry = "git://mirrors.ustc.edu.cn/crates.io-index"

# 上海交通大学
[source.sjtu]
registry = "https://mirrors.sjtug.sjtu.edu.cn/git/crates.io-index"

# rustcc社区
[source.rustcc]
registry = "git://crates.rustcc.cn/crates.io-index"
EOF



RUN apt update && apt install -y \
wget \
git \
build-essential \
libffi-dev \
libtiff-dev \
jq \
curl \
locales \
locales-all \
tzdata \
libssl-dev\
&& rm -rf /var/lib/apt/lists/*

RUN apt install -y libssl-dev

# 安装 Rustup 和指定的 Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH=/root/.cargo/bin:$PATH

# 设置 Rust 默认版本，可以使用 'stable', 'beta', 'nightly' 或具体版本号如 '1.67.0'
RUN rustup default nightly
RUN rustup default 1.81.0

RUN adduser --disabled-password --gecos 'dog' nonroot

# 安装常见软件包
RUN apt-get update
RUN apt-get install pkg-config -y
RUN apt-get install python3-pip -y
RUN apt-get install cmake -y
RUN apt-get install protobuf-compiler -y

"""

_DOCKERFILE_ENV = r"""FROM --platform={platform} sweb.base.{arch}:latest

COPY ./setup_env.sh /root/
RUN chmod +x /root/setup_env.sh
RUN /bin/bash -c "source ~/.bashrc && /root/setup_env.sh"
WORKDIR /testbed/

# Automatically activate the testbed environment
# RUN echo "source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed" > /root/.bashrc
"""

_DOCKERFILE_ENV_asterinas = r"""
FROM --platform={platform} asterinas/asterinas:{tag}
ENV HTTPS_PROXY=http://172.24.16.1:7899
ENV HTTP_PROXY=http://172.24.16.1:7899

# ENV RUSTUP_DIST_SERVER=https://mirrors.tuna.tsinghua.edu.cn/rustup
# ENV RUSTUP_UPDATE_ROOT=https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup

ENV RUSTUP_DIST_SERVER=https://mirror.sjtu.edu.cn/rust-static
ENV RUSTUP_UPDATE_ROOT=https://mirror.sjtu.edu.cn/rust-static/rustup

RUN mkdir -p ~/.cargo && \
    cat <<EOF > ~/.cargo/config
[source.crates-io]
replace-with = "sjtu"

[source.tuna]
registry = "https://mirrors.tuna.tsinghua.edu.cn/crates.io-index"

# 中国科学技术大学
[source.ustc]
registry = "git://mirrors.ustc.edu.cn/crates.io-index"

# 上海交通大学
[source.sjtu]
registry = "https://mirrors.sjtug.sjtu.edu.cn/git/crates.io-index"

# rustcc社区
[source.rustcc]
registry = "git://crates.rustcc.cn/crates.io-index"
EOF

RUN git config --global user.name "riverLaugh" \
    && git config --global user.email "2314398305@qq.com"
COPY ./setup_env.sh /root/
RUN chmod +x /root/setup_env.sh
RUN /bin/bash -c "source ~/.bashrc && /root/setup_env.sh"
"""

_DOCKERFILE_INSTANCE = r"""FROM --platform={platform} {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""


def get_dockerfile_base(platform, arch):
    if arch == "arm64":
        conda_arch = "aarch64"
    else:
        conda_arch = arch
    return _DOCKERFILE_BASE.format(platform=platform, conda_arch=conda_arch)


def get_dockerfile_env(platform, arch):
    return _DOCKERFILE_ENV.format(platform=platform, arch=arch)


def get_dockerfile_instance(platform, env_image_name):
    return _DOCKERFILE_INSTANCE.format(platform=platform, env_image_name=env_image_name)


def get_dockerfile_env_asterinas(platform, tag):
    return _DOCKERFILE_ENV_asterinas.format(platform=platform, tag=tag)