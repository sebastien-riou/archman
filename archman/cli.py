import argparse
import logging
import os
from pathlib import Path, PurePath
import io
#from archman.dummyarchive import DummyArchive as ArchiveImpl
from archman.sqlarchive import SqlArchive as ArchiveImpl
from archman import NotAFileError
           
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

def check_file(*, path:str, may_not_exist=False):
    exist = os.path.exists(path)
    if not exist:
        if may_not_exist:
            return
        else:
            raise FileNotFoundError(path)
    isdir = os.path.isdir(path)
    if isdir:
        raise NotAFileError(path)

def path_to_archive(path):
    root = ArchiveImpl.get_archive_root(path)
    return ArchiveImpl(root)

def cmd_args_new(args):
    cmd_new(dst=args.dst)

def cmd_new(*, dst:str) -> None:
    check_dir(path=dst,expected_to_exist=False)
    ArchiveImpl.create_archive(dst)

def cmd_args_mkdir(args):
    cmd_mkdir(dst=args.dst)

def cmd_mkdir(*, dst:str) -> None:
    check_dir(path=dst,expected_to_exist=False)
    archive = path_to_archive(dst)
    print('create new directory',os.path.abspath(dst), 'in archive', archive)
    raise NotImplementedError()

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

def cmd_args_delete(args):
    cmd_delete(dst=args.dst, recursive=args.recursive)

def cmd_delete(dst:str, recursive:bool=False):
    check_recursive(path=dst,recursive=recursive)
    archive = path_to_archive(dst)
    if recursive:
        archive.delete_dir(dst)
    else:
        archive.delete_file(dst)
    archive.commit()

def cmd_args_move(args):
    cmd_move(src=args.src,dst=args.dst)

def cmd_move(*,src:str, dst:str, recursive:bool=False):
    check_recursive(path=src,recursive=recursive)
    archive = path_to_archive(src)
    if recursive:
        archive.move_dir(src=src,dst=dst)
    else:
        archive.move_file(src=src,dst=dst)
    archive.commit()

def cmd_args_export(args):
    cmd_export(src=args.src,dst=args.dst, recursive=args.recursive)

def cmd_export(*,src:str, dst:str, recursive:bool=False):
    check_recursive(path=src,recursive=recursive)
    archive = path_to_archive(src)
    if recursive:
        archive.export_dir(src=src, dst=dst)
    else:
        archive.export_file(src=src, dst=dst)

def cmd_args_update(args):
    cmd_update(src=args.src,dst=args.dst)

def cmd_update(*, src, dst):
    check_file(path=src)
    archive = path_to_archive(dst)
    archive.update_file(src=src, dst=dst)
    archive.commit()

def cmd_args_list(args):
    cmd_list(src=args.src,recursive=args.recursive)

def cmd_list_core(*, archive:ArchiveImpl, path:Path, content:dict, parents_last=[]) -> str:
    out = io.StringIO()
    depth = len(parents_last)
    extend = '│ '
    extend_last = '  '
    def p(*args, **kwargs):
        header = ""
        for i in range(0,depth):
            if parents_last[i]:
                header += extend_last
            else:
                header += extend
        line = header + ' '.join(args)
        print(line,**kwargs,file=out)
    nfiles = len(content['files'])
    for i in range(0,len(content['dirs'])):
        (child,child_content) = content['dirs'][i]
        if 0 < nfiles:
            last = False
        else:
            last = i + 1 == len(content['dirs'])
        mark = '├─'
        if last:
            mark = '└─'
        p(mark+child.name+'/')
        child_last = parents_last + [last]
        child_str = cmd_list_core(
            archive=archive, 
            path=path.joinpath(child.name), 
            content=child_content,
            parents_last = child_last)
        print(child_str,end='',file=out)
    for i in range(0,nfiles):
        child = content['files'][i]
        last = i + 1 == nfiles
        mark = '├─'
        if last:
            mark = '└─'
        p(mark+child.name)
    return out.getvalue()
    
def cmd_list(*, src:str, recursive:bool=False, hardlinks:bool=False) -> str:
    root = ArchiveImpl.get_archive_root(src)
    assert root.is_absolute()
    archive = ArchiveImpl(str(root))
    if hardlinks:
        raise NotImplementedError()
    if not os.path.isdir(src):
        raise NotADirectoryError(src)
    out = io.StringIO()
    path = Path(src).resolve()
    print("archive '"+str(root)+"':",file=out)
    res = archive.list(path, recursive=recursive)
    rel_path = path.relative_to(root.parent)
    mark=''
    if archive.is_dir(rel_path):
        mark='/'
    print(str(rel_path.parts[-1])+mark, file=out)
    return out.getvalue()+cmd_list_core(archive=archive,path=rel_path,content=res)
    
def cmd_args_dedup(args):
    cmd_dedup(src=args.src,hardlink=args.hardlink)

def cmd_dedup(*, src:str, hardlink=False):
    archive = path_to_archive(src)
    archive.dedup(src,hardlink)
    archive.commit()

def cmd_args_check(args):
    cmd_check(src=args.src)

def cmd_check(*, src:str):
    archive = path_to_archive(src)
    archive.check()

def get_archive_impl_dirs():
    return ArchiveImpl.get_impl_dirs()

def get_archive_impl_files():
    return ArchiveImpl.get_impl_files()

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
    parser_delete.set_defaults(func=cmd_args_delete)
    parser_move = subparsers.add_parser('move', help='Move/rename a file or a directory within the archive')
    parser_move.set_defaults(func=cmd_move)
    parser_export = subparsers.add_parser('export', help='Output the content of a file or a directory')
    parser_export.set_defaults(func=cmd_args_export)
    parser_update = subparsers.add_parser('update', help='Change the content of a file')
    parser_update.set_defaults(func=cmd_args_update)
    parser_list = subparsers.add_parser('list', help='Output the content of a directory')
    parser_list.set_defaults(func=cmd_args_list)
    parser_dedup = subparsers.add_parser('dedup', help='Operations on files with equivalent content')
    parser_dedup.set_defaults(func=cmd_args_dedup)
    parser_check = subparsers.add_parser('check', help='Sanity check')
    parser_check.set_defaults(func=cmd_args_check)
    
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
    parser_delete.add_argument('dst', help='Target path', type=str)
    
    # move command
    parser_move.add_argument('src', help='Source path', type=str)
    parser_move.add_argument('dst', help='Destination path', type=str)
    
    # export command
    parser_export.add_argument('src', help='Source path', type=str)
    parser_export.add_argument('dst', help='Destination path', type=str)
    
    # update command
    parser_update.add_argument('src', help='Source path', type=str)
    parser_update.add_argument('dst', help='Destination path', type=str)

    # list command
    parser_list.add_argument('src', help='Source path', type=str)
    #parser_list.add_argument('--hardlinks', help='list files hardlinked with src', action='store_true')
    
    # dedup command
    parser_dedup.add_argument('src', help='Source path', type=str)
    parser_dedup.add_argument('--hardlink', help='Turn all equivalent files to hard links', action='store_true')
    #parser_dedup.add_argument('--softlink', help='Turn all equivalent files to soft links', action='store_true')
    parser_dedup.add_argument('--remove', help='Delete all equivalent files', action='store_true')
    
    # check command
    parser_check.add_argument('src', help='Source path', type=str)
    
    args = parser.parse_args()
    logging.basicConfig(format='%(message)s', level=args.log_level)
    args.func(args)
    