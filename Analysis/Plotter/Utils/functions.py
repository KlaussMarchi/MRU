from Utils.variables import pythonColors
from time import sleep


def sendEvent(eventType, message, delay=0.0, color='blue'):
    status = True if eventType == 'success' else False if eventType == 'error' else None
    color  = pythonColors[color]
    reset  = pythonColors['white']
    
    print(f'{color}[{eventType}]{reset}', message)
    if delay > 0.0: sleep(delay)
    return status
