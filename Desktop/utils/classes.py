import threading
from time import sleep, time
from utils.functions import sendEvent


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

class CustomForms:
    options = []

    def set(self, options=[]):
        self.options = []
        
        for i, (value, label) in enumerate(options.items()):
            data = {'id': i+1, 'value': value, 'label': label}
            self.options.append(data)

    def getChoice(self, question, target='value'):
        choice = input(question).strip().replace(' ', '').replace('\t', '')

        if not choice.isnumeric():
            choice = len(self.options) - 1

        choice   = int(choice)
        selected = self.options[-1]['value']

        for option in self.options:
            if option['id'] == choice:
                selected = option

        sendEvent('selecionado', selected['label'], color='orange', end='\n\n')
        return selected[target]

    def get(self, title='selecione uma opção', target='value'):
        question = '\n' + title + ': \n'

        for option in self.options:
            question += f"  [{option['id']}] {option['label']}\n"

        question += '  digite: '
        return self.getChoice(question, target)
    
    def getBool(self, title='deseja continuar?', sep=True):
        question = '\n' if sep else ''
        question += title + '\n'

        for i, option in enumerate(['sim', 'não']):
            question += f"  [{i+1}] {option}\n"

        question += '  digite: '
        return input(question).strip() != '2'
