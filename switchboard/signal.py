from pydbus import SystemBus
from gi.repository import GLib
import threading
import os

bus = SystemBus()
signal = bus.get('org.asamk.Signal')

class Signal(threading.Thread):
    def __init__(self, number, sb):
        super().__init__()
        self.number = number
        self.sb = sb

    def send(self, message):
        os.system(f'dbus-send --system --type=method_call --print-reply --dest="org.asamk.Signal" /org/asamk/Signal org.asamk.Signal.sendMessage string:"{message}" array:string: string:+{self.number}')

    def receive_signal(self, timestamp, source, groupID, message, attachments):
        source = source.strip("+")
        self.sb.send(message, source)

    def run(self):
        loop = GLib.MainLoop()
        signal.onMessageReceived = self.receive_signal
        loop.run()