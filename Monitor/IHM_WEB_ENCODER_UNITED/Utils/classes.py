import threading
from time import sleep, time
from pynput import keyboard


class KeyboardListener:
    """
    Classe geral para monitorar teclas pressionadas de forma assíncrona.

    - start()  -> inicia o listener em thread separada
    - stop()   -> para o listener
    - is_pressed('a') -> True se a tecla 'a' estiver pressionada
    - is_key(keyboard.Key.space) -> True se a tecla especial estiver pressionada
    """

    def __init__(self, stop_key=keyboard.Key.esc, normalize_chars=True):
        # Conjunto com as teclas atualmente pressionadas
        self._pressed = set()
        self._stop_key = stop_key
        self._normalize_chars = normalize_chars
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._running = False

    def _on_press(self, key):
        try:
            char = key.char
            if char is not None and self._normalize_chars:
                char = char.lower()
            self._pressed.add(char)
        except AttributeError:
            # Tecla especial (ex: Key.space, Key.enter, etc.)
            self._pressed.add(key)

    def _on_release(self, key):
        try:
            char = key.char
            if char is not None and self._normalize_chars:
                char = char.lower()
            self._pressed.discard(char)
        except AttributeError:
            self._pressed.discard(key)

        # Se apertar a tecla de parar, encerra o listener
        if key == self._stop_key:
            self.stop()

    def start(self):
        """Inicia o listener em thread separada."""
        if not self._running:
            self._listener.start()
            self._running = True

    def stop(self):
        """Para o listener."""
        if self._running:
            self._listener.stop()
            self._running = False

    def is_pressed(self, char: str) -> bool:
        """
        Verifica se uma tecla de caractere está pressionada.
        Ex: is_pressed('a'), is_pressed('1')
        """
        if self._normalize_chars:
            char = char.lower()
        return char in self._pressed

    def is_key(self, key) -> bool:
        """
        Verifica se uma tecla especial está pressionada.
        Ex: is_key(keyboard.Key.space)
        """
        return key in self._pressed

    @property
    def running(self):
        return self._running


class AsyncThreading:
    def __init__(self, callback, interval=0.01):
        self.kb = KeyboardListener()
        self.kb.start()

        self.callback  = callback
        self.interval  = interval
        self.startTime = 0
        self.running = True  
        self.thread = threading.Thread(target=self.handleThread, daemon=True)
        self.thread.start()
        

    def handleThread(self):
        while self.running and self.kb.running:
            sleep(0.01)

            if self.kb.is_pressed('q'):
                break

            if time() - self.startTime < self.interval:
                continue
            
            self.startTime = time()
            self.callback()

    def stop(self):
        self.running = False
        self.thread.join()

