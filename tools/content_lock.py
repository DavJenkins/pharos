"""Cooperate with a recovery coordinator without bypassing the real flock."""
import fcntl
import os

def inherited_descriptor(stream=None):
    value=os.environ.get('DATAARK_CONTENT_LOCK_FD')
    if value is None:return None
    descriptor=int(value)
    expected=os.stat('/var/lib/dataark/updates/worker.lock') if stream is None else os.fstat(stream.fileno())
    actual=os.fstat(descriptor)
    if (actual.st_dev,actual.st_ino)!=(expected.st_dev,expected.st_ino):raise ValueError('Inherited lock is not the content worker lock')
    # flock on the inherited open-file description must succeed. A different
    # process's conflicting lock is never ignored.
    fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
    return descriptor

def acquire(stream):
    if inherited_descriptor(stream) is None:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
