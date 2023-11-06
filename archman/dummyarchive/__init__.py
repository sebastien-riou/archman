"""Functional reference implementation

Limitations:
- all operations are commited immediatly (commit as no effect)
- no robustness against bit rot

"""

from pathlib import Path, PurePath
import os
from archman.dummyarchive import params
from archman import Archive,NotAFileError,BaseDir,BaseFile
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
        
    def list(self, path: Path, recursive = False):
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
        logging.info('adding ' + str(s) + ' to ' + str(d) + ' in archive' + str(self.root_path))
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
        logging.info('adding ' + str(s) + ' to ' + str(d) + ' in archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if s.is_file():
            raise NotADirectoryError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.copytree(src=s,dst=d,symlinks=False) # TODO: handle symlinks
    
    def commit(self) -> None:
        pass
    
    def export_file(self, src:str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('exporting ' + str(s) + ' to ' + str(d) + ' from archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if not s.is_file():
            raise NotAFileError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        
        shutil.copyfile(src=s,dst=d,follow_symlinks=False) # TODO: handle symlinks

    def export_dir(self, src: str, dst:str) -> None:
        src_file = Path(src).name
        s_parent = Path(src).parent.resolve()
        s = s_parent.joinpath(src_file)
        d = Path(dst).resolve()
        d_parent = d.parent
        logging.info('exporting ' + str(s) + ' to ' + str(d) + ' from archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if s.is_file():
            raise NotADirectoryError(str(s))
        if d.exists():
            raise FileExistsError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        shutil.copytree(src=s,dst=d,symlinks=False) # TODO: handle symlinks

    @staticmethod
    def are_hardlinked(f1, f2):
        if not (os.path.isfile(f1) and os.path.isfile(f2)):
            return False
        return os.path.samefile(f1, f2) or (os.stat(f1).st_ino == os.stat(f2).st_ino)
    
    def dedup(self, src: str, hardlink=False):
        src_dir = Path(src).resolve()
        if not src_dir.is_dir():
            raise NotADirectoryError(str(src_dir))
        print("dedup %s"%src_dir)
        index = {}
        for path, dirs, files in os.walk(src_dir):
            for f in files:
                file_path = os.path.join(path,f)
                dat = open(file_path,'rb').read()
                dig = hashlib.sha256(dat).digest()
                if dig in index:
                    org = index[dig]
                    if not DummyArchive.are_hardlinked(org,file_path):
                        print("duplicated files found: %s and %s"%(org,file_path))
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