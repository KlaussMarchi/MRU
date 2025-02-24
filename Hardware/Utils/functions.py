from time import sleep


def sendEvent(eventType, message, delay=0.0):
    status = None

    if eventType == 'error':
        print(f'\033[31m[error]\033[0m', message)
        status = False
    elif eventType == 'success':
        print(f'\033[34m[success]\033[0m', message)
        status = True
    else:
        print(f'\033[32m[event]\033[0m', message)

    if delay > 0.0:
        sleep(delay)

    return status

