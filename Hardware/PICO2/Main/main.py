from objects.device.index import device
from objects.tasks.index  import tasks
from objects.processing.index import processing
from objects.sensors.index import sensors
from objects.protocol.index import protocol
import _thread
lock = _thread.allocate_lock()


def thread0():
    while True:
        with lock:
            sensors.handle()
            tasks.print()
            tasks.memory()


def thread1():
    while True:
        with lock:
            processing.handle()
            protocol.handle()
            tasks.blink()


if __name__ == '__main__':
    device.setup()
    sensors.setup()
    processing.setup()
    device.status = tasks.WORKING
    _thread.start_new_thread(thread1, ())
    thread0()
    