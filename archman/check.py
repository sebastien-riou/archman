import os
import hashlib 

class RepairInfo(object):
    def __init__(self, path, target_path, *, create = False):
        self.path = path
        self.target_path = target_path

        if not os.path.exists(target_path):
            raise FileNotFoundError(target_path)
        
        if create:
            if os.path.exists(path):
                raise FileExistsError(path)
            with open(path,'wb') as fo:
                with open(target_path,'rb') as fi:
                    # dummy implementation: just compute sha256 over the whole file
                    digest = hashlib.sha256(fi.read()).digest()
                    fo.write(digest)
        else:
            if not os.path.exists(path):
                raise FileNotFoundError(path)

            with open(target_path,'rb') as fi:
                # dummy implementation: just compute sha256 over the whole file
                digest = hashlib.sha256(fi.read()).digest()
            
            with open(path,'rb') as fi:
                # dummy implementation: just compute sha256 over the whole file
                ref_digest = fi.read()
            
            assert digest == ref_digest
            