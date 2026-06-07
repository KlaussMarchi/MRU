from time import sleep
from time import time as getTime


def millis():
    return int(getTime()*1000)


def sendEvent(eventType, message, color='blue', delay=0.0):
    status = eventType
    
    pythonColors = {
        'blue' : '\033[34m',
        'red'  : '\033[31m',
        'green': '\033[32m',
        'white': '\033[0m', 
    }

    if eventType == 'success':
        status = True
        color  = 'blue'

    if eventType == 'error':
        status = False
        color  = 'red'

    if eventType == 'event':
        status = None
        color = 'green'

    status = True if eventType == 'success' else False if eventType == 'error' else None
    color  = pythonColors[color]
    reset  = pythonColors['white']
    
    print(f'{color}[{eventType}]{reset}', message)
    if delay > 0.0: sleep(delay)
    return status
