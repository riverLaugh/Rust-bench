
import argparse
import json
import logging
import os

from datetime import datetime
from fastcore.xtras import obj2dict
from swebench.collect.utils import Repo
from typing import Optional


repo_name = 'rust-lang/rustlings'

token = os.environ.get("GITHUB_TOKENS")
owner, repo = repo_name.split("/")
print("owner",owner)
print("repo",repo)
repo = Repo(owner=owner, repo = repo, token=token)
api = repo.api

# repo_info = api.repos.get(owner="rust-lang", repo="rustlings")
# print(repo_info)

repo.get_specific_pulls([184])