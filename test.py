import time
import threading
import asyncio

class test:
    def __init__(self):
        asyncio.run(self.start_thread())
        #asyncio.to_thread(self.start_thread)
        print('started')
        #MD.initialize()
        #th = threading.Thread(target=self.start_thread)
        #th.start()

    async def start_thread(self):
        #task = asyncio.create_task(self.hello("Taro"))
        await asyncio.to_thread(self.hello("Taro"))
        print('ok')
        await asyncio.sleep(2)
        print('done')

    async def hello(self, name: str, wait_time: int = 2):
        print('Hello ...')
        await asyncio.sleep(wait_time)
        print(f'{name}!')

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
