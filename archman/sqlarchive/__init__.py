from pathlib import Path,PurePath
import os
from archman.sqlarchive.db import IndexDb,FileIndex,FolderIndex
from archman.sqlarchive.check import RepairInfo
from archman import Archive
import shutil
import logging
from archman.sqlarchive import params
from archman import NotAFileError,DirectoryNotFoundError,FileIntegrityError,FsUtils
import pysatl
import hashlib



class SqlArchive(Archive):

    @staticmethod
    def get_impl_dirs():
        return [str(Path(params.INDEX_DIR))]
    
    @staticmethod
    def get_archive_root(path_within_archive: str) -> Path:
        p = Path(path_within_archive).resolve()
        r = Path()
        for part in p.parts:
            r = r.joinpath(part)
            t = r.joinpath(params.INDEX_DIR)
            if t.exists():
                return r
        raise Exception("'"+str(Path(p).resolve())+"' is not within an archive")
    
    @staticmethod
    def create_archive(root_path: str): # TODO: declar type of return value ('Archive' gives undefined error)
        root = Path(root_path)
        root.mkdir(mode=params.READ_WRITE,exist_ok=False)
        idx = root.joinpath(params.INDEX_DIR)
        idx.mkdir(mode=params.READ_WRITE)
        # create database
        db_file = str(idx.joinpath(params.INDEX_FILE).resolve())
        db = IndexDb(db_file,root=root,create=True)
        # create check file
        check_file = str(idx.joinpath(params.CHECK_FILE).resolve())
        check = RepairInfo(check_file,db_file,create=True)
        #idx.chmod(mode=params.READ_ONLY)
        #root.chmod(mode=params.READ_ONLY)
        return SqlArchive(root_path)
    
    @staticmethod
    def digest(data: bytes) -> bytes:
        dig = hashlib.sha256(data).digest()
        return dig
    
    def chmod(path, mode):
        Path(path).chmod(mode)

    def __init__(self,root_path: str, user_root_path: str=None):
        self.root_path = Path(root_path).resolve()
        assert user_root_path is None
        self.user_root_path = Path(root_path).resolve()
        self.index_dir = self.root_path.joinpath(params.INDEX_DIR)
        self.db_file = self.index_dir.joinpath(params.INDEX_FILE)
        self.db = IndexDb(self.db_file, root=root_path)
        self.check_file = self.index_dir.joinpath(params.CHECK_FILE)
        self.repair_info = RepairInfo(self.check_file, self.db_file)

    def resolve_path(self, path: Path):
        if not path.is_absolute():
            path = self.user_root_path.joinpath(path)
        return path.resolve()
    
    def is_dir(self, path: Path):
        path = self.resolve_path(path)
        return path.is_dir
    
    def list_id(self, dir_id, recursive = False):
        dirs = list(self.db.folders(parent_id=dir_id))
        files = list(self.db.files(parent_id=dir_id))   
        dirs_tuples = list()
        for d in dirs:
            dirs_tuples.append((d[1],{'dirs':[],'files':[]}))
        f_items = list()
        for f in files:
            f_items.append(f[1])
        f_items.sort(key=lambda x: x.name)
        dirs_tuples.sort(key=lambda x: x[0].name)
        out = {'dirs':dirs_tuples, 'files':f_items}        
        if recursive:
            rec_dirs = list()
            for (uid,child) in dirs:
                content = self.list_id(uid, recursive=True)
                item = (child,content)
                rec_dirs.append(item) 
            out['dirs'] = rec_dirs
        return out
    
    def list(self, path, recursive = False):
        out = {}
        dir_id = self.db.folder_from_path(path)[0]
        return self.list_id(dir_id,recursive=recursive)
    
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
        self._add_file_in_db(src=s,dst=d)

    def _compute_file_hash(self,f: Path) -> bytes:
        if f.is_symlink():
            target = os.readlink(f)
            digest = self.digest(target.encode('utf8'))
        else:
            digest = self.digest(f.read_bytes())
        logging.debug(pysatl.Utils.hexstr(digest) + ': '+str(f))
        return digest

    def _compute_file_index(self, src:Path, dst: Path = None):
        if dst is None:
            dst = src
        folder_id = self.db.folder_from_path(dst.parent)[0]
        digest = self._compute_file_hash(src)
        mode = int(oct(src.stat().st_mode)[-3:])
        dfi = FileIndex(
            parent_id=folder_id,
            name = dst.name,
            digest = digest,
            mode = mode)
        return dfi
    
    def _compute_dir_index(self, src:Path, dst: Path = None):
        if dst is None:
            dst = src
        folder_id = self.db.folder_from_path(dst.parent)[0]
        mode = int(oct(src.stat().st_mode)[-3:])
        dfi = FolderIndex(
            parent_id=folder_id,
            name = dst.name,
            mode = mode)
        return dfi
    
    def _add_file_in_db(self,src: Path, dst: Path):
        logging.debug('adding file ' + str(src) + ' to ' + str(dst) + ' in archive' + str(self.root_path))
        dfi = self._compute_file_index(src,dst)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_WRITE)
        self.db.add_file(dfi)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_ONLY)
        
    def _add_dir_in_db(self,src: Path, dst: Path):    
        logging.debug('adding dir ' + str(src) + ' to ' + str(dst) + ' in archive' + str(self.root_path))
        dfi = self._compute_dir_index(src=src,dst=dst)
        #self.root_path.joinpath(params.INDEX_FOLDER).chmod(params.READ_WRITE)
        #self.root_path.chmod(params.READ_WRITE)
        #self.db_file.chmod(params.READ_WRITE)
        self.db.add_folder(dfi)
        #self.db_file.chmod(params.READ_ONLY)
        #self.root_path.chmod(params.READ_ONLY)
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
        
        # write the files within the archive
        d_parent.chmod(params.READ_WRITE)
        shutil.copytree(src=s,dst=d,symlinks=True)
        d_parent.chmod(params.READ_ONLY)

        # update index database, in memory for now
        self._add_dir_in_db(src=s,dst=d)

        # add all sub directories and files in DB
        for root,dirs,files in os.walk(d,topdown=True,followlinks=False):
            r = Path(root)
            rel_path = r.relative_to(d)
            src_root = s.joinpath(rel_path)
            for file in files:
                src = src_root.joinpath(file)
                dst = r.joinpath(file)
                self._add_file_in_db(src=src,dst=dst)
            for dir in dirs:
                src = src_root.joinpath(dir)
                dst = r.joinpath(dir)
                self._add_dir_in_db(src=src,dst=dst)

    def delete_file(self, dst:str) -> None:
        logging.info('deleting file ' + str(dst) + ' from archive' + str(self.root_path))
        os.remove(dst)
        (id,f) = self.db.file_from_path(Path(dst))
        self.db.delete_file(id)

    def delete_dir(self, dst:str) -> None:
        logging.info('deleting directory ' + str(dst) + ' from archive' + str(self.root_path))
        FsUtils.rmtree(dst)
        (id,f) = self.db.folder_from_path(dst)
        self.db.delete_folder(id)

    def update_file(self, src: str, dst:str) -> None:
        #self.delete_file(dst)
        #self.add_file(src=src,dst=dst)
        s = Path(src)
        d = Path(dst)
        d_parent = d.parent
        logging.info('updating ' + str(d) + ' with ' + str(s) + ' in archive' + str(self.root_path))
        if not s.exists():
            raise FileNotFoundError(str(s))
        if not s.is_file():
            raise NotAFileError(str(s))
        if not d.exists():
            raise FileNotFoundError(str(d))
        if not d_parent.exists():
            raise FileNotFoundError(str(d_parent))
        (id_f,f) = self.db.file_from_path(d)
        # write the file within the archive
        d_parent.chmod(params.READ_WRITE)
        shutil.copyfile(src=s,dst=d,follow_symlinks=False)
        d_parent.chmod(params.READ_ONLY)
        dfi = self._compute_file_index(s,d)
        self.db.update_file(uid=id_f,val=dfi)

    def move_file(self, src: str, dst:str) -> None:
        s = Path(src).resolve()
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
        (id_dst,f) = self.db.folder_from_path(d_parent)
        (id_f,f) = self.db.file_from_path(s)
        dfi = self._compute_file_index(d)
        assert f.digest == dfi.digest
        assert f.mode == dfi.mode
        self.db.update_file(uid=id_f,val=dfi)

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
        (id_dst,f) = self.db.folder_from_path(d_parent)
        (id_src,f) = self.db.folder_from_path(s)
        dfi = self._compute_dir_index(d)
        assert f.mode == dfi.mode
        self.db.update_folder(uid=id_src,val=dfi)

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
        (id,sfi) = self.db.file_from_path(s)
        self.check_exported_file_integrity(s,d,sfi)

    def check_file_integrity(self, path: Path, file_index: FileIndex):
        dig = self._compute_file_hash(path)
        if file_index.digest != dig:
            raise FileIntegrityError("%s digest:\n%s\nexpected:\n%s"%(
                str(path),
                pysatl.Utils.hexstr(dig),
                pysatl.Utils.hexstr(file_index.digest)
                ))

    def check_exported_file_integrity(self, s: Path, d: Path, file_index: FileIndex):
        try:
            self.check_file_integrity(d,file_index)
        except Exception as e:
            logging.warning(e)
            logging.warning("digest mismatch between DB and destination file %s"%d)
            self.check_file_integrity(s,file_index)
            # retry
            shutil.copyfile(src=s,dst=d,follow_symlinks=False) 
            try:
                self.check_file_integrity(d,file_index)
            except:
                raise Exception("Copy to %s is unreliable"%str(d))   

    def export_dir(self, src: str, dst:str) -> None:
        s = Path(src).resolve()
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
        for root_id,files,dirs in self.db.walk(s):
            root = self.db.path_from_folder_uid(root_id)
            rel_path = root.relative_to(s)
            dst_base = d / rel_path
            for (id,f) in files:
                sf = root / f.name
                df = dst_base / f.name
                self.check_exported_file_integrity(sf,df,f)
            for (id,dir) in dirs:
                dst_dir = dst_base / dir.name
                if not dst_dir.exists():
                    raise FileNotFoundError(dst_dir)
                
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
                dig = hash(dat)
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
                        if hardlink:
                            os.remove(other)
                            os.link(keep,other)
                        else:
                            self.delete_file(other)
                else:
                    index[dig] = file_path
    
    def check(self):
        for root_id,files,dirs in self.db.walk(self.root_path):
            root = self.db.path_from_folder_uid(root_id)
            # get rid of UIDs
            files = list(map(lambda x: x[1].name, files))
            dirs = list(map(lambda x: x[1].name, dirs))
            fs_files=[]
            fs_dirs=[]
            # check files and directories in FS are in DB
            for fs_entry in root.iterdir():
                if fs_entry.is_file():
                    fs_files.append(fs_entry)
                    if fs_entry.name not in files:
                        raise FileExistsError(str(fs_entry)+' not in DB as a file')
                elif fs_entry.is_dir():
                    fs_dirs.append(fs_entry)
                    if fs_entry.name not in dirs:
                        if fs_entry != self.index_dir:
                            raise FileExistsError(str(fs_entry)+' not in DB as a directory')
                elif fs_entry.is_symlink():
                        #happens when the symlink is broken
                        fs_files.append(fs_entry)
                        if fs_entry.name not in files:
                            raise FileExistsError(str(fs_entry)+' not in DB as a file (broken link ?)')
                else:
                    logging.debug(f"fs_entry={fs_entry}")
                    logging.debug(f"fs_entry.is_file()={fs_entry.is_file()}")
                    logging.debug(f"fs_entry.is_dir()={fs_entry.is_dir()}")
                    logging.debug(f"fs_entry.is_symlink()={fs_entry.is_symlink()}")
                    raise RuntimeError(str(fs_entry)+' not a file nor a dir nor a symlink!')
                
            # check files and directories in DB are in FS
            for f in files:
                sf = root / f
                # check that the file exist
                if sf not in fs_files:
                    raise FileNotFoundError(sf)
                # check its content match the digest in DB    
                uid,dfi = self.db.file_from_path(sf)
                self.check_file_integrity(sf,dfi)
            
            for d in dirs:
                sd = root / d
                # check the directory exist in FS
                if sd not in fs_dirs:
                    raise DirectoryNotFoundError(sd)