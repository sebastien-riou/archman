import sqlite3
from sqlite3 import Error
import os
from pathlib import Path
from typing import Generator
from typing import Tuple
from typing import Iterator
from archman.sqlarchive import params
class DbUtils(object):
    @staticmethod
    def create_connection(db_file, *, create = False):
        """ create a database connection to the SQLite database
            specified by db_file. Raise an error if the file don't exist
        :param db_file: database file
        :return: Connection object or None
        """
        if not os.path.exists(db_file):
            if not create:
                raise FileNotFoundError(db_file)
        else:
            if create:
                raise FileExistsError(db_file)
        conn = sqlite3.connect(db_file)
        return conn

    @staticmethod
    def create_table(conn, create_table_sql):
        """ create a table from the create_table_sql statement
        :param conn: Connection object
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
        except Error as e:
            print(e)

    
    def _results(self, cursor, item=None):
        cur = cursor
        while True:
            res = cur.fetchmany(200)
            if not res:
                break
            for r in res:
                if item is None:
                    yield r
                else:
                    yield r[item]

    def _get_from_uid(self, table, uid):
        cur = self.conn.cursor()
        if uid is None:
            return None
        sql = '''SELECT * FROM %s WHERE UID = ?'''%table
        args = (uid,)
        cur.execute(sql,args)
        res = list(self._results(cur))
        if len(res) != 1:
            raise Exception()
        r  = res[0]
        uid2 = r[0]
        if uid != uid2:
            raise Exception()
        return r

    def _enum_distinct(self,table,field):
        cur = self.conn.cursor()
        sql = '''SELECT DISTINCT %s FROM %s'''%(field,table)
        cur.execute(sql)
        return self._results(cur,0)


class FolderIndex(object):

    def __init__(self, *, parent_id=None, name=None, mode=None):
        self.parent_id = parent_id
        self.name = name
        self.mode = mode

class FileIndex(object):

    def __init__(self, *, parent_id=None, name=None, digest=None, mode=None):
        self.parent_id = parent_id
        self.name = name
        self.digest = digest
        self.mode = mode


class IndexDb(DbUtils):

    def __init__(self, path:str, *,root:str, create = False):
        self.path = path
        self.root = Path(root).resolve()

        # create a database connection
        self.conn = DbUtils.create_connection(path,create=create)
        if self.conn is None:
            raise Exception("cannot connect to database '%s'"%path)

        DbUtils.create_table(self.conn, """ CREATE TABLE IF NOT EXISTS folders (
                                            UID integer PRIMARY KEY,
                                            PARENT_UID integer,
                                            NAME text NOT NULL,
                                            MODE integer NOT NULL,
                                            FOREIGN KEY (PARENT_UID) REFERENCES folders (UID) ON DELETE RESTRICT
                                        ); """)

        DbUtils.create_table(self.conn, """ CREATE TABLE IF NOT EXISTS files (
                                            UID integer PRIMARY KEY,
                                            PARENT_UID integer,
                                            NAME text NOT NULL,
                                            DIGEST blob NOT NULL,
                                            MODE integer NOT NULL,
                                            FOREIGN KEY (PARENT_UID) REFERENCES folders (UID) ON DELETE RESTRICT
                                        ); """)
        
        DbUtils.create_table(self.conn, """ CREATE TABLE IF NOT EXISTS inodes (
                                            UID integer PRIMARY KEY,
                                            NO integer NOT NULL,
                                            DIGEST blob NOT NULL
                                        ); """)
        
        DbUtils.create_table(self.conn, """ CREATE TABLE IF NOT EXISTS hardlinks (
                                            UID integer PRIMARY KEY,
                                            PARENT_UID integer,
                                            NAME text NOT NULL,
                                            USER integer NOT NULL,
                                            INODE_UID integer NOT NULL,
                                            MODE integer NOT NULL,
                                            FOREIGN KEY (PARENT_UID) REFERENCES folders (UID) ON DELETE RESTRICT
                                            FOREIGN KEY (INODE_UID) REFERENCES inodes (UID) ON DELETE RESTRICT
                                        ); """)
        
        if create:
            # create the root directory
            dfi = FolderIndex(
                parent_id=None,
                name = params.ROOT_DIR,
                mode = params.READ_WRITE)
            self.add_folder(dfi)
            self.commit()
    
    def commit(self):
        self.conn.commit() 

    def file_from_uid(self, uid):
        if uid is None:
            return None
        r=self._get_from_uid("files", uid)
        return FileIndex(parent_id=r[1], name=r[2], digest=r[3], mode=r[4])

    def folder_from_uid(self, uid):
        if uid is None:
            return None
        r=self._get_from_uid("folders", uid)
        return FolderIndex(parent_id=r[1], name=r[2], mode=r[3])

    def add_file(self, file: FileIndex):
        args = (
            file.parent_id,
            file.name,
            file.digest,
            file.mode,
            )
        if file.parent_id is None:
            raise ValueError("parent_id cannot be null")
        # TODO: check if it exist already
        cur = self.conn.cursor()
        cur.execute(''' INSERT INTO files(PARENT_UID,NAME,DIGEST,MODE)
              VALUES(?,?,?,?) ''', args)
    
    def update_file(self, uid: int, val: FileIndex):
        args = (
            val.parent_id,
            val.name,
            val.digest,
            val.mode,
            uid,
            )
        if val.parent_id is None:
            raise ValueError("parent_id cannot be null")
        cur = self.conn.cursor()
        cur.execute(''' UPDATE files 
                    SET 
                        PARENT_UID = ?,
                        NAME = ?,
                        DIGEST = ?,
                        MODE = ?
                    WHERE
                        UID = ? 
               ''', args)
    
    def delete_file(self, file_uid):
        cur = self.conn.cursor()
        cur.execute(''' DELETE FROM files WHERE UID=%d'''%file_uid)

    def add_folder(self, f: FolderIndex):
        args = (
            f.parent_id,
            f.name,
            f.mode
            )
        if f.parent_id is None:
            if f.name != params.ROOT_DIR:
                raise ValueError("parent_id cannot be null")
        # TODO: check if it exist already
        cur = self.conn.cursor()
        cur.execute(''' INSERT INTO folders(PARENT_UID,NAME,MODE)
              VALUES(?,?,?) ''', args)
    
    def update_folder(self, uid: int, val: FolderIndex):
        args = (
            val.parent_id,
            val.name,
            val.mode,
            uid,
            )
        if val.parent_id is None:
            if val.name != params.ROOT_DIR:
                raise ValueError("parent_id cannot be null")
        cur = self.conn.cursor()
        cur.execute(''' UPDATE folders
                    SET 
                        PARENT_UID = ?,
                        NAME = ?,
                        MODE = ?
                    WHERE
                        UID = ? 
               ''', args)
    
    @staticmethod
    def file_filter(*, file=None, parent_id=None, name=None, digest=None, mode=None):
        if file is not None:
            if parent_id is None:
                parent_id = file.parent_id
            if name is None:
                name = file.name 
            if digest is None:
                digest = file.digest 
            if mode is None:
                mode = file.mode

        args = ()
        filters = []
        if parent_id is not None:
            filters.append("PARENT_UID = ?")
            args += (parent_id,)
        if name is not None:
            filters.append("NAME = ?")
            args += (name,)
        if digest is not None:
            filters.append("DIGEST = ?")
            args += (name,)
        if mode is not None:
            filters.append("MODE = ?")
            args += (mode,)

        if len(filters):
            return (" WHERE "+" AND ".join(filters), args)
        else:
            return ("",args)

    def files(self, *, parent_id=None, name=None, digest=None, mode=None) -> Generator[Tuple[int,FileIndex],None,None]:
        cur = self.conn.cursor()
        sql = '''SELECT * FROM files'''
        (f,args) = self.file_filter(parent_id=parent_id, name=name, digest=digest, mode=mode)
        sql += f
        cur.execute(sql,args)

        for r in self._results(cur):
            uid = r[0]
            o = FileIndex(parent_id=r[1], name=r[2], digest=r[3], mode=r[4])
            yield (uid, o)

    @staticmethod
    def folder_filter(*, folder=None, parent_id=None, name=None, mode=None):
        if folder is not None:
            if parent_id is None:
                parent_id = folder.parent_id
            if name is None:
                name = folder.name 
            if mode is None:
                mode = folder.mode

        args = ()
        filters = []
        if parent_id is not None:
            filters.append("PARENT_UID = ?")
            args += (parent_id,)
        if name is not None:
            filters.append("NAME = ?")
            args += (name,)
        if mode is not None:
            filters.append("MODE = ?")
            args += (mode,)

        if len(filters):
            return (" WHERE "+" AND ".join(filters), args)
        else:
            return ("",args)

    def folders(self, *, parent_id=None, name=None, mode=None) -> Generator[Tuple[int,FolderIndex],None,None]:
        cur = self.conn.cursor()
        sql = '''SELECT * FROM folders'''
        (f,args) = self.folder_filter(parent_id=parent_id, name=name, mode=mode)
        sql += f
        cur.execute(sql,args)

        for r in self._results(cur):
            uid = r[0]
            folder = FolderIndex(parent_id=r[1], name=r[2], mode=r[3])
            yield (uid, folder)

    def folder_from_path(self, path) -> Tuple[int,FolderIndex]:
        p = Path(path).resolve()
        pr = p.relative_to(self.root)
        parent_id = 1
        parent = None
        for part in pr.parts:
            children = self.folders(parent_id=parent_id)
            found = False
            for (uid,child) in children:
                if part == child.name:
                    parent_id = uid
                    parent = child
                    found = True
                    break
            if not found:
                raise Exception("folder '%s' not found in db, part: '%s'"%(p,part))
        if parent is None:
            # happens for the root directory
            parent = self.folder_from_uid(parent_id)
        return (parent_id,parent)
    
    def file_from_path(self, path: Path) -> Tuple[int,FileIndex]:
        (parent_id,parent) = self.folder_from_path(path.parent)
        res = list(self.files(parent_id = parent_id, name = path.name))
        assert len(res) == 1
        return res[0]

    def path_from_folder_uid(self, folder_uid) -> Path:
        part_id = folder_uid
        parts = list()
        while(part_id is not None):
            di = self.folder_from_uid(part_id)
            parts.append(di.name)
            part_id = di.parent_id
        path = Path(self.root)
        for part in reversed(parts):
            path = path.joinpath(part)
        return path

    def path_from_file_uid(self, file_uid) -> Path:
        fi = self.file_from_uid(file_uid)
        path = self.path_from_folder_id(fi.parent_id)
        path = path.joinpath(fi.name)
        return path

    def walk(self, path):
        (parent_id,parent) = self.folder_from_path(path)
        return self.walk_id(parent_id)
    
    def walk_id(self,parent_id):
        files = list(self.files(parent_id = parent_id))
        dirs = list(self.folders(parent_id = parent_id))
        yield (parent_id,files,dirs)
        for (id,dfi) in dirs:
            yield from self.walk_id(id)

    def delete_folder(self, folder_uid):
        # delete all files
        args = (
                folder_uid,
                )
        cur = self.conn.cursor()
        cur.execute(''' DELETE FROM files
                    WHERE
                        PARENT_UID = ? 
                ''', args)
        # delete all sub folders
        for uid,dir in self.folders(parent_id=folder_uid):
            self.delete_folder(uid)
        # delete folder
        cur.execute(''' DELETE FROM folders
                    WHERE
                        UID = ? 
                ''', args)
    