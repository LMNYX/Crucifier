import threading
import pygame
import time
import numpy as np
from enum import Enum
from glob import glob
import random
import hashlib
from map_parser.map_parser import MapParser
from osu_sr_calculator import calculateStarRating
from based import *
import os
import gc


class Gamemode(Enum):
    STD = 0
    MANIA = 1
    TAIKO = 2
    CTB = 3  # NOBODY GIVES A FUCK ABOUT IT.


class Logic:
    def __init__(self, size: int):
        self._size = size
        self.lock = threading.Lock()
        self.input_list = []

    def _loop(self):
        time.sleep(0.5)

        while True:
            time.sleep(0.01)

    def start_loop(self):
        threading.Thread(target=self._loop, args=(), daemon=True).start()


class Map(object):
    def __init__(self, path: str):
        self.path = path
        self.beatmap = MapParser(self.path)
        self.background = dict(self.beatmap.events)['0'][1].replace('"', '')
        self.sr_list = calculateStarRating(
            filepath=self.path, allCombinations=True)
        self.nm_sr = self.sr_list['nomod']


class Mapset(object):
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.maps = self.load_maps()

    def load_maps(self):
        maps = []
        for map_path in glob(self.path + '/*.osu'):
            try:
                maps.append(Map(map_path))
            except Exception as e:
                print(
                    f"Caught exception while importing a map: {str(e)}. Skipping it...\n \
Problematic map: {map_path}")
                continue
        return maps

    def GetRandomDifficulty(self):
        return random.choice(self.maps)


class MapCollector:
    def __init__(self, pathTo: str = "maps/*"):
        self.path = pathTo
        self._maps = []
        self._cachedPaths = []

    def Collect(self) -> None:
        if os.path.isfile('maps.cache'):
            self.LoadCache()

        for mapset in glob(self.path, recursive=True):
            if mapset.split("\\")[1] != "Failed" and not (hashlib.md5(mapset.encode()).hexdigest() in self._cachedPaths):
                self._maps.append(Mapset(mapset))
        self._maps = [x for x in self._maps if x is not None]

        del self._cachedPaths
        gc.collect()

    def GetMapset(self, index: int) -> Mapset:
        return self._maps[index] if len(self._maps) > index else None

    def GetRandomMapset(self) -> Mapset:
        return random.choice(self._maps)

    def GetRandomMap(self) -> Map:
        return self.GetRandomMapset().GetRandomDifficulty()

    def LoadCache(self):
        print("Loading maps from cache... ", end="")
        with open('maps.cache', 'rb') as c:
            self._maps = list(np.load(c, allow_pickle=True))
            self._cachedPaths = [hashlib.md5(
                x.path.encode()).hexdigest() for x in self._maps]
        print("Done.")

    def CacheSave(self):
        print("Saving maps to cache... ", end="")
        with (open('maps.cache', 'wb') as c, open('maps.cache.bak', 'wb') as b):
            np.save(c, np.array(self._maps))
            np.save(b, np.array(self._maps))
        print("Done.")


class Game:
    def __init__(self, size: int, gamemode: Gamemode, isBorderless: bool = False):
        self.size = size
        self.isBorderless = isBorderless
        self.gamemode = gamemode
        pygame.init()
        pygame.display.set_caption(
            f"osu!simulation {'[b]' if isBorderless else ''}")

        self.window = pygame.display.set_mode(
            size, pygame.NOFRAME if isBorderless else 0)
        self.logic = Logic(np.array(size))
        self.running = True

    def Start(self):
        pygame.display.update()
        self.logic.start_loop()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            with self.logic.lock:
                self.window.fill((0, 0, 0))

                pygame.display.update()

        pygame.time.wait(10)
        pygame.quit()

    def LoadMap(self, map: Map):
        return
