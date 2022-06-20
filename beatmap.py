from map_parser.map_parser import MapParser
from osu_sr_calculator import calculateStarRating
from glob import glob
from cache import Cache
import os
import random
import hashlib
from slider import beatmap
import gc
import numpy as np
import traceback

# Overwriting HitObject object to add a new comparison functions.
beatmap.HitObject.is_circle = lambda self: self.type_code == 1
beatmap.HitObject.is_slider = lambda self: self.type_code == 2
beatmap.HitObject.is_spinner = lambda self: self.type_code == 8
beatmap.HitObject.is_holdnote = lambda self: self.type_code == 128


class HitObject:
    def __init__(self, x, y, offset, objtype, hitsound=0, object_params="", hit_sample=""):
        self.x = int(x)
        self.y = int(y)
        self.offset = int(offset)
        self.objtype = objtype
        self.hitsound = hitsound
        self.objectParams = object_params
        self.hitSample = hit_sample


class Map:
    def __init__(self, path: str):
        self.path = path
        self.beatmap = MapParser(self.path)
        self.background = dict(self.beatmap.events)['0'][1].replace('"', '')
        try:
            self.sr_list = calculateStarRating(
                filepath=self.path, allCombinations=True)
            self.nm_sr = self.sr_list['nomod']
        except AttributeError as e:
            # TODO: Consider using osu!api v2 to get the star rating of the map if it's submitted [use osu.py ;)]
            print(f"Failed to load {self.beatmap.metadata['Artist']} - {self.beatmap.metadata['Title']} [{self.beatmap.metadata['Version']}]:\n"
                  f"    {e}")
            self.sr_list = {}
            self.nm_sr = 0
        with open(self.path, 'r', encoding='utf-8') as osu_file:
            self.hit_objects = beatmap.Beatmap.from_file(
                osu_file).hit_objects()


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
                print(f"Caught exception while importing a map: {traceback.format_exc()}. "
                      f"Skipping it...\n Problematic map: {map_path}")
                continue
        return maps

    def get_random_difficulty(self):
        return random.choice(self.maps)


class MapCollector:
    cache_version = 3

    def __init__(self, path_to: str = "maps/*", is_caching_enabled=True, should_reset_cache=False):
        self.path = path_to
        self._maps = []
        self._cached_paths = []
        self.is_caching_enabled = is_caching_enabled
        self.should_reset_cache = should_reset_cache

    def collect(self) -> None:
        if os.path.isfile('maps.cache') and self.is_caching_enabled and not self.should_reset_cache:
            self.load_cache()

        for mapset in glob(self.path, recursive=True):
            if mapset.split("\\")[1] != "Failed" and not (hashlib.md5(mapset.encode()).hexdigest() in self._cached_paths):
                np.append(self._maps, Mapset(mapset))
        self._maps = [x for x in self._maps if x is not None]

        del self._cached_paths
        gc.collect()
        if self.is_caching_enabled:
            self.save_cache()

    def get_mapset(self, index: int) -> Mapset:
        return self._maps[index] if len(self._maps) > index else None

    def get_random_mapset(self) -> Mapset:
        return random.choice(self._maps)

    def get_random_map(self) -> Map:
        return self.get_random_mapset().get_random_difficulty()

    def load_cache(self):
        try:
            print("Loading maps from cache... ", end="")
            with open('maps.cache', 'rb') as c:
                cache_data = list(np.load(c, allow_pickle=True))[0]
                if not isinstance(cache_data, Cache):
                    print("Outdated.")
                    return
                if cache_data.version < self.cache_version:
                    print("Outdated.")
                    return
                self._maps = cache_data.mapsets
                self._cached_paths = [hashlib.md5(
                    x.path.encode()).hexdigest() for x in self._maps]
            print("Done.")
        except Exception as err:
            print(f"Failed to load cache: {err}")

    def save_cache(self):
        print("Saving maps to cache... ", end="")
        for file in (open('maps.cache', 'wb'), open('maps.cache.bak', 'wb')):
            np.save(file, [Cache(self.cache_version, np.array(self._maps))])
            file.close()
        print("Done.")
