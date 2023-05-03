# metayaml: Oragnize file and directory attributes using YAML files

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

## Get Started

To create attributes of a directory, just create a file `meta.yml` into that directory.
Create a file `/path/foo.txt.yml` to create attributes to just the file `/path/foo.txt`.

```
$ ./metayaml.py get example
description: all data
is_example: true

$ ./metayaml.py get example/EU
INFO:root:overwrite description from 'all data' to 'EU data'
description: EU data
is_example: true
users:
- dloos
- fgans

$ ./metayaml.py get example/EU/de.txt
INFO:root:overwrite description from 'all data' to 'EU data'
INFO:root:overwrite users from '['dloos', 'fgans']' to '['djohn']'
INFO:root:overwrite description from 'EU data' to 'Germany data'
description: Germany data
has_sidecar_meta_file: true
is_example: true
users:
- djohn

# reverse search: get files using attributes
$ ./metayaml.py find description "EU data" 2>/dev/null
example/EU
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
