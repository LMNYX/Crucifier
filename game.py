import pygame
import pygame.gfxdraw  # Must be imported explicitly to work
import numpy as np
import math
import time
from profilehooks import profile
from random import randint
from typing import Sequence
from os import path
from constants import *
from enums import Gamemode, DebugMode
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
            endtime = self.hit_objects[index].end_time.total_seconds()*1000 if self.hit_objects[index].type_code == 2 \
                else self.hit_objects[index].time.total_seconds()*1000
            if offset > endtime:
                self.obj_offset += 1
                index += 1
                continue
            if offset < self.hit_objects[index].time.total_seconds()*1000-self.preempt:
                break
            index += 1
            yield self.hit_objects[index-1]

    def get_opacity(self, hit_object, offset):
        # Time at which circle becomes 100% opacity
        clear = hit_object.time.total_seconds()*1000 - self.preempt + self.fadein
        return 255 if offset >= clear else 255 - round(
            (clear - offset) / self.fadein * 255)


class AudioManager:
    def __init__(self, default_volume=0.25, is_disabled=False, channel_amount=32):
        pygame.mixer.init()

        self.channel_amount = channel_amount

        # for overlapping sounds, channel 0 is reserved for beatmap music
        pygame.mixer.set_num_channels(channel_amount)

        self.time_after_last_modified_volume = -750
        self.is_disabled = is_disabled
        self.volume = default_volume if not is_disabled else 0

        self.beatmap_audio_playing = False

        pygame.mixer.music.set_volume(self.volume)

    def set_volume(self, new_volume):
        if self.is_disabled or self.volume == max(0, min(1, new_volume)):
            return
        self.volume = max(0, min(1, new_volume))
        self.time_after_last_modified_volume = pygame.time.get_ticks()+750
        pygame.mixer.music.set_volume(new_volume)

    def increase_volume(self, channel=0, event=None):
        self.set_volume(self.volume+0.01)

    def decrease_volume(self, channel=0, event=None):
        self.set_volume(self.volume-0.01)

    def load_audio(self, pathto, is_beatmap_audio=False, channel=0):
        if self.is_disabled:
            return
        if is_beatmap_audio:
            pygame.mixer.music.load(pathto)
        else:
            channel = randint(
                1, self.channel_amount) if channel == 0 else channel
            pygame.mixer.Channel(1).load(pathto)
        return channel if not is_beatmap_audio else 0

    def play_audio(self, channel=0):
        if self.is_disabled:
            return
        if channel == 0:
            pygame.mixer.music.play()
            self.beatmap_audio_playing = True
        else:
            pygame.mixer.Channel(channel).play()

    def stop_audio(self, channel=0):
        if self.is_disabled:
            return
        if channel == 0:
            pygame.mixer.music.stop()
            self.beatmap_audio_playing = False
        else:
            pygame.mixer.Channel(channel).stop()

    def load_and_play_audio(self, pathto, is_beatmap_audio=False):
        if self.is_disabled or (is_beatmap_audio and self.beatmap_audio_playing):
            return
        if is_beatmap_audio:
            self.beatmap_audio_playing = True
        channel = self.load_audio(pathto, is_beatmap_audio=is_beatmap_audio)
        self.play_audio(channel=channel)


class GameFrameManager:
    def __init__(self, size, window, clock, audio_manager, debug_mode=DebugMode.NO):
        self.size = size
        self.window = window
        self.clock = clock
        self.debug_mode = debug_mode
        self.font = pygame.font.SysFont("Times New Roman", 16)
        w = size[0] * 0.8
        h = size[1] * 0.8
        self.playfield_size = (h / osu_pixel_window[1] * osu_pixel_window[0], h) \
            if w / osu_pixel_window[0] * osu_pixel_window[1] > h \
            else (w, w / osu_pixel_window[0] * osu_pixel_window[1])
        self.playfield_size = tuple(map(round, self.playfield_size))
        self.placement_offset = [
            round((size[i] - self.playfield_size[i]) / 2) for i in (0, 1)]
        self.osu_pixel_multiplier = self.playfield_size[0] / 512
        self.object_size = 0
        self.object_manager = ObjectManager()
        self.current_map = None
        self.current_offset = 0

        self.audio_manager = audio_manager

        pekora = pygame.image.load(r'resources\\pekora.png')
        self.pekora = pygame.transform.smoothscale(pekora, (128, 128))
        self.pekora_angle = 0

        self.original_hitcircle = pygame.image.load(
            r'resources\\hitcircle.png')
        self.hitcircle = None
        self.plain_circle = None

        self.background = None
        self.background_fading = False

    def load_map(self, beatmap):
        self.current_map = beatmap
        self.object_manager.load_hit_objects(beatmap)
        self.object_size = round(
            (54.4 - 4.48 * float(self.current_map.beatmap.difficulty["CircleSize"])) * 2 * self.osu_pixel_multiplier)
        self.hitcircle = pygame.transform.smoothscale(
            self.original_hitcircle, (self.object_size, self.object_size))
        self.plain_circle = self.create_plain_circle()
        self.plain_circle.set_colorkey((0, 0, 0))
        self.current_offset = self.current_map.hit_objects[0].time.total_seconds()*1000 - \
            self.object_manager.preempt - 3000
        self.background = pygame.image.load(
            f"{path.dirname(self.current_map.path)}/{self.current_map.background}")
        background_ratio = self.size[1]/self.background.get_size()[1] + 0.1
        self.background = pygame.transform.smoothscale(self.background, (
            self.background.get_size()[0] * background_ratio,
            self.background.get_size()[1] * background_ratio))
        self.background_fading = True

    def create_plain_circle(self):
        size = self.object_size
        circle = np.zeros((size, size, 3), dtype=np.uint8)
        for y in range(size):
            for x in range(size):
                if (x - size / 2)**2 + (y - size / 2)**2 < (size / 2)**2:
                    circle[y, x] = (255, 255, 255)
        return pygame.surfarray.make_surface(circle)

    @property
    def can_skip(self):
        return self.current_offset < self.current_map.hit_objects[0].time.total_seconds()*1000-3000

    def skip(self):
        self.current_offset = self.current_map.hit_objects[0].time.total_seconds(
        )*1000-2500

    def debug_blit(self, *args, n=0):
        self.window.blit(*args)
        return n + 19

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
        debug_y_offset = 0
        offset_render = self.font.render(
            f'Offset: {self.current_offset}', False, (255, 255, 255))
        tick_render = self.font.render(
            f'pygame.time.get_ticks(): {pygame.time.get_ticks()}', False, (255, 255, 255))
        fps_render = self.font.render(
            f'FPS: {round(self.clock.get_fps())}', False, (255, 255, 255))
        debug_y_offset = self.debug_blit(
            text_surface, (0, debug_y_offset), n=debug_y_offset)
        if self.debug_mode is DebugMode.FULL:
            debug_y_offset = self.debug_blit(
                offset_render, (0, debug_y_offset), n=debug_y_offset)
            debug_y_offset = self.debug_blit(
                tick_render, (0, debug_y_offset), n=debug_y_offset)
        debug_y_offset = self.debug_blit(
            fps_render, (0, debug_y_offset), n=debug_y_offset)

    def draw_pekora(self):
        rotated_image = pygame.transform.rotate(self.pekora, self.pekora_angle)
        self.window.blit(rotated_image,
                         rotated_image.get_rect(
                             center=self.pekora.get_rect(
                                 topleft=(self.size[0] / 2 - 64, self.size[1] / 2 - 64)).center).topleft)
        self.pekora_angle = 0 if self.pekora_angle >= 360 else self.pekora_angle + 0.555

    def draw_background(self):
        if self.background is None:
            return
        if self.background_fading and self.fade_background():
            self.background_fading = False
        self.window.blit(
            self.background, (self.size[0]/2-(self.background.get_size()[0]/2), self.size[1]/2-(self.background.get_size()[1]/2)))

    def fade_background(self):
        opacity = round(max(50, (self.current_map.hit_objects[0].time.total_seconds(
        )*1000 - self.current_offset) / 500 * 255))
        self.background.set_alpha(opacity)
        return opacity == 50

    def draw_playfield(self):
        pygame.draw.rect(self.window, (255, 0, 0),
                         (self.placement_offset[0], self.placement_offset[1],
                          self.playfield_size[0], self.playfield_size[1]),
                         width=1)

    def draw_objects(self):
        self.current_offset += self.clock.get_time()
        for hit_object in self.object_manager.get_hit_objects_for_offset(self.current_offset):
            opacity = self.object_manager.get_opacity(
                hit_object, self.current_offset)
            # TODO: Make this more practical as opposed to statically comparing to 2
            if hit_object.type_code == 2:  # slider
                self.draw_slider(hit_object, opacity)
            self.hitcircle.set_alpha(opacity)
            size = self.hitcircle.get_rect()
            self.window.blit(self.hitcircle, (hit_object.position.x * self.osu_pixel_multiplier + self.placement_offset[0] - size.width//2,
                                              hit_object.position.y * self.osu_pixel_multiplier + self.placement_offset[1] - size.height//2))

    def draw_slider(self, slider, opacity):
        points = list(
            map(lambda point:
                (round(point.x * self.osu_pixel_multiplier + self.placement_offset[0]),
                 round(point.y * self.osu_pixel_multiplier + self.placement_offset[1])),
                map(slider.curve, np.linspace(0, 1, round(slider.length*self.osu_pixel_multiplier)))))

        self.plain_circle.set_alpha(opacity)

        for point in points:
            self.window.blit(
                self.plain_circle, (point[0] - self.object_size//2, point[1] - self.object_size//2))

        # Fail
        """
        for i in range(len(points) - 1):
            direction = pygame.math.Vector2(points[i][0]-points[i+1][0], points[i][1]-points[i+1][1])
            if direction.length() > 0:
                direction = direction.normalize()
            perp1 = direction.rotate(90) * (self.object_size // 2)
            perp2 = direction.rotate(-90) * (self.object_size // 2)

            p1 = points[i][0] + perp1.x, points[i][1] + perp1.y
            p2 = points[i+1][0] + perp1.x, points[i+1][1] + perp1.y
            p3 = points[i][1] + perp2.x, points[i][1] + perp2.y
            p4 = points[i+1][1] + perp2.x, points[i+1][1] + perp2.y

            pygame.gfxdraw.aapolygon(self.window, (p1, p2, p3, p4), (255, 255, 255, opacity))
            pygame.gfxdraw.filled_polygon(self.window, (p1, p2, p3, p4), (255, 255, 255, opacity))
        """

    def draw_volume(self):
        pygame.draw.rect(self.window, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, 100, 16), 1)
        pygame.draw.rect(self.window, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, self.audio_manager.volume*100, 16), 0)

    @property
    def map_ended(self):
        return self.current_offset > self.current_map.hit_objects[-1].time.total_seconds()*1000


class Game:
    def __init__(self, size: Sequence[int], fps: int, gamemode: Gamemode, is_borderless: bool = False, is_caching_enabled=True, is_background_enabled=True, should_reset_cache=False, is_audio_enabled=True, default_volume=25, debug_mode=0):
        # Should be performed before initializing pygame
        self.map_collector = MapCollector(
            is_caching_enabled=is_caching_enabled, should_reset_cache=should_reset_cache)
        self.map_collector.collect()

        # Game attributes
        self.size = size
        self.is_borderless = is_borderless
        self.gamemode = gamemode
        self.current_map = None
        self.fps = fps
        self.is_background_enabled = is_background_enabled
        self.debug_mode = DebugMode(debug_mode)

        # Initialize pygame
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(
            f"osu!simulation {'[b]' if is_borderless else ''}")

        # "Helper" objects
        self.window = pygame.display.set_mode(
            size, pygame.NOFRAME if is_borderless else 0)
        self.clock = pygame.time.Clock()
        self.audio_manager = AudioManager(
            default_volume=default_volume/100, is_disabled=not is_audio_enabled)
        self.frame_manager = GameFrameManager(
            size, self.window, self.clock, self.audio_manager, debug_mode=self.debug_mode)

        # State variables
        self.running = False
        self.on_start_screen = True
        self.display_debug = True

        self.events = {
            "keydown": {
                pygame.K_r: self.on_random_map,
                pygame.K_d: self.on_toggle_debug,
                pygame.K_SPACE: self.on_skip,
                pygame.K_f: self.on_force_end,
            },
            "mousedown": {
                4: self.audio_manager.increase_volume,
                5: self.audio_manager.decrease_volume,
            }
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
        if self.frame_manager.can_skip:
            self.frame_manager.skip()

    def on_force_end(self, event):
        if self.on_start_screen:
            return
        self.current_map = None
        self.audio_manager.stop_audio(0)
        self.on_start_screen = True

    # Running functions

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.on_quit()
            if event.type == pygame.KEYDOWN:
                if event.key in self.events['keydown']:
                    self.events['keydown'][event.key](event=event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in self.events['mousedown']:
                    self.events['mousedown'][event.button](event=event)

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

        if self.display_debug and self.debug_mode is not DebugMode.NO:
            self.frame_manager.render_debug()
            if self.current_map is not None:
                self.frame_manager.draw_playfield()

        if self.audio_manager.time_after_last_modified_volume > pygame.time.get_ticks():
            self.frame_manager.draw_volume()

    def handle_audio(self):
        if not self.on_start_screen and not self.audio_manager.beatmap_audio_playing and self.frame_manager.current_offset >= 0:
            self.audio_manager.load_and_play_audio(
                f"{path.dirname(self.current_map.path)}/{self.current_map.beatmap.general['AudioFilename']}",
                is_beatmap_audio=True)

    @profile
    def run(self):
        self.running = True

        while self.running:
            self.handle_events()
            self.handle_audio()
            self.draw()

            pygame.display.update()
            self.clock.tick(self.fps)

        pygame.time.wait(10)
        pygame.quit()
