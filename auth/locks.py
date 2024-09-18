from abc import ABC, abstractmethod

#TODO: implement real RW locks
class Lock(ABC):
    def __enter__(self):
        self.acquire_lock()
    def __exit__(self, *args):
        self.release_lock()
    @abstractmethod
    def acquire_lock(self):
        pass
    @abstractmethod
    def release_lock(self):
        pass

class FakeLock(Lock):
    def acquire_lock(self):
        pass
    def release_lock(self):
        pass

class FakeLockWithDestructor(FakeLock):
    def __init__(self, destructor):
        self.destructor = destructor
    def __exit__(self, *args):
        self.destructor()
        self.release_lock()

class FakeRWLock():
    def __init__(self, destructor=None):
        self.read_lock = FakeLock()
        if destructor is None:
            self.write_lock = FakeLock()
        else:
            self.write_lock = FakeLockWithDestructor(destructor)
    def reader_lock(self):
        return self.read_lock
    def writer_lock(self):
        return self.write_lock