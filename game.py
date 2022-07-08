import pygame
import numpy as np
import random
from beatmap_reader import SongsFolder, HitObjectType, GameMode
from typing import Sequence
from os import path, getenv
from constants import *
from enums import DebugMode


# TODO: consider moving logic for calculating resolution and such to its own class


class ObjectManager:
    def __init__(self):
        self.hit_objects = None
        self.obj_offset = 0
        self.preempt = 0
        self.fadein = 0

    def load_hit_objects(self, beatmap, screen_size, placement_offset, osu_pixel_multiplier):
        ar = float(beatmap.difficulty.approach_rate)
        self.preempt = 1200 + 600 * \
            (5 - ar) / 5 if ar < 5 else 1200 - 750 * (ar - 5) / 5
        self.fadein = 800 + 400 * \
            (5 - ar) / 5 if ar < 5 else 800 - 500 * (ar - 5) / 5
        self.hit_objects = list(beatmap.hit_objects)  # new list object
        self.obj_offset = 0

        for i, hit_object in enumerate(self.hit_objects):
            progress = round((i / len(self.hit_objects))*20)
            print(f"\rPre-rendering sliders: [{progress * '#'}{(20 - progress) * '-'}]", end='\r')
            if hit_object.type == HitObjectType.SLIDER:
                hit_object.render(screen_size, placement_offset, osu_pixel_multiplier)
        print()

    def get_hit_objects_for_offset(self, offset):
        index = self.obj_offset
        while True:
            if index == len(self.hit_objects):
                break
            end_time = self.hit_objects[index].end_time if hasattr(self.hit_objects[index], "end_time") \
                else self.hit_objects[index].time
            if offset > end_time:
                self.obj_offset += 1
                index += 1
                continue
            if offset < self.hit_objects[index].time-self.preempt:
                break
            index += 1
            yield self.hit_objects[index-1]

    def get_opacity(self, hit_object, offset):
        # Time at which circle becomes 100% opacity
        clear = hit_object.time - self.preempt + self.fadein
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
            channel = random.randint(
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
        self.status_message = None
        self.font = pygame.font.Font("resources/Torus.otf", 16)
        self.pekora_font = pygame.font.Font("resources/Torus.otf", 24)
        w = size[0] * 0.8
        h = size[1] * 0.8
        # Visual playfield size
        # Scale playfield size by the osu_pixel_window
        # Size is limited based on resolution of width and height
        self.playfield_size = (h / osu_pixel_window[1] * osu_pixel_window[0], h) \
            if w / osu_pixel_window[0] * osu_pixel_window[1] > h \
            else (w, w / osu_pixel_window[0] * osu_pixel_window[1])
        self.playfield_size = tuple(map(round, self.playfield_size))
        self.placement_offset = [
            round((size[i] - self.playfield_size[i]) / 2) for i in (0, 1)
        ]
        self.osu_pixel_multiplier = self.playfield_size[0] / osu_pixel_window[0]
        # Playfield size for all objects
        self.actual_playfield_size = (
            512 * self.osu_pixel_multiplier, 384 * self.osu_pixel_multiplier
        )
        self.actual_placement_offset = [
            round((size[i] - self.actual_playfield_size[i]) / 2) for i in (0, 1)
        ]
        self.object_size = 0
        self.object_manager = ObjectManager()
        self.current_map = None
        self.current_offset = 0

        self.audio_manager = audio_manager

        pekora = pygame.image.load(r'resources\\pekora.png')
        self.pekora = pygame.transform.smoothscale(pekora, (128, 128))
        self.pekora_angle = 0

        self.original_hitcircle = pygame.image.load(r'resources\\hitcircle.png')
        self.hitcircle = None
        self.plain_circle = None

        self.background = None
        self.background_fading = False

    def set_status_message(self, message):
        self.status_message = message

    @staticmethod
    def get_background_path(beatmap):
        for event in beatmap.events:
            event = event.split(",")
            if len(event) == 5 and event[0] == "0" and event[1] == "0":
                return path.join(path.split(beatmap.path)[0], event[2] if '"' not in event[2] else event[2][1:-1])

    def load_map(self, beatmap):
        print("Loading beatmap...")
        beatmap.load()
        self.current_map = beatmap

        self.object_manager.load_hit_objects(beatmap, self.size,
                                             self.actual_placement_offset, self.osu_pixel_multiplier)

        self.object_size = round(
            (54.4 - 4.48 * float(beatmap.difficulty.circle_size)) * 2 * self.osu_pixel_multiplier)
        self.hitcircle = pygame.transform.smoothscale(
            self.original_hitcircle, (self.object_size, self.object_size))
        self.plain_circle = self.create_plain_circle()

        self.current_offset = beatmap.hit_objects[0].time - \
            self.object_manager.preempt - 3000

        bg_path = self.get_background_path(beatmap)
        if bg_path:
            self.background = pygame.image.load(bg_path)
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
        surf = pygame.surfarray.make_surface(circle)
        surf.set_colorkey((0, 0, 0))
        return surf

    @property
    def can_skip(self):
        return self.current_offset < self.current_map.hit_objects[0].time-3000

    def skip(self):
        self.current_offset = self.current_map.hit_objects[0].time-2500

    def debug_blit(self, *args, n=0):
        self.window.blit(*args)
        return n + 19

    def render_debug(self):
        text_surface = self.font.render(f'Map: {self.current_map.metadata.artist} - '
                                        f'{self.current_map.metadata.title} '
                                        f'[{self.current_map.metadata.version}] '
                                        f'({self.current_map.metadata.creator}) '
                                        # f'{round(self.current_map.nm_sr, 2)}*, '  # TODO: star rating
                                        f'AR: {self.current_map.difficulty.approach_rate}, '
                                        f'CS: {self.current_map.difficulty.circle_size}'
                                        if self.current_map is not None else "No map loaded.", True,
                                        (255, 255, 255))
        debug_y_offset = 0
        fps_render = self.font.render(
            f'FPS: {round(self.clock.get_fps())}', True, (255, 255, 255))
        debug_y_offset = self.debug_blit(
            text_surface, (0, debug_y_offset), n=debug_y_offset)
        if self.debug_mode is DebugMode.FULL:
            # Render
            offset_render = self.font.render(
                f'Offset: {self.current_offset}', True, (255, 255, 255))
            tick_render = self.font.render(
                f'pygame.time.get_ticks(): {pygame.time.get_ticks()}', True, (255, 255, 255))

            # Blit
            debug_y_offset = self.debug_blit(
                offset_render, (0, debug_y_offset), n=debug_y_offset)
            debug_y_offset = self.debug_blit(
                tick_render, (0, debug_y_offset), n=debug_y_offset)
        debug_y_offset = self.debug_blit(
            fps_render, (0, debug_y_offset), n=debug_y_offset)

    def draw_pekora(self):
        rotated_image = pygame.transform.rotate(self.pekora, self.pekora_angle)
        if self.status_message:
            pekora_status = self.pekora_font.render(
                self.status_message, True, (255, 255, 255))
            self.window.blit(pekora_status,
                             (self.size[0]/2 - pekora_status.get_size()[0]/2,
                              self.size[1]/2 - pekora_status.get_size()[1]/2 + self.size[1] * 0.2)
                             )
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
        opacity = round(max(50, (self.current_map.hit_objects[0].time -
                                 self.current_offset) / 500 * 255))
        self.background.set_alpha(opacity)
        return opacity == 50

    def draw_playfield(self):
        pygame.draw.rect(self.window, (255, 0, 0),
                         (self.placement_offset[0], self.placement_offset[1],
                          self.playfield_size[0], self.playfield_size[1]),
                         width=1)
        pygame.draw.rect(self.window, (255, 0, 0),
                         (self.actual_placement_offset[0], self.actual_placement_offset[1],
                          self.actual_playfield_size[0], self.actual_playfield_size[1]),
                         width=1)

    def draw_objects(self):
        self.current_offset += self.clock.get_time()
        for hit_object in self.object_manager.get_hit_objects_for_offset(self.current_offset):
            opacity = self.object_manager.get_opacity(
                hit_object, self.current_offset)
            # TODO: Make this more practical as opposed to statically comparing to 2
            if hit_object.type == HitObjectType.SLIDER:
                hit_object.surf.set_alpha(opacity)
                self.window.blit(hit_object.surf, (0, 0))
            self.hitcircle.set_alpha(opacity)
            self.plain_circle.set_alpha(opacity)

            size = self.hitcircle.get_rect()
            position = (hit_object.x * self.osu_pixel_multiplier + self.actual_placement_offset[0] - size.width//2,
                        hit_object.y * self.osu_pixel_multiplier + self.actual_placement_offset[1] - size.height//2)
            self.window.blit(self.plain_circle, position)
            self.window.blit(self.hitcircle, position)

    def draw_cursor(self, position):
        pygame.draw.circle(self.window, (255, 0, 0),
                           (position[0] + self.placement_offset[0], position[1] + self.placement_offset[1]), 4)

    def draw_volume(self):
        pygame.draw.rect(self.window, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, 100, 16), 1)

    @property
    def map_ended(self):
        last_obj = self.current_map.hit_objects[-1]
        return self.current_offset > (last_obj.time if not hasattr(last_obj, "end_time") else last_obj.end_time)


class Game:
    def __init__(self, size: Sequence[int], fps: int, gamemode: GameMode, is_borderless: bool = False, is_caching_enabled=True, is_background_enabled=True, should_reset_cache=False, is_audio_enabled=True, default_volume=25, debug_mode=0):
        # Should be performed before initializing pygame
        self.songs_folder = SongsFolder.from_path(getenv("SONGS_PATH"))

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

        self.frame_manager.set_status_message(
            "Press R to select a random map.")

        self.cursor_position = (
            self.frame_manager.playfield_size[0]/2, self.frame_manager.playfield_size[1]/2)

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

    def get_random_beatmapset(self):
        return random.choice(self.songs_folder.beatmapsets)

    def get_random_beatmap(self):
        return random.choice(self.get_random_beatmapset().beatmaps)

    def on_random_map(self, event):
        if not self.on_start_screen:
            return
        try:
            self.current_map = self.get_random_beatmap()
        except Exception as e:
            try:
                raise e
            except IndexError:
                self.frame_manager.set_status_message(
                    "No maps found. Load maps first.")
                return

            self.frame_manager.set_status_message(
                f"{e}")
            return
        if self.current_map is None:
            self.frame_manager.set_status_message(
                "Failed to load a map. Try again.")
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

            self.frame_manager.draw_cursor(self.cursor_position)
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
            self.audio_manager.load_and_play_audio(self.current_map.general.audio_file, is_beatmap_audio=True)

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
