from archman import cli, FsUtils,FileIntegrityError, DirectoryNotFoundError
from archman.sqlarchive import params
import os
import stat
from pathlib import Path
import shutil
from archman.prng_sha256 import PrngSha256
from seedir import FakeDir,FakeFile
import seedir
import io
import difflib
from filecmp import dircmp
import filecmp
import tempfile

test_root = Path('playground')
test_root.mkdir(exist_ok=True)
archive_root = test_root / 'archive_root'
fixtures_root = test_root / 'fixtures'
files_path = fixtures_root / "files"
out_path = test_root / "out"
random_tree_name = "random_tree"
random_tree_root = test_root.joinpath(random_tree_name)


def check_randomdir(*,root,name,seed=0,size_mb=1,n_duplicated_files=0,n_soft_links=0):
    dirs = seedir.randomdir(name=name,seed=seed)
    nfiles = 0
    size = size_mb * 1024 * 1024
    for path, dirs, files in os.walk(root / name):
        for f in files:
            if not os.path.islink(os.path.join(path,f)):
                nfiles += 1
    average_size = size // nfiles
    remaining = size
    dat_rng = PrngSha256(seed)
    # Use another PRNG to ensure same dir and files 
    # are generated no matter the duplicated file settings
    dup_rng = PrngSha256(seed) 
    dup = []
    soft_rng = PrngSha256(seed) 
    soft = []
    for path, dirs, files in os.walk(root / name):
        for f in files:
            if os.path.islink(os.path.join(path,f)):
                continue
            file_path = os.path.join(path,f)
            if n_duplicated_files > 0:
                if len(dup) < n_duplicated_files:
                    dup.append(file_path)
                else:
                    pos = dup_rng.randint(0,n_duplicated_files-1)
                    dup[pos] = file_path
            if n_soft_links > 0:
                if len(soft) < n_soft_links:
                    soft.append(file_path)
                else:
                    pos = soft_rng.randint(0,n_soft_links-1)
                    soft[pos] = file_path
            file_size = min(remaining,dat_rng.randint(0,2*average_size))
            remaining -= file_size
            with open(file_path,'rb') as file:
                dat = dat_rng.randbytes(file_size)
                expected = bytes(dat)
                actual = file.read()
                assert expected == actual, file_path
    check_dup_files(dup,root,name)
    check_soft_links(soft,root,name)

def randomdir(*,root,name,seed=0,size_mb=1,n_duplicated_files=0,n_soft_links=0):
    dirs = seedir.randomdir(name=name,seed=seed)
    nfiles = 0
    size = size_mb * 1024 * 1024
    dirs.realize(root)
    for path, dirs, files in os.walk(root / name):
        for f in files:
            if not os.path.islink(os.path.join(path,f)):
                nfiles += 1
    average_size = size // nfiles
    remaining = size
    dat_rng = PrngSha256(seed)
    # Use another PRNG to ensure same dir and files 
    # are generated no matter the duplicated file settings
    dup_rng = PrngSha256(seed) 
    dup = []
    soft_rng = PrngSha256(seed) 
    soft = []
    for path, dirs, files in os.walk(root / name):
        for f in files:
            file_path = os.path.join(path,f)
            if n_duplicated_files > 0:
                if len(dup) < n_duplicated_files:
                    dup.append(file_path)
                else:
                    pos = dup_rng.randint(0,n_duplicated_files-1)
                    dup[pos] = file_path
            if n_soft_links > 0:
                if len(soft) < n_soft_links:
                    soft.append(file_path)
                else:
                    pos = soft_rng.randint(0,n_soft_links-1)
                    soft[pos] = file_path
            file_size = min(remaining,dat_rng.randint(0,2*average_size))
            remaining -= file_size
            with open(file_path,'wb') as file:
                dat = dat_rng.randbytes(file_size)
                file.write(dat)
    create_dup_files(dup,root,name)
    create_soft_links(soft,root,name)


def create_dup_files(dup,root,name):
    cnt = 0
    for f in dup:
        fn = "%d.dup"%cnt
        shutil.copyfile(f,root / name / fn)
        cnt += 1                

def check_dup_files(dup,root,name):
    cnt = 0
    for f in dup:
        fn = "%d.dup"%cnt
        assert filecmp.cmp(f,root / name / fn,shallow=False)
        cnt += 1                


def create_soft_links(soft,root,name):
    cnt = 0
    base = root / name
    for f in soft:
        fn = "%d.soft"%cnt
        rel_path = Path(f).relative_to(base)
        os.symlink(rel_path, base / fn)
        cnt += 1

def check_soft_links(soft,root,name):
    cnt = 0
    base = root / name
    for f in soft:
        fn = "%d.soft"%cnt
        rel_path = str(Path(f).relative_to(base))
        actual = os.readlink(base / fn)
        assert actual == rel_path
        cnt += 1

if not random_tree_root.exists():    
    randomdir(root=test_root,
              name=random_tree_name,
              n_duplicated_files=3,
              n_soft_links=4)

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


def clean():
    FsUtils.rmtree(str(archive_root))
    FsUtils.rmtree(str(out_path))
    out_path.mkdir()

def gen_list_expected_output(path:Path, recursive = False, max_depth=None):
    expected = io.StringIO()
    print("archive '%s':"%str(archive_root.absolute()),file=expected)
    print(
        seedir.seedir(
            path=path,first='folders',
            sort=True,
            exclude_folders=cli.get_archive_impl_dirs(),
            exclude_files=cli.get_archive_impl_files(), 
            printout=False),
        file=expected)
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

def check_dirs_equal(a,b):
    cmp = dircmp(a,b)
    assert 0 == len(cmp.left_only)
    assert 0 == len(cmp.right_only)
    assert 0 == len(cmp.diff_files)

def check_export_dir():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    check_dirs_equal(random_tree_root,out)

def check_dedup_hardlink():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    cli.cmd_check(src=str(archive_root))
    cli.cmd_dedup(src=arch,hardlink=True)
    cli.cmd_check(src=str(archive_root))
    cli.cmd_export(src=arch, dst=out, recursive=True)
    check_dirs_equal(random_tree_root,out)

def check_dedup_remove():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    cli.cmd_check(src=str(archive_root))
    cli.cmd_dedup(src=arch,hardlink=False)
    cli.cmd_check(src=str(archive_root))
    cli.cmd_export(src=arch, dst=out, recursive=True)
    check_randomdir(root=out_path,name=random_tree_name,n_duplicated_files=0,n_soft_links=4)

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

def check_pure_move():
    """change parent directory but don't change the name"""
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    for root,dirs,files in os.walk(random_tree_root):
        forg = os.path.join(root,files[0])
        fnew = os.path.join(root,dirs[0],files[0])
        dorg = os.path.join(root,dirs[1])
        dnew = os.path.join(root,dirs[2],dirs[1])
        break
    forg = Path(forg).relative_to(random_tree_root)
    fnew = Path(fnew).relative_to(random_tree_root) 
    dorg = Path(dorg).relative_to(random_tree_root)
    dnew = Path(dnew).relative_to(random_tree_root)
    cli.cmd_move(src=arch / forg,dst=arch / fnew)
    cli.cmd_move(src=arch / dorg,dst=arch / dnew, recursive=True)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    tmp = out_path / 'expected'
    shutil.copytree(random_tree_root,tmp)
    shutil.move(tmp / forg, tmp / fnew)
    shutil.move(tmp / dorg, tmp / dnew) 
    check_dirs_equal(tmp,arch)

def check_move():
    """change parent directory and change the name"""
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    for root,dirs,files in os.walk(random_tree_root):
        forg = os.path.join(root,files[0])
        fnew = os.path.join(root,dirs[0],files[0]+".moved")
        dorg = os.path.join(root,dirs[1])
        dnew = os.path.join(root,dirs[2],dirs[1]+".moved")
        break
    forg = Path(forg).relative_to(random_tree_root)
    fnew = Path(fnew).relative_to(random_tree_root) 
    dorg = Path(dorg).relative_to(random_tree_root)
    dnew = Path(dnew).relative_to(random_tree_root)
    cli.cmd_move(src=arch / forg,dst=arch / fnew)
    cli.cmd_move(src=arch / dorg,dst=arch / dnew, recursive=True)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    tmp = out_path / 'expected'
    shutil.copytree(random_tree_root,tmp)
    shutil.move(tmp / forg, tmp / fnew)
    shutil.move(tmp / dorg, tmp / dnew) 
    check_dirs_equal(tmp,arch)

def check_delete():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    for root,dirs,files in os.walk(random_tree_root):
        forg = os.path.join(root,files[0])
        dorg = os.path.join(root,dirs[1])
        break
    forg = Path(forg).relative_to(random_tree_root)
    dorg = Path(dorg).relative_to(random_tree_root)
    cli.cmd_delete(dst=arch / forg)
    cli.cmd_delete(dst=arch / dorg, recursive=True)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    tmp = out_path / 'expected'
    shutil.copytree(random_tree_root,tmp)
    os.remove(tmp / forg)
    FsUtils.rmtree(tmp / dorg) 
    check_dirs_equal(tmp,arch)

def check_update():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    out = out_path / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    for root,dirs,files in os.walk(random_tree_root):
        forg = os.path.join(root,files[0])
        break
    forg = Path(forg).relative_to(random_tree_root)
    content = PrngSha256().randbytes(12)
    tmp = out_path / 'expected'
    shutil.copytree(random_tree_root,tmp)
    with open(tmp / forg,'wb') as file:
        file.write(content)
    cli.cmd_update(src=tmp / forg, dst=arch / forg)
    cli.cmd_export(src=arch, dst=out, recursive=True)
    check_dirs_equal(tmp,arch)

def corrupt_file(arch):
    #corrupt it
    for root,dirs,files in os.walk(arch):
        forg = os.path.join(root,files[0])
        logging.info(f"Corrupting {forg}")
        with open(forg,"rb") as f:
            b = bytearray(f.read())
        with open(forg,"wb") as f:
            b[0] = b[0] ^ 0x01
            f.write(b)
        break
    #check
    try:
        cli.cmd_check(src=arch)
        raise RuntimeError("Data corruption in data file NOT detected!")
    except FileIntegrityError:
        pass
    #fix it
    with open(forg,"wb") as f:
        b[0] = b[0] ^ 0x01
        f.write(b)
    cli.cmd_check(src=arch)
    
def delete_data_file(arch):
    for root,dirs,files in os.walk(arch):
        forg = os.path.join(root,files[0])
        logging.info(f"Deleting {forg}")
        b=open(forg,"rb").read()
        break
    #delete it
    os.remove(forg)
    try:
        cli.cmd_check(src=arch)
        raise RuntimeError("Deleted data file NOT detected!")
    except FileNotFoundError:
        pass
    #fix it
    with open(forg,"wb") as f:
        f.write(b)
    cli.cmd_check(src=arch)

def delete_data_folder(arch):
    for root,dirs,files in os.walk(arch):
        forg = os.path.join(root,dirs[0])
        break
    #delete it
    fnew = os.path.join(tempfile.gettempdir() , "delete_data_folder")
    logging.info(f"Deleting {forg} (moving to {fnew})")
    os.rename(src=forg,dst=fnew)
    try:
        cli.cmd_check(src=arch)
        raise RuntimeError("Deleted data file NOT detected!")
    except DirectoryNotFoundError:
        pass
    finally:
        #fix it
        os.rename(src=fnew,dst=forg)
    cli.cmd_check(src=arch)

def check_check():
    clean()
    cli.cmd_new(dst=str(archive_root))
    arch = archive_root / random_tree_name
    cli.cmd_add(src=random_tree_root,dst=arch, recursive=True)
    cli.cmd_check(src=arch)
    #archive is good, now apply various corruptions and check they are caught
    corrupt_file(arch)
    delete_data_file(arch)
    delete_data_folder(arch)
    #final check that all corruptions have been repared
    cli.cmd_check(src=arch)
    

def test_it():
    check_list_empty()
    check_list_generic()
    check_export_file()
    check_export_dir()
    check_dedup_hardlink()
    check_dedup_remove()
    check_pure_move()
    check_move()
    check_delete()
    check_update()
    check_check()


if __name__ == '__main__':
    import logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG) 
    test_it()