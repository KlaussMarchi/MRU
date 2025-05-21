import threading
from time import sleep


class AsyncThreading:
    def __init__(self, callback):
        self.callback = callback
        self.running = True  
        self.thread = threading.Thread(target=self.handleThread, daemon=True)
        self.thread.start()

    def handleThread(self):
        while self.running:
            self.callback()
            sleep(0.01) 

    def stop(self):
        self.running = False
        self.thread.join()  