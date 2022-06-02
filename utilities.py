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


class HitObject(object):
    def __init__(self, x, y, offset, objtype, hitsound=0, objectParams="", hitSample=""):
        self.x = int(x)
        self.y = int(y)
        self.offset = int(offset)
        self.objtype = objtype
        self.hitsound = hitsound
        self.objectParams = objectParams
        self.hitSample = hitSample


class Map(object):
    def __init__(self, path: str):
        self.path = path
        self.beatmap = MapParser(self.path)
        self.background = dict(self.beatmap.events)['0'][1].replace('"', '')
        self.sr_list = calculateStarRating(
            filepath=self.path, allCombinations=True)
        self.hitObjects = self.ParseHitObjectData()
        self.nm_sr = self.sr_list['nomod']

    def ParseHitObjectData(self) -> list:
        hitObjects = []
        for i in self.beatmap.hitobjects:
            _ho = i.split(",")
            hitObjects.append(
                HitObject(_ho[0], _ho[1], _ho[2], _ho[3]))
        return hitObjects


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
        self.CacheSave()

    def GetMapset(self, index: int) -> Mapset:
        return self._maps[index] if len(self._maps) > index else None

    def GetRandomMapset(self) -> Mapset:
        return random.choice(self._maps)

    def GetRandomMap(self) -> Map:
        try:
            return self.GetRandomMapset().GetRandomDifficulty()
        except Exception as err:
            return self.GetRandomMap()

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
        self.MapCollector = MapCollector()
        self.MapCollector.Collect()
        self.current_map = None
        pygame.init()
        pygame.display.set_caption(
            f"osu!simulation {'[b]' if isBorderless else ''}")
        self.clock = pygame.time.Clock()
        self.window = pygame.display.set_mode(
            size, pygame.NOFRAME if isBorderless else 0)
        self.running = True

    def Start(self):
        pygame.display.update()
        pygame.font.init()

        # Temporary resources. TO-DO: Make it better.
        font = pygame.font.SysFont("Times New Roman", 16)
        pekoraSpin = pygame.image.load(r'resources\\pekora.png')
        pekoraSpin = pygame.transform.scale(pekoraSpin, (128, 128))

        pekoraAngle = 0
        pekoraSpinning = True
        _test = 0
        DisplayDebug = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.current_map = self.MapCollector.GetRandomMap()
                        pekoraSpinning = False
                        _test = 0
                    if event.key == pygame.K_d:
                        DisplayDebug = not DisplayDebug

            self.window.fill((0, 0, 0))
            text_surface = font.render(
                f'Map: {self.current_map.beatmap.metadata["Artist"]} - {self.current_map.beatmap.metadata["Title"]} [{self.current_map.beatmap.metadata["Version"]}] ({self.current_map.beatmap.metadata["Creator"]}) {self.current_map.nm_sr}*' if self.current_map != None else "No map loaded.", False, (255, 255, 255))
            offsetRender = font.render(
                f'Offset: {_test}', False, (255, 255, 255))
            tickRender = font.render(
                f'pygame.time.get_ticks(): {pygame.time.get_ticks()}', False, (255, 255, 255))
            if pekoraSpinning:
                rotated_image = pygame.transform.rotate(
                    pekoraSpin, pekoraAngle)
                self.window.blit(rotated_image, rotated_image.get_rect(
                    center=pekoraSpin.get_rect(topleft=(self.size[0]/2-64, self.size[1]/2-64)).center).topleft)
                if pekoraAngle > 360:
                    pekoraAngle = 0
                else:
                    pekoraAngle += 0.555

            hitcricle = pygame.image.load(r'resources\\hitcircle.png')
            if self.current_map is not None:
                _test += self.clock.get_time()
                for i in self.current_map.hitObjects:
                    if _test-1000 <= i.offset <= _test :
                        hitcricle.set_alpha(
                            300 + 255 + (i.offset-_test) if i.offset-_test < 0 else 0)
                        self.window.blit(hitcricle, hitcricle.get_rect(
                            center=hitcricle.get_rect(topleft=(i.x-64, i.y-64)).center).topleft)

            if DisplayDebug:
                self.window.blit(text_surface, (0, 0))
                self.window.blit(offsetRender, (0, 21))
                self.window.blit(tickRender, (0, 42))

            pygame.display.update()
            self.clock.tick(1000)

        pygame.time.wait(10)
        pygame.quit()
