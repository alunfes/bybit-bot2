import numpy as np

class RandomGenerator:
    @classmethod
    def getRandomArray(cls, num):
        res = []
        for i in range(num):
            res.append(np.random.randint(-10000, 10000) / 10000)
        return res

    @classmethod
    def getRandomArrayRange(cls, minv, maxv):
        return np.random.randint(minv * 1000, maxv * 1000) / 1000.0