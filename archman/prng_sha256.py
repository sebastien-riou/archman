from hashlib import sha256
from pysatl import Utils

class PrngSha256(object):
    BLOCK_SIZE = 32

    def __init__(self,seed = 0):
        self._state = bytearray()
        self._buf = bytearray()
        self.seed(seed)

    def seed(self, seed):
        try:
            self._state = bytearray(seed)
        except:
            self._state = seed.to_bytes(byteorder='little')
        self._buf = bytearray()

    def getstate(self,state):
        self._state = state
        consumed = len(state) - PrngSha256.BLOCK_SIZE
        buf_len = PrngSha256.BLOCK_SIZE - consumed
        self._buf = self._state[consumed:PrngSha256.BLOCK_SIZE]

    def setstate(self):
        return self._state

    def _step(self):
        self._buf = sha256(self._state).digest()
        self._state = self._buf

    def _get(self, n: int) -> bytes:
        """get at most n bytes from internal buffer and sync the state"""
        out = self._buf[0:n]
        self._buf = self._buf[n:]
        self._state += out
        return out

    def randbytes(self, n: int) -> bytes:
        out = self._get(n)
        remaining = n - len(out)
        while remaining > 0:
            self._step()
            out += self._get(remaining)
            remaining = n - len(out)
        return out
    
    def randint(self, a, b):
        delta = b - a
        nbytes = (delta.bit_length() + 7) // 8
        b = self.randbytes(nbytes)
        i = int.from_bytes(b,byteorder='little')
        out = a + (i % delta)
        return out

    