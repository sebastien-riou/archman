from archman import cli
from archman import params
import pytest
import os

@pytest.fixture()
def archive_root(tmp_path):
    yield tmp_path.joinpath('archive_root')


@pytest.fixture(scope="session")
def files_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("files")
    for i in range(0,100):
        fn = 'f%04d'%i
        with open(path / fn,'w')as f:
            f.write(fn)
    return path

@pytest.fixture(scope="session")
def dirs_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("dirs")
    for i in range(0,100):
        dn = 'd%04d'%i
        dp = path / dn
        dp.mkdir()
    return path

def test_list_empty(archive_root):
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data)+"'"
    expected += """
 .
"""
    assert out == expected

def test_list_1file(archive_root,files_path):
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=files_path / 'f0000',dst=data / 'f0000')
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data)+"'"
    expected += """
 .
 - f0000
"""
    assert out == expected

def test_list_1dir(archive_root,dirs_path):
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=dirs_path / 'd0000',dst=data / 'd0000', recursive=True)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data)+"'"
    expected += """
 .
 d d0000
"""
    assert out == expected

def test_list_nested_dir(archive_root,dirs_path):
    print("getuid:",os.getuid())
    cli.cmd_new(dst=str(archive_root))
    data = archive_root.joinpath(params.DATA_FOLDER)
    cli.cmd_add(src=dirs_path / 'd0000',dst=data / 'd0000', recursive=True)
    out = cli.cmd_list(src=data)
    expected = "list of '"+str(data)+"'"
    expected += """
 .
 d d0000
"""
    assert out == expected
    cli.cmd_add(src=dirs_path / 'd0001',dst=data / 'd0000' / 'd0001', recursive=True)
    out = cli.cmd_list(src=data)
    assert out == expected
    out = cli.cmd_list(src=data, recursive=True)
    expected = "list of '"+str(data)+"'"
    expected += """
 .
 d d0000
   d d0001
"""
    assert out == expected