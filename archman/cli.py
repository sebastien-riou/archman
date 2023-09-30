import argparse
import logging
import os
from pathlib import Path, PurePath
import io
from archman import Archive
from archman import params
           
def check_recursive(*, path:str, recursive:bool):
    isdir = os.path.isdir(path)
    if isdir != recursive:
        if isdir:
            raise IsADirectoryError(path)
        else:
            raise NotADirectoryError(path)

def check_dir(*, path:str, expected_to_exist=True):
    if expected_to_exist != os.path.exists(path):
        if expected_to_exist:
            raise FileNotFoundError(path)
        else:
            raise FileExistsError(path)
    if expected_to_exist:
        isdir = os.path.isdir(path)
        if not isdir:
            raise NotADirectoryError(path)

def path_to_archive(path):
    root = Archive.get_archive_root(path)
    return Archive(root)

def cmd_args_new(args):
    cmd_new(dst=args.dst)

def cmd_new(*, dst:str) -> None:
    check_dir(path=dst,expected_to_exist=False)
    Archive.create_archive(dst)

def cmd_args_mkdir(args):
    cmd_mkdir(dst=args.dst)

def cmd_mkdir(*, dst:str) -> None:
    check_dir(path=dst,expected_to_exist=False)
    archive = path_to_archive(dst)
    print('create new directory',os.path.abspath(dst), 'in archive', archive)

def cmd_args_add(args):
    cmd_add(src=args.src,dst=args.dst,recursive=args.recursive)

def cmd_add(*,src:str, dst:str, recursive:bool=False) -> None:
    check_recursive(path=src,recursive=recursive)
    archive = path_to_archive(dst)
    if recursive:
        archive.add_dir(src=src, dst=dst)
    else:
        archive.add_file(src=src, dst=dst)
    archive.commit()

def cmd_delete(args):
    print(args)

def cmd_rename(args):
    print(args)

def cmd_move(args):
    print(args)

def cmd_export(args):
    print(args)

def cmd_update(args):
    print(args)

def cmd_args_list(args):
    print(cmd_list(src=args.src,recursive=args.recursive),end='')

def cmd_list(*, src:str, recursive:bool=False, hardlinks:bool=False) -> str:
    if hardlinks or recursive:
        raise NotImplementedError()
    if not os.path.isdir(src):
        raise NotADirectoryError(src)
    root = Archive.get_archive_root(src)
    archive = Archive(str(root))
    out = io.StringIO()
    print("list of '"+str(Path(src).resolve())+"'",file=out)
    res = archive.list(src)
    indent_unit = '  '
    for data in res.values():
        rel_path = data['rel_path']
        folders = data['folders']
        files = data['files']
        parts = Path(rel_path).parts
        indent = indent_unit*len(parts)
        def p(*args, **kwargs):
            print(indent,*args,**kwargs,file=out)
        if len(parts)>0:
            p(parts[-1])
        else:
            p(rel_path)
        #indent += indent_unit
        for (uid,child) in folders:
            p('d',child.name)
        for (uid,child) in files:
            p('-',child.name)
    return out.getvalue()
    
def cmd_dedup(args):
    print(args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='archman.cli')
    levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    parser.add_argument('--log-level', default='WARNING', choices=levels)
    subparsers = parser.add_subparsers(title='subcommands', required=True)
    parser_new = subparsers.add_parser('new', help='Create an empty archive')
    parser_new.set_defaults(func=cmd_args_new)
    parser_mkdir = subparsers.add_parser('mkdir', help='Create a directory within an archive')
    parser_mkdir.set_defaults(func=cmd_args_mkdir)
    parser_add = subparsers.add_parser('add', help='Add a file or a directory to an archive')
    parser_add.set_defaults(func=cmd_args_add)
    parser_delete = subparsers.add_parser('delete', help='Delete a file or a directory from an archive')
    parser_delete.set_defaults(func=cmd_delete)
    parser_rename = subparsers.add_parser('rename', help='Rename a file or a directory within the archive')
    parser_rename.set_defaults(func=cmd_rename)
    parser_move = subparsers.add_parser('move', help='Move a file or a directory within the archive')
    parser_move.set_defaults(func=cmd_move)
    parser_export = subparsers.add_parser('export', help='Output the content of a file or a directory')
    parser_export.set_defaults(func=cmd_export)
    parser_update = subparsers.add_parser('update', help='Change the content of a file')
    parser_update.set_defaults(func=cmd_update)
    parser_list = subparsers.add_parser('list', help='Output the content of a directory')
    parser_list.set_defaults(func=cmd_args_list)
    parser_dedup = subparsers.add_parser('dedup', help='Operations on files with equivalent content')
    parser_dedup.set_defaults(func=cmd_dedup)
    
    # add common options
    for p in subparsers.choices.values():
        if p not in [parser_new, parser_list]:
            p.add_argument('--recursive', help='Needed when the operation is on a directory', action='store_true')
        elif p in [parser_list]:
            p.add_argument('--recursive', help='Recurse in sub directories', action='store_true')
        
    # new command
    parser_new.add_argument('dst', help='Destination path', type=str)
    
    # mkdir command
    parser_mkdir.add_argument('dst', help='Destination path', type=str)
    
    # add command
    parser_add.add_argument('src', help='Source path', type=str)
    parser_add.add_argument('dst', help='Destination path', type=str)
    
    # delete command
    parser_delete.add_argument('src', help='Source path', type=str)
    
    # rename command
    parser_rename.add_argument('src', help='Source path', type=str)
    parser_rename.add_argument('name', help='New name', type=str)
    
    # move command
    parser_move.add_argument('src', help='Source path', type=str)
    parser_move.add_argument('dst', help='Destination directory path', type=str)
    
    # export command
    parser_export.add_argument('--out', help='Specify the output path', default='stdout', type=str)
    
    # update command
    parser_update.add_argument('src', help='Source path', type=str)
    parser_update.add_argument('dst', help='Destination path', type=str)

    # list command
    parser_list.add_argument('src', help='Source path', type=str)
    parser_list.add_argument('--hardlinks', help='list files hardlinked with src', action='store_true')
    
    # dedup command
    parser_dedup.add_argument('src', help='Source path', type=str)
    parser_dedup.add_argument('--hardlinks', help='Turn all equivalent files to hard links', action='store_true')
    parser_dedup.add_argument('--softlinks', help='Turn all equivalent files to soft links', action='store_true')
    parser_dedup.add_argument('--remove', help='Delete all equivalent files', action='store_true')
    
    
    args = parser.parse_args()
    logging.basicConfig(format='%(message)s', level=args.log_level)
    args.func(args)
    