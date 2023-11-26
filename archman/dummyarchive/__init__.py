"""Functional reference implementation

Limitations:
- all operations are commited immediatly (commit as no effect)
- no robustness against bit rot

"""

from pathlib import Path, PurePath
import os
from archman.dummyarchive import params
from archman import Archive,NotAFileError,FsUtils,BaseDir,BaseFile
import logging
import shutil
import hashlib

class DummyArchive(Archive):
    
    @staticmethod
    def get_impl_files():
        return [params.INDEX_FILE]
    
    @staticmethod
    def get_archive_root(path_within_archive: str) -> Path:
        p = Path(path_within_archive).resolve()
        r = Path()
        for part in p.parts:
            r = r.joinpath(part)
            t = r.joinpath(params.INDEX_FILE)
            if t.exists():
                return r
        raise FileNotFoundError()
    
    @staticmethod
    def create_archive(root_path: str): # TODO: declar type of return value ('Archive' gives undefined error)
        r = Path(root_path)
        assert r.parent.exists()
        r.mkdir()
        t = r.joinpath(params.INDEX_FILE)
        open(t,"w").close()
        return DummyArchive(str(r))
    
    def chmod(path, mode):
        Path(path).chmod(mode)

    def __init__(self,root_path: str, user_root_path: str=None):
        self.root_path = Path(root_path)
        assert self.root_path.exists()
        assert user_root_path is None
        self.user_root_path = Path(root_path)
    
    def resolve_path(self, path: Path):
        if not path.is_absolute():
            path = self.user_root_path.joinpath(path)
        return path.resolve()
    
    def is_dir(self, path: Path):
        path = self.resolve_path(path)
        return path.is_dir
        
    def list(self, path: Path, recursive = False) -> dict:
        path = self.resolve_path(path)
        dirs = list()
        files = list()
        is_root = path == self.root_path
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    if not is_root or entry.name!=params.INDEX_FILE: 
                        files.append(BaseFile(name=entry.name))
                else:
                    dirs.append(BaseDir(name=entry.name))
        files.sort(key=lambda x: x.name)
        dirs.sort(key=lambda x: x.name)
        dirs_tuples = list()
        for d in dirs:
            dirs_tuples.append((d,{'dirs':[],'files':[]}))
        out = {'dirs':dirs_tuples, 'files':files}     
        if recursive:
            rec_dirs = []
            for child in dirs:
                child_full_path = path.joinpath(child.name)
                content = self.list(child_full_path,recursive=True)
                item = (child,content)
                rec_dirs.append(item) 
            out['dirs'] = rec_dirs
        return out
    
    def add_file(self, src: str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('adding file ' + str(s) + ' to ' + str(d) + ' in archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if not s.is_file():
            raise NotAFileError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.copyfile(src=s,dst=d,follow_symlinks=False) # TODO: handle symlinks
        
    def add_dir(self, src: str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('adding directory ' + str(s) + ' to ' + str(d) + ' in archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if s.is_file():
            raise NotADirectoryError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.copytree(src=s,dst=d,symlinks=True) # symlinks are preserved
    
    def delete_file(self, dst:str) -> None:
        logging.info('deleting file ' + str(dst) + ' from archive' + str(self.root_path))
        os.remove(dst)
    
    def delete_dir(self, dst:str) -> None:
        logging.info('deleting directory ' + str(dst) + ' from archive' + str(self.root_path))
        FsUtils.rmtree(dst)

    def update_file(self, src: str, dst:str) -> None:
        self.delete_file(dst)
        self.add_file(src=src,dst=dst)

    def move_file(self, src: str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('moving file ' + str(s) + ' to ' + str(d) + ' within archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if not s.is_file():
            raise NotAFileError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.move(src,dst)

    def move_dir(self, src: str, dst:str) -> None:
        s = Path(src).resolve()
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('moving directory ' + str(s) + ' to ' + str(d) + ' within archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if s.is_file():
            raise NotADirectoryError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.move(src,dst)

    def commit(self) -> None:
        pass
    
    def export_file(self, src:str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('exporting file ' + str(s) + ' to ' + str(d) + ' from archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if not s.is_file():
            raise NotAFileError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        
        shutil.copyfile(src=s,dst=d,follow_symlinks=False) 

    def export_dir(self, src: str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('exporting directory ' + str(s) + ' to ' + str(d) + ' from archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if s.is_file():
            raise NotADirectoryError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.copytree(src=s,dst=d,symlinks=True) # preserve symlinks
 
    def dedup(self, src: str, hardlink=False) -> None:
        src_dir = Path(src).resolve()
        if not src_dir.is_dir():
            raise NotADirectoryError(str(src_dir))
        logging.info("dedup %s"%src_dir)
        index = {}
        for path, dirs, files in os.walk(src_dir):
            for f in files:
                file_path = os.path.join(path,f)
                if os.path.islink(file_path):
                    print("soft link found: %s"%file_path)
                    continue
                dat = open(file_path,'rb').read()
                dig = hashlib.sha256(dat).digest()
                if dig in index:
                    org = index[dig]
                    if not FsUtils.are_hardlinked(org,file_path):
                        logging.info("duplicated files found: %s and %s"%(org,file_path))
                        if org.endswith(".dup"):
                            keep = file_path
                            other = org
                        else:
                            keep = org 
                            other = file_path
                        index[dig] = keep                        
                        os.remove(other)
                        if hardlink:
                            os.link(keep,other)
                else:
                    index[dig] = file_path