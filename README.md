# archman
Archive management tool. This is a work in progress.

## Goals
The main goal is to backup files safely and easily. 

By "safely" I mean:
- reasonably "idiot proof", don't let the user shoot himself in the foot
- robust vs accidental file corruption (bit rot)

By "easily" I mean:
- It just works without complicated process for user
- It is usable without refering constantly to the user manual

Note on robustness against bit rot: a single bit corruption within the storage medium may still corrupt the archive however ArchMan is able to identify the corruption and repaire if you have another copy (as long as the other copy is not corrupted in the same way). It is therefore recommended to keep at least two copies of an archive on two different storage devices.

## Features

- [ ] detect data corruption
- [x] de duplicate files (replace by hard links or remove)
- [ ] correct errors / repair files based on several damaged copies

## Concept
Archman works on top of any POSIX file system, an archive is a regular folder that contains: 
- regular files from user: any kind of files and folders
- an index database: a standard sqlite3 file
- a database check file: a custom binary file containing redundant information to check the integrity of the index database

The index database and its check file are placed in a ".archman" folder to discourage users to touch them. User files are placed just inside the archive folder. Everything in that folder is set as "read only + execute", the original access right are stored in the index database.

A top level README.txt explains what archman is and points to online doc.

### Treatment of links
Soft and hard links are stored "as is", ArchMan handle them like the OS.
The "dedup" command can create hard links when it detects equivalent files
and is invoked with "--hardlink".

### Repair
There are several types of damage:
- file content
- file / directory name
- low level file system structure which make everything unreadable

The third kind can be corrected only with knowledge of the file system structure, ArchMan does not handle this.

## How to test
````
pipenv run python -m test.test_cli3
````