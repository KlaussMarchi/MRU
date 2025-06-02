import requests


def getWebData(url, route, timeout=5):
    URL = url + route
    response = None

    try:
        response = requests.get(URL, timeout=timeout).json()
    except Exception as error:
        print('error:', error)

    return response 


class Server:
    def __init__(self):
        self.URL = 'http://192.168.0.25/'

    def getData(self):
        return getWebData(self.URL, 'INFO', timeout=10)
    