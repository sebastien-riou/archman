from pathlib import Path,PurePath
import os
from archman.db import IndexDb,FileIndex,FolderIndex
from archman.check import RepairInfo
from archman import params
import shutil
import logging
import hashlib 

def hash(dat):
    return hashlib.sha256(dat).digest()

class NotAFileError(OSError):
    def __init__(self, msg=None):
        super().__init__("NotAFileError:"+str(msg))

class Archive(object):

    @staticmethod
    def get_archive_root(path_within_archive: str) -> Path:
        p = PurePath(path_within_archive)
        if params.DATA_FOLDER in p.parts:
            r=PurePath()
            for part in p.parts:
                if part == params.DATA_FOLDER:
                    ar = Path(r)
                    ar = ar.joinpath(params.INDEX_FOLDER)
                    if ar.exists():
                        # TODO: detect nested archives
                        return Path(r).resolve()
                r = r.joinpath(part)
                
                
        raise Exception("'"+str(Path(p).resolve())+"' is not within an archive")
    
    @staticmethod
    def create_archive(root_path: str): # TODO: declar type of return value ('Archive' gives undefined error)
        root = Path(root_path)
        root.mkdir(mode=params.READ_WRITE,exist_ok=False)
        data = root.joinpath(params.DATA_FOLDER)
        data.mkdir(mode=params.READ_ONLY)
        idx = root.joinpath(params.INDEX_FOLDER)
        idx.mkdir(mode=params.READ_WRITE)
        # create database
        db_file = str(idx.joinpath(params.INDEX_FILE).resolve())
        db = IndexDb(db_file,root=root,create=True)
        # create check file
        check_file = str(idx.joinpath(params.CHECK_FILE).resolve())
        check = RepairInfo(check_file,db_file,create=True)
        #idx.chmod(mode=params.READ_ONLY)
        #root.chmod(mode=params.READ_ONLY)
        return Archive(root_path)
    
    def chmod(path, mode):
        Path(path).chmod(mode)

    def __init__(self,root_path: str):
        self.root_path = Path(root_path).resolve()
        self.db_file = self.root_path.joinpath(params.INDEX_FOLDER,params.INDEX_FILE)
        #dbroot = self.root_path.joinpath(params.DATA_FOLDER)
        self.db = IndexDb(self.db_file, root=root_path)
        self.check_file = self.root_path.joinpath(params.INDEX_FOLDER,params.CHECK_FILE)
        self.check = RepairInfo(self.check_file, self.db_file)

    def list_id(self, folder_id, recursive = False):
        out = {}
        folders = self.db.folders(parent_id=folder_id)
        if recursive:
            for (uid,child) in folders:
                sub_list = self.list_id(uid, recursive=True)[uid]
                for d in sub_list['folders']:
                    d['rel_path'] = str(Path(child.name).joinpath(d['rel_path']))
                out[uid] = {'rel_path':child.name, 'folders':sub_list['folders'], 'files':sub_list['files']} 
        files = self.db.files(parent_id=folder_id)   
        rel_path = '.'
        out[folder_id] = {'rel_path':rel_path, 'folders':folders, 'files':files}     
        return out
    
    def list(self, path, recursive = False):
        out = {}
        parent_id = self.db.folder_from_path(path)[0]
        return self.list_id(parent_id,recursive=recursive)
    
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
        
        # write the file within the archive
        d_parent.chmod(params.READ_WRITE)
        shutil.copyfile(src=s,dst=d,follow_symlinks=False)
        d_parent.chmod(params.READ_ONLY)

        # update index database, in memory for now
        folder_id = self.db.folder_from_path(d_parent)[0]
        digest = hash(s.read_bytes())
        mode = int(oct(s.stat().st_mode)[-3:])
        dfi = FileIndex(
            parent_id=folder_id,
            name = d.name,
            digest = digest,
            mode = mode)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_WRITE)
        self.db.add_file(dfi)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_ONLY)
        
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
        
        # write the file within the archive
        d_parent.chmod(params.READ_WRITE)
        shutil.copytree(src=s,dst=d,symlinks=True)
        d_parent.chmod(params.READ_ONLY)

        # update index database, in memory for now
        folder_id = self.db.folder_from_path(d_parent)[0]
        mode = int(oct(s.stat().st_mode)[-3:])
        dfi = FolderIndex(
            parent_id=folder_id,
            name = d.name,
            mode = mode)
        # TODO: recurse
        logging.warning('user ' + str(os.geteuid()))
        
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_WRITE)
        #self.root_path.chmod(params.READ_WRITE)
        #self.db_file.chmod(params.READ_WRITE)
        self.db.add_folder(dfi)
        #self.db_file.chmod(params.READ_ONLY)
        #self.root_path.chmod(params.READ_ONLY)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_ONLY)
        
    def commit(self) -> None:
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_WRITE)
        #self.db_file.chmod(params.READ_WRITE)
        self.db.commit()
        #self.db_file.chmod(params.READ_ONLY)
        #self.check_file.chmod(params.READ_WRITE)
        os.remove(self.check_file)
        check = RepairInfo(self.check_file,self.db_file,create=True)
        #self.check_file.chmod(params.READ_ONLY)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_ONLY)
        