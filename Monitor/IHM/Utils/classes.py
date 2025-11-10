import threading
from time import sleep, time


class AsyncThreading:
    def __init__(self, callback, interval=0.01):
        self.callback  = callback
        self.interval  = interval
        self.startTime = 0
        self.running = True  
        self.thread = threading.Thread(target=self.handleThread, daemon=True)
        self.thread.start()

    def handleThread(self):
        while self.running:
            sleep(0.01)

            if time() - self.startTime < self.interval:
                continue
            
            self.startTime = time()
            self.callback()

    def stop(self):
        self.running = False
        self.thread.join()

