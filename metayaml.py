#!/usr/bin/env python

#
# Collect meta data attributes of files or directories stored in meta.yml files
# More specific attributes override those from its parent directories
#

import click
import yaml
import os
from pathlib import Path
import logging
from cachetools import cached, TTLCache
from datetime import datetime, timedelta

def merge(a, b, key = None):
    if a is not None and b is None:
        return a
    elif b is not None and a is None:
        return b
    else:
        logging.info(f"overwrite {key} from '{b}' to '{a}'")
        return a

@cached(cache=TTLCache(maxsize=1e6, ttl=timedelta(hours=1), timer=datetime.now))
def get_meta_data(path):
    yml_paths = []
    if os.path.isfile(path):
        yml_paths = [os.path.abspath(path) + ".yml"]
    else:
        yml_paths = [os.path.abspath(path) + "/meta.yml"]

    yml_paths += [os.path.abspath(path) + ".yaml"]
    yml_paths += [os.path.abspath(path) + ".meta.yml"]
    yml_paths += [os.path.abspath(path) + ".meta.yaml"]

    yml_paths += [f"{x}/meta.yml" for x in Path(os.path.abspath(path)).parents]
    yml_paths += [f"{x}/meta.yaml" for x in Path(os.path.abspath(path)).parents]

    yml_paths = [x for x in yml_paths if os.path.exists(x)]
    yml_paths.reverse() # child overrides parent

    d = {}
    for yml_path in yml_paths:        
        with open(yml_path, "r") as f:
            cur_d = yaml.safe_load(f)
            keys = set((*d.keys(), *cur_d.keys()))
            d = {k: merge(cur_d.get(k), d.get(k), k)  for k in keys}
    return d

@click.group()
def main():
    logging.basicConfig(filename="/dev/stderr", encoding="utf-8", level=logging.DEBUG)

@main.command()
@click.argument("key")
@click.argument("value")
@click.option("--directory", "-d", default=".")
def find(key, value, directory):
    """
    Find files and directories based on a specific attribute stored in YAML meta data sidecar files.
    """
    logging.info("Meta data for files is not yet implemented")

    for path in Path(directory).rglob("*meta.yml"):
        m = get_meta_data(path)
        if m[key] == value:
            print(path.parents[0])
    

@main.command()
@click.argument("path", type=click.Path(exists=True)) 
def get(path):
    """
    Retrieves attributes of a directory or file based on YAML meta data sidecar files.
    """
    d = get_meta_data(path)
    print(yaml.dump(d))

if __name__ == '__main__':
    main()
