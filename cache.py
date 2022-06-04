from typing import Sequence


class Cache:
    def __init__(self, version: int, map_array: Sequence):
        self.version = version
        self.mapsets = map_array
