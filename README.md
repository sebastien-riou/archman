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
- [ ] de duplicate files (replace by hard links)
- [ ] correct errors / repair files based on several damaged copies

## Concept
Archman works on top of any POSIX file system, an archive is a regular folder that contains: 
- regular files from user: any kind of files and folders
- an index database: a standard sqlite3 file
- a database check file: a custom binary file containing redundant information to check the integrity of the index database

The index database and its check file are placed in a ".archman" folder to discourage users to touch them. User files are placed in a "data" folder. Everything in "data" folder is set as "read only + execute", the original access right are stored in the index database.

A top level README.txt explains what archman is and points to online doc.

### Treatment of links
Soft and hard links are stored "as is", ArchMan handle them like the OS.
ArchMan creates hard links when it detect several files with identical content. Those hard links are marked in the index database (USER=0). The "dedup" command can turn those hard links into regular hard links (USER=1), soft links or regular files (all other hard linked files are then removed). 


