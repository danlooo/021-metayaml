#!/usr/bin/env python

#
# Collect meta data attributes of files or directories stored in meta.yml files
# More specific attributes override those from its parent directories
#

import click
import yaml
import os
from subprocess import Popen, check_output
from pathlib import Path
import logging
from tempfile import NamedTemporaryFile
import re

operators = ["<", ">", "=", "<=", ">=", "in"]


def get_meta_yaml_paths(path):
    res = check_output(
        [
            "rclone",
            "lsf",
            "--files-only",
            "--recursive",
            "--include",
            "**meta.yml",
            path,
        ]
    )
    return [Path(os.path.join(path, x)) for x in res.decode().splitlines()]


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


def get_meta_data(path):
    yml_paths = []
    if os.path.isfile(path):
        yml_paths = [os.path.abspath(path) + ".meta.yml"]
    else:
        yml_paths = [os.path.abspath(path) + "/meta.yml"]

    yml_paths += [os.path.abspath(path) + ".meta.yml"]

    yml_paths += [f"{x}/meta.yml" for x in Path(os.path.abspath(path)).parents]
    yml_paths += [f"{x}/meta.yaml" for x in Path(os.path.abspath(path)).parents]

    yml_paths = [x for x in yml_paths if os.path.exists(x)]
    yml_paths.reverse()  # child overrides parent

    d = {}
    for yml_path in yml_paths:
        with open(yml_path, "r") as f:
            cur_d = yaml.safe_load(f)
            if cur_d is None:
                continue
            keys = set((*d.keys(), *cur_d.keys()))
            d = {k: merge(cur_d.get(k), d.get(k), k) for k in keys}
    return d


def create_rclone_rules(arg1, operator, arg2, directory, abs_path):
    if not os.path.isdir(directory):
        raise ValueError("Must be a directory path and not a file.")

    abs_directory = os.path.abspath(directory)
    if abs_path:
        directory = abs_directory

    # handle strings
    arg1 = parse_string(arg1)
    arg2 = parse_string(arg2)

    already_harmonized = lambda x: x.startswith("'") and x.endswith(",")
    harmonize_string = (
        lambda x: f"'{x}'" if isinstance(x, str) and not already_harmonized(x) else x
    )

    if operator == "=" and isinstance(arg2, bool):
        expr = f"m.get({harmonize_string(arg1)}) == {arg2}"
    elif operator == "=":
        expr = f"m.get({harmonize_string(arg1)}) == {arg2}"
    elif operator in ["<", ">", "<=", ">=", "="] and isinstance(arg2, float):
        expr = f"m.get({harmonize_string(arg1)}) {operator} {harmonize_string(arg2)}"
    elif operator == "in":
        expr = f"{harmonize_string(arg1)} in m.get({harmonize_string(arg2)})"
    else:
        raise ValueError("Operator and arguments do not match")

    # save results to enable sorting
    res = []
    for path in get_meta_yaml_paths(directory):
        # extract corresponding data file if single meta data file was found
        if not path.name.endswith("/meta.yml"):
            path = Path(re.sub("\.meta\.yml$", "", str(path)))
        else:
            path = Path(path)

        m = get_meta_data(path)

        if str(path).endswith("/meta.yml"):
            path_str = str(path.parents[0]) + "/**"
        else:
            path_str = str(path)

        try:
            if eval(expr):
                res.append(f"+ {path_str}")
            else:
                res.append(f"- {path_str}")
        except:
            continue

    # child rule overwrites parent
    # rclone takes the first match
    res.sort(reverse=True, key=len)
    res.append("- **")

    res = [
        f"# rclone filter rules for searching '{arg1} {operator} {arg2}' inside '{os.path.abspath(directory)}'",
        "- **/meta.yml",
        "- **.meta.yml",
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
    metayaml find "description = 'foo' "
    """

    arg1, arg2 = map(lambda x: x.strip(), re.split("|".join(operators), query))
    operator = re.findall("|".join(operators), query)[0]

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
    metayaml find "description = 'foo' "
    """
    # doing this for directories is ambiguous in the recursive mode: It would output the directory even if some children don't match

    arg1, arg2 = map(lambda x: x.strip(), re.split("|".join(operators), query))
    operator = re.findall("|".join(operators), query)[0]

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
        p.wait()  # wait to keep tmp file alive


@main.command()
@click.argument("path", type=click.Path(exists=True))
def get(path):
    """
    Retrieves attributes of a directory or file based on YAML meta data sidecar files.
    """
    d = get_meta_data(path)
    print(yaml.dump(d))


@main.command()
@click.argument("root_dir", type=click.Path(exists=True))
def export(root_dir):
    """
    Export all YAML meta data to one YAML file

    \b
    root_dir should be / to ensure that all meta data files are collected.
    Otherwise, recursive inheritance of attributes can not be retrieved from the exported data
    """
    root_dir_s = Path(os.path.expanduser(root_dir)).absolute()

    print(f"# metayaml export of directory {root_dir_s}")
    d = {}
    for p in get_meta_yaml_paths(root_dir_s):
        with open(p, "r") as f:
            d[str(p.absolute())] = yaml.safe_load(f)
    print(yaml.dump(d))


if __name__ == "__main__":
    main()
