import threading

import numpy
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
from typing import Sequence, Union


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


class HitObject:
    def __init__(self, x, y, offset, objtype, hitsound=0, objectParams="", hitSample=""):
        self.x = int(x)
        self.y = int(y)
        self.offset = int(offset)
        self.objtype = objtype
        self.hitsound = hitsound
        self.objectParams = objectParams
        self.hitSample = hitSample


class Map:
    def __init__(self, path: str):
        self.path = path
        self.beatmap = MapParser(self.path)
        self.background = dict(self.beatmap.events)['0'][1].replace('"', '')
        self.sr_list = calculateStarRating(
            filepath=self.path, allCombinations=True)
        self.hitObjects = self.ParseHitObjectData()
        self.nm_sr = self.sr_list['nomod']
        ar = float(self.beatmap.difficulty["ApproachRate"])
        self.preempt = 1200 + 600 * \
            (5 - ar) / 5 if ar < 5 else 1200 - 750 * (ar - 5) / 5
        self.fadein = 800 + 400 * \
            (5 - ar) / 5 if ar < 5 else 800 - 500 * (ar - 5) / 5

    def ParseHitObjectData(self) -> list:
        hitObjects = []
        for i in self.beatmap.hitobjects:
            _ho = i.split(",")
            hitObjects.append(
                HitObject(_ho[0], _ho[1], _ho[2], _ho[3]))
        return hitObjects


class Mapset:
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


class Cache:
    def __init__(self, version: int, MapArray: Sequence):
        self.Version = version
        self.Mapsets = MapArray


class MapCollector:
    CacheVersion = 1

    def __init__(self, pathTo: str = "maps/*", isCachingEnabled=True):
        self.path = pathTo
        self._maps = []
        self._cachedPaths = []
        self.isCachingEnabled = isCachingEnabled

    def Collect(self) -> None:
        if os.path.isfile('maps.cache') and self.isCachingEnabled:
            self.LoadCache()

        for mapset in glob(self.path, recursive=True):
            if mapset.split("\\")[1] != "Failed" and not (hashlib.md5(mapset.encode()).hexdigest() in self._cachedPaths):
                self._maps.append(Mapset(mapset))
        self._maps = [x for x in self._maps if x is not None]

        del self._cachedPaths
        gc.collect()
        if self.isCachingEnabled:
            self.CacheSave()

    def GetMapset(self, index: int) -> Mapset:
        return self._maps[index] if len(self._maps) > index else None

    def GetRandomMapset(self) -> Mapset:
        return random.choice(self._maps)

    def GetRandomMap(self) -> Map:
        try:
            return self.GetRandomMapset().GetRandomDifficulty()
        except Exception as err:
            try:
                raise err
            except IndexError:
                print("No maps found.")
                return
            return self.GetRandomMap()

    def LoadCache(self):
        try:
            print("Loading maps from cache... ", end="")
            with open('maps.cache', 'rb') as c:
                CacheData = list(np.load(c, allow_pickle=True))[0]
                if(type(CacheData) != Cache):
                    print("Outdated.")
                    return
                if CacheData.Version < self.CacheVersion:
                    print("Outdated.")
                    return
                self._maps = CacheData.Mapsets
                self._cachedPaths = [hashlib.md5(
                    x.path.encode()).hexdigest() for x in self._maps]
            print("Done.")
        except Exception as err:
            print("Failed.")

    def CacheSave(self):
        print("Saving maps to cache... ", end="")
        with (open('maps.cache', 'wb') as c, open('maps.cache.bak', 'wb') as b):
            np.save(c, [Cache(self.CacheVersion, np.array(self._maps))])
            np.save(b, [Cache(self.CacheVersion, np.array(self._maps))])
        print("Done.")


class Game:
    osu_pixel_playfield = (640, 512)

    def __init__(self, size: Sequence[int], gamemode: Gamemode, isBorderless: bool = False, isCachingEnabled=True):
        self.size = size
        w = size[0]*0.8
        h = size[1]*0.8
        self.playfield_size = (h/self.osu_pixel_playfield[1]*self.osu_pixel_playfield[0], h) \
            if w/self.osu_pixel_playfield[0]*self.osu_pixel_playfield[1] > h \
            else (w, w/self.osu_pixel_playfield[0]*self.osu_pixel_playfield[1])
        self.osu_pixel_multiplier = self.playfield_size[0] / self.osu_pixel_playfield[0]
        self.isBorderless = isBorderless
        self.gamemode = gamemode
        self.MapCollector = MapCollector(isCachingEnabled=isCachingEnabled)
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
        original_hitcircle = pygame.image.load(r'resources\\hitcircle.png')
        hitcircle = None  # defined when a new song is loaded

        placement_offset = [round((self.size[i] - self.playfield_size[i]) / 2) for i in (0, 1)]

        pekoraAngle = 0
        pekoraSpinning = True
        _currentMapOffset = 0
        _firstCircleOffset = -1
        _lastCircleOffset = 1
        DisplayDebug = True
        beatmap_started = False

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.current_map = self.MapCollector.GetRandomMap()
                        if self.current_map == None:
                            continue
                        _firstCircleOffset = self.current_map.hitObjects[0].offset
                        _lastCircleOffset = self.current_map.hitObjects[-1].offset
                        size = (
                            54.4 - 4.48 * float(self.current_map.beatmap.difficulty["CircleSize"])) * 2*self.osu_pixel_multiplier
                        hitcircle = pygame.transform.scale(
                            original_hitcircle, (size, size))
                        pekoraSpinning = False
                        _currentMapOffset = 0
                    if event.key == pygame.K_d:
                        DisplayDebug = not DisplayDebug
                    if event.key == pygame.K_SPACE:
                        if _currentMapOffset < _firstCircleOffset-3000:
                            _currentMapOffset = _firstCircleOffset-2500

            self.window.fill((0, 0, 0))
            text_surface = font.render(
                f'Map: {self.current_map.beatmap.metadata["Artist"]} - {self.current_map.beatmap.metadata["Title"]} [{self.current_map.beatmap.metadata["Version"]}] ({self.current_map.beatmap.metadata["Creator"]}) {round(self.current_map.nm_sr, 2)}*, AR: {self.current_map.beatmap.difficulty["ApproachRate"]}, CS: {self.current_map.beatmap.difficulty["CircleSize"]}' if self.current_map != None else "No map loaded.", False, (255, 255, 255))
            offsetRender = font.render(
                f'Offset: {_currentMapOffset} / First HitObject: {_firstCircleOffset} / Last HitObject: {_lastCircleOffset}', False, (255, 255, 255))
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

            if self.current_map is not None:
                _currentMapOffset += self.clock.get_time(
                ) if beatmap_started else self.current_map.hitObjects[0].offset - self.current_map.preempt
                if beatmap_started is False:
                    beatmap_started = True
                for i in self.current_map.hitObjects:
                    if i.offset - self.current_map.preempt <= _currentMapOffset <= i.offset:
                        # Time at which circle becomes 100% opacity
                        clear = i.offset - self.current_map.preempt + self.current_map.fadein
                        hitcircle.set_alpha(255 if _currentMapOffset >= clear else 255 - round(
                            (clear - _currentMapOffset) / self.current_map.fadein * 255))
                        size = hitcircle.get_rect()
                        self.window.blit(hitcircle, (i.x*self.osu_pixel_multiplier + placement_offset[0], i.y*self.osu_pixel_multiplier + placement_offset[1]))

            if DisplayDebug:
                self.window.blit(text_surface, (0, 0))
                self.window.blit(offsetRender, (0, 21))
                self.window.blit(tickRender, (0, 42))

            if _currentMapOffset > _lastCircleOffset+3000:
                self.current_map = None
                # TO-DO: Should initialize a new map here.
                # But I'll do that later, because I'll revamp all that shit :Chatting:

            pygame.display.update()
            self.clock.tick(1000)

        pygame.time.wait(10)
        pygame.quit()
