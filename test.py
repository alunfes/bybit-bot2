import time
import threading

class test:
    def __init__(self):
        MD.initialize()
        th = threading.Thread(target=self.start_thread)
        th.start()

    def start_thread(self):
        while True:
            print('test')
            time.sleep(1)



class MD:
    @classmethod
    def initialize(cls):
        th = threading.Thread(target=cls.start_thread)
        th.start()

    @classmethod
    def start_thread(cls):
        while True:
            print('MD')
            time.sleep(1)

if __name__ == '__main__':
    t = test()
