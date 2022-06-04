import threading
import pygame
import time
from typing import Sequence
from os import path
from constants import *
from enums import Gamemode
from beatmap import MapCollector


class ObjectManager:
    def __init__(self):
        self.hit_objects = None
        self.obj_offset = 0
        self.preempt = 0
        self.fadein = 0

    def load_hit_objects(self, beatmap):
        ar = float(beatmap.beatmap.difficulty["ApproachRate"])
        self.preempt = 1200 + 600 * \
            (5 - ar) / 5 if ar < 5 else 1200 - 750 * (ar - 5) / 5
        self.fadein = 800 + 400 * \
            (5 - ar) / 5 if ar < 5 else 800 - 500 * (ar - 5) / 5
        self.hit_objects = list(beatmap.hit_objects)  # new list object
        self.obj_offset = 0

    def get_hit_objects_for_offset(self, offset):
        index = self.obj_offset
        while True:
            if index == len(self.hit_objects):
                break
            if offset > self.hit_objects[index].offset:
                self.obj_offset += 1
                index += 1
                continue
            if offset < self.hit_objects[index].offset-self.preempt:
                break
            index += 1
            yield self.hit_objects[index-1]

    def get_opacity(self, hit_object, offset):
        # Time at which circle becomes 100% opacity
        clear = hit_object.offset - self.preempt + self.fadein
        return 255 if offset >= clear else 255 - round(
            (clear - offset) / self.fadein * 255)


class GameFrameManager:
    def __init__(self, size, window, clock):
        self.size = size
        self.window = window
        self.clock = clock
        self.font = pygame.font.SysFont("Times New Roman", 16)
        w = size[0] * 0.8
        h = size[1] * 0.8
        self.playfield_size = (h / osu_pixel_window[1] * osu_pixel_window[0], h) \
            if w / osu_pixel_window[0] * osu_pixel_window[1] > h \
            else (w, w / osu_pixel_window[0] * osu_pixel_window[1])
        self.placement_offset = [
            round((size[i] - self.playfield_size[i]) / 2) for i in (0, 1)]
        self.osu_pixel_multiplier = self.playfield_size[0] / \
            osu_pixel_window[0]
        self.object_manager = ObjectManager()
        self.current_map = None
        self.current_offset = 0

        pekora = pygame.image.load(r'resources\\pekora.png')
        self.pekora = pygame.transform.scale(pekora, (128, 128))
        self.pekora_angle = 0

        self.original_hitcircle = pygame.image.load(
            r'resources\\hitcircle.png')
        self.hitcircle = None

        self.background = None

    def load_map(self, beatmap):
        self.current_map = beatmap
        self.object_manager.load_hit_objects(beatmap)
        size = (
            54.4 - 4.48 * float(self.current_map.beatmap.difficulty["CircleSize"])) * 2 * self.osu_pixel_multiplier
        self.hitcircle = pygame.transform.scale(
            self.original_hitcircle, (size, size))
        self.current_offset = self.current_map.hit_objects[0].offset - \
            self.object_manager.preempt - 3000
        self.background = pygame.image.load(
            f"{path.dirname(self.current_map.path)}/{self.current_map.background}")
        self.background = pygame.transform.scale(self.background, (
            self.background.get_size(
            )[0] * (self.size[0] / self.background.get_size()[0]),
            self.background.get_size()[1] * (self.size[1] / self.background.get_size()[1])))

    @property
    def can_skip(self):
        return self.current_offset < self.current_map.hit_objects[0].offset-3000

    def skip(self):
        self.current_offset = self.current_map.hit_objects[0].offset-2500

    def render_debug(self):
        text_surface = self.font.render(f'Map: {self.current_map.beatmap.metadata["Artist"]} - '
                                        f'{self.current_map.beatmap.metadata["Title"]} '
                                        f'[{self.current_map.beatmap.metadata["Version"]}] '
                                        f'({self.current_map.beatmap.metadata["Creator"]}) '
                                        f'{round(self.current_map.nm_sr, 2)}*, '
                                        f'AR: {self.current_map.beatmap.difficulty["ApproachRate"]}, '
                                        f'CS: {self.current_map.beatmap.difficulty["CircleSize"]}'
                                        if self.current_map is not None else "No map loaded.", False,
                                        (255, 255, 255))
        offset_render = self.font.render(
            f'Offset: {self.current_offset}', False, (255, 255, 255))
        tick_render = self.font.render(
            f'pygame.time.get_ticks(): {pygame.time.get_ticks()}', False, (255, 255, 255))
        self.window.blit(text_surface, (0, 0))
        self.window.blit(offset_render, (0, 21))
        self.window.blit(tick_render, (0, 42))

    def draw_pekora(self):
        rotated_image = pygame.transform.rotate(self.pekora, self.pekora_angle)
        self.window.blit(rotated_image,
                         rotated_image.get_rect(
                             center=self.pekora.get_rect(
                                 topleft=(self.size[0] / 2 - 64, self.size[1] / 2 - 64)).center).topleft)
        self.pekora_angle = 0 if self.pekora_angle >= 360 else self.pekora_angle + 0.555

    def draw_background(self):
        if(self.background == None):
            return
        self.background.set_alpha(
            max(50, min(self.current_map.hit_objects[0].offset-self.current_offset-500, 255)))
        self.window.blit(self.background, (0, 0))

    def draw_objects(self):
        self.current_offset += self.clock.get_time()
        for hit_object in self.object_manager.get_hit_objects_for_offset(self.current_offset):
            self.hitcircle.set_alpha(self.object_manager.get_opacity(
                hit_object, self.current_offset))
            size = self.hitcircle.get_rect()
            self.window.blit(self.hitcircle, (hit_object.x * self.osu_pixel_multiplier + self.placement_offset[0] - size[0]//2,
                                              hit_object.y * self.osu_pixel_multiplier + self.placement_offset[1] - size[1]//2))

    @property
    def map_ended(self):
        return self.current_offset > self.current_map.hit_objects[-1].offset


class Game:
    def __init__(self, size: Sequence[int], fps: int, gamemode: Gamemode, is_borderless: bool = False, is_caching_enabled=True, is_background_enabled=True):
        # Should be performed before initializing pygame
        self.map_collector = MapCollector(
            is_caching_enabled=is_caching_enabled)
        self.map_collector.collect()

        # Game attributes
        self.size = size
        self.is_borderless = is_borderless
        self.gamemode = gamemode
        self.current_map = None
        self.fps = fps
        self.is_background_enabled = is_background_enabled

        # Initialize pygame
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(
            f"osu!simulation {'[b]' if is_borderless else ''}")

        # "Helper" objects
        self.window = pygame.display.set_mode(
            size, pygame.NOFRAME if is_borderless else 0)
        self.clock = pygame.time.Clock()
        self.frame_manager = GameFrameManager(size, self.window, self.clock)

        # State variables
        self.running = False
        self.on_start_screen = True
        self.display_debug = True

        self.actions = {
            pygame.K_r: self.on_random_map,
            pygame.K_d: self.on_toggle_debug,
            pygame.K_SPACE: self.on_skip,
            pygame.K_f: self.on_force_end,
        }

    # Event functions

    def on_quit(self):
        self.running = False

    def on_random_map(self, event):
        if not self.on_start_screen:
            return
        self.current_map = self.map_collector.get_random_map()
        if self.current_map is None:
            return
        self.on_start_screen = False
        self.frame_manager.load_map(self.current_map)

    def on_toggle_debug(self, event):
        self.display_debug = not self.display_debug

    def on_skip(self, event):
        if not self.frame_manager.can_skip:
            return
        self.frame_manager.skip()

    def on_force_end(self, event):
        if self.on_start_screen:
            return
        self.current_map = None
        self.on_start_screen = True

    # Running functions

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.on_quit()
            if event.type == pygame.KEYDOWN:
                if event.key in self.actions:
                    self.actions[event.key](event)

    def draw(self):
        self.window.fill((0, 0, 0))

        if self.on_start_screen:
            self.frame_manager.draw_pekora()

        elif self.current_map is not None:
            if self.is_background_enabled:
                self.frame_manager.draw_background()
            self.frame_manager.draw_objects()
            if self.frame_manager.map_ended:
                self.on_start_screen = True

        if self.display_debug:
            self.frame_manager.render_debug()

    def run(self):
        self.running = True

        while self.running:
            self.handle_events()
            self.draw()

            pygame.display.update()
            self.clock.tick(self.fps)

        pygame.time.wait(10)
        pygame.quit()
