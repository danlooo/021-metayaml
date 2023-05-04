#!/usr/bin/env python

#
# Collect meta data attributes of files or directories stored in meta.yml files
# More specific attributes override those from its parent directories
#

import click
import yaml
import os
from subprocess import Popen
from pathlib import Path
import logging
from cachetools import cached, TTLCache
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile


def parse_string(s):
    if s == "True":
        return True
    if s == "False":
        return False
    try:
        return float(s)
    except ValueError:
        return s


def merge(a, b, key=None):
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
    yml_paths.reverse()  # child overrides parent

    d = {}
    for yml_path in yml_paths:
        with open(yml_path, "r") as f:
            cur_d = yaml.safe_load(f)
            keys = set((*d.keys(), *cur_d.keys()))
            d = {k: merge(cur_d.get(k), d.get(k), k) for k in keys}
    return d


def create_rclone_rules(arg1, operator, arg2, directory, abs_path):
    if not os.path.isdir(directory):
        raise ValueError("Must be a directory path and not a file.")

    if abs_path:
        directory = os.path.abspath(directory)

    # handle strings
    arg1 = parse_string(arg1)
    arg2 = parse_string(arg2)

    already_harmonized = lambda x: x.startswith('"') and x.endswith('"')
    harmonize_string = (
        lambda x: f'"{x}"' if isinstance(x, str) and not already_harmonized(x) else x
    )

    if operator == "=" and isinstance(arg2, bool):
        expr = f"m.get({harmonize_string(arg1)}) == {arg2}"
    elif operator == "=":
        expr = f"m.get({harmonize_string(arg1)}) == {harmonize_string(arg2)}"
    elif operator in ["<", ">", "<=", ">=", "="] and isinstance(arg2, float):
        expr = f"m.get({harmonize_string(arg1)}) {operator} {harmonize_string(arg2)}"
    elif operator == "in":
        expr = f"{harmonize_string(arg1)} in m.get({harmonize_string(arg2)})"
    else:
        raise ValueError("Operator and arguments do not match")

    # save results to enable sorting
    res = []
    for path in Path(directory).rglob("*meta.yml"):
        m = get_meta_data(path)
        try:
            if eval(expr):
                res.append(f"+ {path.parents[0]}/**")
            else:
                res.append(f"- {path.parents[0]}/**")
        except:
            continue

    # child rule overwrites parent
    # rclone takes the first match
    res.sort(reverse=True, key=len)
    res.append("- **")

    res = [
        f"# rclone filter rules for searching '{arg1} {operator} {arg2}' inside '{os.path.abspath(directory)}'",
        "- **/meta.yml",
        "- **.meta.yml"
    ] + res

    return res


@click.group()
@click.option("--verbose", "-v", default=False, show_default=True, is_flag=True)
def main(verbose):
    if verbose:
        logging.basicConfig(
            filename="/dev/stderr", encoding="utf-8", level=logging.DEBUG
        )


@main.command()
@click.argument("query", required=True)
@click.option(
    "--directory",
    "-d",
    default=".",
    show_default=True,
    type=click.Path(exists=True),
    help="Search everything recursiveley inside this root directory",
)
@click.option(
    "--abs-path",
    "-a",
    default=False,
    show_default=True,
    is_flag=True,
    help="Use absolute paths",
)
def filter(query, directory, abs_path):
    """
    Create rclone filter rules for files and directories matching a specific attribute stored in YAML meta data sidecar files.

    \b
    Examples:
    metayaml filter "score > 5"
    metayaml filter "djohn in users"
    metayaml filter "is_example = True"
    """
    arg1, operator, arg2 = [x for x in query.split(" ") if len(x) > 0]
    for l in create_rclone_rules(arg1, operator, arg2, directory, abs_path):
        print(l)


@main.command()
@click.argument("query", required=True)
@click.option(
    "--directory",
    "-d",
    default=".",
    show_default=True,
    type=click.Path(exists=True),
    help="Search everything recursiveley inside this root directory",
)
@click.option(
    "--abs-path",
    "-a",
    default=False,
    show_default=True,
    is_flag=True,
    help="Use absolute paths",
)
def find(query, directory, abs_path):
    """
    Find files matching a specific attribute stored in YAML meta data sidecar files.

    \b
    Examples:
    metayaml find "score > 5"
    metayaml find "djohn in users"
    metayaml find "is_example = True"
    """
    # doing this for directories is ambiguous in the recursive mode: It would output the directory even if some children don't match

    arg1, operator, arg2 = [x for x in query.split(" ") if len(x) > 0]
    rules = create_rclone_rules(arg1, operator, arg2, directory, abs_path)

    with NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            f.writelines([x + "\n" for x in rules])
        p = Popen(
            [
                "rclone",
                "lsf",
                directory,
                "--files-only",
                "--recursive",
                "--filter-from",
                tmp.name,
            ]
        )
        p.wait()


@main.command()
@click.argument("path", type=click.Path(exists=True))
def get(path):
    """
    Retrieves attributes of a directory or file based on YAML meta data sidecar files.
    """
    d = get_meta_data(path)
    print(yaml.dump(d))


if __name__ == "__main__":
    main()
