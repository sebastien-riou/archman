from pathlib import Path
from dataclasses import dataclass

class NotAFileError(OSError):
    def __init__(self, msg=None):
        super().__init__("NotAFileError:"+str(msg))

class Archive(object):

    @staticmethod
    def get_archive_root(path_within_archive: str) -> Path:
        raise NotImplementedError()
    
    @staticmethod
    def create_archive(root_path: str): # TODO: declar type of return value ('Archive' gives undefined error)
        raise NotImplementedError()

    def chmod(path, mode):
        raise NotImplementedError()

    def __init__(self, root_path: str, user_root_path: str=None):
        raise NotImplementedError()
    
    def list(self, path, recursive = False):
        raise NotImplementedError()
    
    def add_file(self, src: str, dst:str) -> None:
        raise NotImplementedError()
        
    def add_dir(self, src: str, dst:str) -> None:
        raise NotImplementedError()
    
    def commit(self) -> None:
        raise NotImplementedError()

@dataclass(order=True)
class BaseDir(object):

    def __init__(self, *, name=None):
        self.name = name

@dataclass(order=True)
class BaseFile(object):

    def __init__(self, *, name=None):
        self.name = name       