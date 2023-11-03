from archman import cli
from archman.sqlarchive import params
import os
import stat
from pathlib import Path
import shutil
import random

test_root = Path('playground')
archive_root = test_root / 'archive_root'
fixtures_root = test_root / 'fixtures'
files_path = fixtures_root / "files"
if not files_path.exists():
    files_path.mkdir(parents=True)
    for i in range(0,100):
        fn = 'f%04d'%i
        with open(files_path / fn,'w')as f:
            f.write(fn)

dirs_path = fixtures_root / "dirs"
if not dirs_path.exists():
    dirs_path.mkdir(parents=True)
    for i in range(0,100):
        dn = 'd%04d'%i
        dp = dirs_path / dn
        dp.mkdir()

def rmtree(path):
    if not os.path.exists(path):
        return
    DIR_READ_WRITE = 0o700
    FILE_READ_WRITE = 0o600
    def remove_readonly(func, path, _):
        "Clear the readonly bit and reattempt the removal"
        os.chmod(path, FILE_READ_WRITE)
        func(path)

    # set all directories as read/write
    os.chmod(path, DIR_READ_WRITE)
    for root, dirs, files in os.walk(path):
        for d in dirs:
            os.chmod(os.path.join(root, d), DIR_READ_WRITE)

    shutil.rmtree(path, onerror=remove_readonly)


def rmtree1(path):
    files_in_directory = os.listdir(path)

    for file in files_in_directory:
        try:
            path_to_file_or_folder = os.path.join(path, file)
            shutil.rmtree(path_to_file_or_folder)
        except:
            os.unlink(path_to_file_or_folder)

def clean():
    rmtree(str(archive_root))
import seedir
def gen_list_expected_output(path:Path, recursive = False, max_depth=None):
    expected = io.StringIO()
    print("archive '%s':"%str(archive_root.absolute()),file=expected)
    rel_path = path.relative_to(archive_root)
    rel_path = Path(rel_path).parent
    if str(rel_path) != ".":
        print(rel_path,end="/",file=expected)
    print(seedir.seedir(path=path, printout=False),file=expected)
    return expected.getvalue()

def check_list_empty():
    clean()
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data.absolute())+"'"
    expected += """
 .
"""
    print(expected)
    print(out)
    assert out == expected
    print(gen_list_expected_output(data,recursive=True))

def check_list_1file():
    clean()
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=files_path / 'f0000',dst=data / 'f0000')
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data.absolute())+"'"
    expected += """
 .
 - f0000
"""
    print(expected)
    print(out)
    assert out == expected
    print(gen_list_expected_output(data,recursive=True))

def check_list_1dir():
    clean()
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=dirs_path / 'd0000',dst=data / 'd0000', recursive=True)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data.absolute())+"'"
    expected += """
 .
 d d0000
"""
    assert out == expected
    print(gen_list_expected_output(data,recursive=True))

def check_list_nested_dir():
    clean()
    print("getuid:",os.getuid())
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=dirs_path / 'd0000',dst=data / 'd0000', recursive=True)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data.absolute())+"'"
    expected += """
 .
 d d0000
"""
    assert out == expected
    cli.cmd_add(src=dirs_path / 'd0001',dst=data / 'd0000' / 'd0001', recursive=True)
    out = cli.cmd_list(src=data)
    assert out == expected
    out = cli.cmd_list(src=data, recursive=True)
    expected = "list of '"+str(data.absolute())+"'"
    expected += """
 .
 d d0000
   d d0001
"""
    print(expected)
    print(out)
    assert out == expected
    print(gen_list_expected_output(data,recursive=True))
    print(gen_list_expected_output(data / 'd0000',recursive=True))

import math
import io
def check_list_generic(max_depth=3, nfiles=10, ndirs=10):
    clean()
    ave_files_per_dir = math.ceil(nfiles / ndirs)
    max_files_per_dir = 2*ave_files_per_dir
    random.seed(0)
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    expected = io.StringIO()
    print("list of '"+str(data.absolute())+"'",file=expected)
    indent = ' '
    indent_unit = '  '
    for i in range(0,ndirs):
        remaining = ndirs-i
        level = min(remaining,random.randint(1,max_depth))
        path = data
        for j in range(0,level):
            id = i+j
            name = 'd%04d'%id
            path = path.joinpath(name)
            cli.cmd_add(src=dirs_path / name,dst=path, recursive=True)

    out = cli.cmd_list(src=data)
    print(expected)
    print(out)
    assert out == expected

def test_it():
    check_list_empty()
    check_list_1file()
    check_list_1dir()
    check_list_nested_dir()
    check_list_generic()


if __name__ == '__main__':
    test_it()