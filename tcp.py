import socket
import threading
from config import Configuration
from multiprocessing import Process

class TCPServer(Process):

    def __init__(self, handler, patchers, ip=Configuration.IP_ADDR, port=Configuration.MSN_PORT, listeners=Configuration.listeners):
        super().__init__()
        self.handler = handler
        self.patchers = patchers
        self.ip = ip
        self.port = port
        self.listeners = listeners
        
    def run(self):
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _sock.bind((self.ip, self.port))
        _sock.listen(self.listeners)
        connections = []
        try:
            while True:
                connection, client_address = _sock.accept()
                t = threading.Thread(target=Connection, args=[self.handler, self.patchers, connection, client_address])
                t.start()
                connections.append(t)
        finally:
            if _sock:
                _sock.close()
            for t in connections:
                t.join()

class Connection():
    def __init__(self, handler, patchers, connection, client_address):
        self.connection = connection
        self.client_address = client_address
        self.handler = handler()
        self.patchers = []
        self.username = None
        self.status = "FLN"
        for patcher in patchers:
            self.add_patcher(patcher)
        self.recv_loop()
        
    def recv_loop(self):
        while True:
            data = self.connection.recv(1024)
            if data:
                decoded = data.decode("utf-8")
                if Configuration.debug:
                    print(f"{self.get_address()[1]}: received '{decoded.strip('\r\n')}' from {self.client_address}")
                self.handler.handle(decoded)
            else:
                self.connection.close()
                return

    def get_address(self):
        return self.connection.getsockname()

    def add_patcher(self, patcher):
        p = patcher(self)
        self.patchers.append(p)
        p.patch(self.handler)

    def tell(self, cmd):
        self.handler.handle(cmd)

    def send(self, string):
        self.connection.sendall(f"{string}\r\n".encode("utf-8"))
        if Configuration.debug:
            print(f"{self.get_address()[1]}: sent '{string}' to {self.client_address}")

    def error(self, errno, trid):
        self.send(f"{errno} {trid}")
    
    def send_multi_line(self, strings):
        concat_string = "".join([f"{k}\r\n" for k in strings])
        self.connection.sendall(concat_string.encode("utf-8"))
        if Configuration.debug:
            print(f"{self.get_address()[1]}: sent '{concat_string}' to {self.client_address}")
