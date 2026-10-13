"""Imported first by every test module: any network connection attempt fails the test run."""
import socket

class NetworkBlocked(RuntimeError):
    pass

def _blocked(*a, **k):
    raise NetworkBlocked('network access attempted during tests')

socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
