''' pickleddict.py
    
    the PickledDict class takes a path and creates picke caches there.
    it then presents itself like a dict, and reading and writing to the pickle
    cache is by way of reading and writing to/from the class instance
'''
import pickle, sys
from collections.abc import MutableMapping as DictMixin
from pathlib import Path
from uuid import uuid4

class PickledDict(DictMixin):
    
    def __init__(self,_cache_path:Path=None, **kwargs):
        if _cache_path is None:
            _cache_path = Path(sys.path[0]) / "cache"
            
        _cache_path.mkdir(parents=True, exist_ok=True)
        for extras in _cache_path.iterdir(): 
            extras.unlink()
        self._cache_path = _cache_path

        self.jar = {}
        
        for k,v in kwargs.items():
            self.__setitem__(k,v)

        
    def __setitem__(self, key, item):
        if key in self.jar:
            self.__delitem__(key)

        uuid_file = self._cache_path / uuid4().hex
        uuid_file.write_bytes(pickle.dumps(item))
        self.jar[key] = uuid_file
    
    def __getitem__(self, key):
        if key not in self.jar:
            raise KeyError(key)
            
        return pickle.loads(self.jar[key].read_bytes())
        
    def __delitem__(self, key):
        if key not in self.jar: return
        
        self.jar[key].unlink()
        del self.jar[key]
        
    def __iter__(self):
        return ((k, pickle.loads(self.jar[k].read_bytes())) \
                for k in self.jar)
        
    def __len__(self): 
        return len(self.jar)
    
    def __del__(self):
        ''' clears all files from cache '''
        for uuid_path in self.jar.values():
            uuid_path.unlink()
