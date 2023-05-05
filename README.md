# metayaml

Attributes of files and directories stored in YAML sidecar files


This is a proof of concept on how to easily create meta data / attributes for files and directories.
This works recursively, so attributes of a file are inherited from those from a parent directory if not specified directly.

Use cases:

- Assign users to directories / files so they can be notified when the directory is scheduled for archiving
- Assign a due date so the data can be deleted or archived afterwards

Advantages:

- Machine and human readable
- Independent on file system and OS
- Allows people to write the meta data but not the file itself (e.g. add him/herself as project members)
- Works with Git
- Very flexible: Can add attributes of any type including string, numbers and lists of them

## Usage

To create attributes of a directory, just create a file `meta.yml` into that directory.
Create a file `/path/foo.txt.yml` to create attributes to just the file `/path/foo.txt`.

Files matching these recursively defined attributes can be then retrieved with the command `metayaml find`.
On the other hand, attributes of a given file or directory can be retrieved with the command `metayaml get`.

## Installation

First, ensure that [rclone](https://github.com/rclone/rclone) is available on the machine. Then, install metayaml using:

```
sudo wget https://raw.githubusercontent.com/danlooo/021-metayaml/master/metayaml.py \
  -O /usr/local/bin/metayaml --no-check-certificate && \
  sudo chmod +x /usr/local/bin/metayaml
```

Get help using `metayaml --help`

```
Usage: metayaml [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose
  --help         Show this message and exit.

Commands:
  filter  Create rclone filter rules for files and directories matching a...
  find    Find files matching a specific attribute stored in YAML meta...
  get     Retrieves attributes of a directory or file based on YAML meta...
```

Help page for a specific command: `metayaml find --help`

```
Usage: metayaml.py find [OPTIONS] QUERY

  Find files matching a specific attribute stored in YAML meta data sidecar
  files.

  Examples:
  metayaml find "score > 5"
  metayaml find "djohn in users"
  metayaml find "is_example = True"

Options:
  -d, --directory PATH  Search everything recursiveley inside this root
                        directory  [default: .]
  -a, --abs-path        Use absolute paths
  --help                Show this message and exit.
```

## Forward search: Get attributes of a given directory or file

Get attributes about a directory using `metayaml get example/Americas`

```
description: all data
is_example: true
score: 5
```

or `metayaml get example/EU`

```
description: EU data
is_example: true
score: 3.5
users:
- dloos
- fgans
```

Verbose mode to get warnings in case a value was overwritten by a child directory: `metayaml -v get example/EU`

```
INFO:root:overwrite description from 'all data' to 'EU data'
INFO:root:overwrite score from '5' to '3.5'
description: EU data
is_example: true
score: 3.5
users:
- dloos
- fgans
```

Get attributes of a single file: `metayaml get example/EU/de.txt`

```
description: Germany data
has_sidecar_meta_file: true
is_example: true
score: 3.5
users:
- djohn
```

## Reverse search: Find files matching giving attributes

Find all files for which a particular user is associated:
`metayaml find "dloos in users"`

```
example/EU/be.txt
example/EU/de.txt
example/EU/nl.txt
```

Files in which the score is less than a given number: `metayaml find "score < 4"`

```
example/EU/be.txt
example/EU/de.txt
example/EU/de.txt.yml
example/EU/nl.txt
```

and also `metayaml find "score >= 4"`

```
example/Americas/South_America/ar.txt
example/Americas/South_America/br.txt
example/Americas/South_America/cl.txt
example/Americas/North_America/ca.txt
example/Americas/North_America/us.txt
```

For boolean values, i.e., tags will show no file, because all files were examples: `metayaml find "is_example = False"`

Metayaml uses [rclone](https://github.com/rclone/rclone) to find and filter files.
It creates [rclone filter rules](https://rclone.org/filtering/) that can be also exported: `metayaml filter "score < 4"`

```
# rclone filter rules for searching 'score < 4.0' inside '/home/dloos/lab/021-metayaml'
- **/meta.yml
+ example/EU/**
- example/**
- **
```

## Thoughts

- Just use TOML?
  - TOML uses a table by default. Yaml allows us to set primitives and it is also a superset of JSON
- Can we just merge lists if there are specified to the file and a parent directory?
  - It would be convenient to just put people A and B to the entire directory and person C to just a subdir. We then put just person C in the child meta file. Persons A and B will be then inferred from the parent meta file. However, doing so, there is no way to really overwrite this attribute. It would be also more confusing
- Can we use [tagfs](https://github.com/loglob/tagfs)?
  - Tagfs is a file system in user space (FUSE). We can add tags to a dir to let it appear in the FUSE mounted dir under the tag. However, this is binary only and the tags are stored at a very different location compared to the files
- Can we use xattrs or Extended Attributes on Linux?
  - This would be only accessible on SSH but not on Windows shared folders with SMB. This would also require write access to the file and is very hidden feature (Need a Terminal to access attributes)
- We can also say that the parent overwrites the children. This is way less flexible but allows much faster reverse search to find files that match a certain attribute. Very bad. And finding all meta data fiels on /Net/Groups/BGI/work_1 takes just 6min

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`metayaml` was created by Daniel Loos. It is licensed under the terms of the MIT license.

## Credits

`metayaml` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).
