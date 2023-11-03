from archman import cli
from archman.sqlarchive import params
import os
import stat
from pathlib import Path
import shutil
import random
from seedir import FakeDir,FakeFile
import seedir
import io
import difflib
from filecmp import dircmp
import filecmp

test_root = Path('playground')
archive_root = test_root / 'archive_root'
fixtures_root = test_root / 'fixtures'
files_path = fixtures_root / "files"
out_path = test_root / "out"
random_tree_name = "random_tree"
random_tree_root = test_root.joinpath(random_tree_name)

if not random_tree_root.exists():    
    model = seedir.randomdir(name=random_tree_name,seed=0)
    model.realize(test_root)

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

def clean():
    rmtree(str(archive_root))
    rmtree(str(out_path))
    out_path.mkdir()

def gen_list_expected_output(path:Path, recursive = False, max_depth=None):
    expected = io.StringIO()
    print("archive '%s':"%str(archive_root.absolute()),file=expected)
    print(seedir.seedir(path=path,first='folders',sort=True,exclude_files=cli.get_archive_impl_files(), printout=False),file=expected)
    return expected.getvalue()

def check_str_equal(actual,expected):
    if actual!=expected:
        print("String mismatch ERROR")
        print("Expected:")
        print(expected)
        print("\n\nActual:")
        print(actual)
        print("\n\nChanges to make actual equal to expected")
        for i,s in enumerate(difflib.ndiff(actual, expected)):
            if s[0]==' ': continue
            elif s[0]=='-':
                print(u'Delete "{}" from position {}'.format(s[-1],i))
            elif s[0]=='+':
                print(u'Add "{}" to position {}'.format(s[-1],i))    
        assert actual==expected

def check_list_empty():
    clean()
    cli.cmd_new(dst=str(archive_root))
    out = cli.cmd_list(src=archive_root)
    expected = gen_list_expected_output(archive_root,recursive=True)
    check_str_equal(out,expected)
    
def check_list_generic():
    clean()
    cli.cmd_new(dst=str(archive_root))
    expected = gen_list_expected_output(random_tree_root,recursive=True)
    dst = archive_root / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=dst, recursive=True)
    out = cli.cmd_list(src=dst,recursive=True)
    check_str_equal(out,expected)
    cmp = dircmp(random_tree_root,dst)
    assert 0 == len(cmp.left_only)
    assert 0 == len(cmp.diff_files)

def check_export_dir():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    cmp = dircmp(random_tree_root,out)
    assert 0 == len(cmp.left_only)
    assert 0 == len(cmp.diff_files)

def check_export_file():
    clean()
    cli.cmd_new(dst=str(archive_root))
    file_name = 'f0000'
    org = files_path / file_name
    arch = archive_root / file_name
    out = out_path / file_name
    cli.cmd_add(src=org, dst=arch)
    cli.cmd_export(src=arch, dst=out)
    assert filecmp.cmp(org,out,shallow=False)

def test_it():
    check_list_empty()
    check_list_generic()
    check_export_file()
    check_export_dir()


if __name__ == '__main__':
    import logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG) 
    test_it()