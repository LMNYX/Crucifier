import threading
import pygame
import time
import numpy as np
from enum import Enum
from glob import glob
import random
from map_parser.map_parser import MapParser
from osu_sr_calculator import calculateStarRating
from based import *
import os


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
            maps.append(Map(map_path))
        return maps

    def GetRandomDifficulty(self):
        return random.choice(self.maps)


class MapCollector:
    def __init__(self, pathTo: str = "maps/*"):
        self.path = pathTo

    def Collect(self) -> None:
        self._maps = [Mapset(x) if x.split("\\")[1] != "Failed" else None
                      for x in glob(self.path, recursive=True)]

    def GetMapset(self, index: int) -> Mapset:
        return self._maps[index] if len(self._maps) > index else None

    def GetRandomMapset(self) -> Mapset:
        return random.choice(self._maps)

    def GetRandomMap(self) -> Map:
        return self.GetRandomMapset().GetRandomDifficulty()


class Game:
    def __init__(self, size: int, gamemode: Gamemode, isBorderless: bool = False):
        self.size = size
        self.isBorderless = isBorderless
        self.gamemode = gamemode
        self.MapCollector = MapCollector()
        self.MapCollector.Collect()
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
