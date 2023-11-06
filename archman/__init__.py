from pathlib import Path
from dataclasses import dataclass
import os
import shutil

class NotAFileError(OSError):
    def __init__(self, msg=None):
        super().__init__("NotAFileError:"+str(msg))

class FsUtils(object):
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

    @staticmethod
    def chmod(path, mode):
        raise NotImplementedError()
    
    @staticmethod
    def are_hardlinked(f1, f2):
        if not (os.path.isfile(f1) and os.path.isfile(f2)):
            return False
        return os.path.samefile(f1, f2) or (os.stat(f1).st_ino == os.stat(f2).st_ino)
    
    

class Archive(object):

    @staticmethod
    def get_archive_root(path_within_archive: str) -> Path:
        raise NotImplementedError()
    
    @staticmethod
    def create_archive(root_path: str): # TODO: declar type of return value ('Archive' gives undefined error)
        raise NotImplementedError()

    def __init__(self, root_path: str, user_root_path: str=None):
        raise NotImplementedError()
    
    def list(self, path, recursive = False) -> dict:
        raise NotImplementedError()
    
    def add_file(self, src: str, dst:str) -> None:
        raise NotImplementedError()
        
    def add_dir(self, src: str, dst:str) -> None:
        raise NotImplementedError()
    
    def delete_file(self, dst:str) -> None:
        raise NotImplementedError()
    
    def delete_dir(self, dst:str) -> None:
        raise NotImplementedError()
    
    def move_file(self, src: str, dst:str) -> None:
        raise NotImplementedError()
        
    def move_dir(self, src: str, dst:str) -> None:
        raise NotImplementedError()
    
    def commit(self) -> None:
        raise NotImplementedError()

    def export_file(self, src:str, dst:str) -> None:
        raise NotImplementedError()

    def export_dir(self, src: str, dst:str) -> None:
        raise NotImplementedError()
 
    def dedup(self, src: str, hardlink=False) -> None:
        raise NotImplementedError()


@dataclass(order=True)
class BaseDir(object):

    def __init__(self, *, name=None):
        self.name = name

@dataclass(order=True)
class BaseFile(object):

    def __init__(self, *, name=None):
        self.name = name       