from abc import ABC, abstractmethod

class PathAlgo(ABC):
    @abstractmethod
    def search(self, start, end, grid):
        pass