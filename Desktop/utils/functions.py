from time import sleep
from time import time as getTime
import sys
import os


def millis():
    return int(getTime()*1000)

def sendEvent(eventType, message, color='blue', delay=0.0, end='\n', top='', repeat=False):
    status = eventType

    pythonColors = {
        'black'     : '\033[30m',
        'red'       : '\033[31m',
        'green'     : '\033[32m',
        'yellow'    : '\033[33m',
        'blue'      : '\033[34m',
        'magenta'   : '\033[35m', 
        'cyan'      : '\033[36m',
        'white'     : '\033[37m',
        'orange'    : '\033[38;5;208m',
        'gray'      : '\033[38;5;244m',
        'light_gray': '\033[38;5;250m',
        'dark_gray' : '\033[38;5;240m',
        'brown'     : '\033[38;5;94m',
        'purple'    : '\033[38;5;129m',
        'reset'     : '\033[0m'
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

    status  = True if eventType == 'success' else False if eventType == 'error' else None
    color   = pythonColors[color]
    reset   = pythonColors['white']

    if repeat:
        print(f'{top}{color}[{eventType}]{reset}', message, f'{color}[{eventType}]{reset}', end=end)
    else:
        print(f'{top}{color}[{eventType}]{reset}', message, end=end)    

    if delay > 0.0: 
        sleep(delay)

    return status


# RETORNA CAMINHO FUNCIONANDO COM PYINSTALLER
def getPath(path):
    try:
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, path)


def getRawStr(string):
    replaceData = ['\r', '\n', '\t', ' ']

    for val in replaceData:
        string = string.replace(val, '')
    
    return string.strip()


def showLogo():
    print('''                                                                                                                                                                                                                
                @@@@@@@@@@@@@@   @@@@@@@@  @@@@@@@@@@@@@@@   @@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@               
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@           @@@@@@@@ @@@@@@@@          @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@              
               @@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
                        @@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@  @@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
               @@@@@@@@@@@@@@@@  @@@@@@@@  @@@@@@@@@@@@@@@@  @@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
                                                    v3.0.0                                                                                                                                                                                               
       '''      
    )

