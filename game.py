import pygame
import math
import random
from beatmap_reader import SongsFolder, HitObjectType, GameMode
from tkinter import filedialog
import tkinter as tk
from typing import Sequence
from os import path
from configuration import ConfigurationManager
from enums import DebugMode, SkinOption
from resource import ResourceManager
from resolution import ResolutionManager

root = tk.Tk()
root.withdraw()

# TODO: consider moving logic for calculating resolution and such to its own class


class ObjectManager:
    def __init__(self):
        self.hit_objects = None
        self.hit_object_combo_colors = {}
        self.obj_offset = 0
        self.preempt = 0
        self.fadein = 0

    def load_hit_objects(self, beatmap, resolution, resources):
        config = resources.skin.config

        ar = float(beatmap.difficulty.approach_rate)
        self.preempt = 1200 + 600 * \
            (5 - ar) / 5 if ar < 5 else 1200 - 750 * (ar - 5) / 5
        self.fadein = 800 + 400 * \
            (5 - ar) / 5 if ar < 5 else 800 - 500 * (ar - 5) / 5
        self.hit_objects = list(beatmap.hit_objects)  # new list object
        self.obj_offset = 0

        current_combo_color = 0
        for i, hit_object in enumerate(self.hit_objects):
            if hit_object.new_combo:
                current_combo_color = (current_combo_color + 1) % len(config.combo_colors)
            self.hit_object_combo_colors[hit_object] = current_combo_color
            progress = round((i / len(self.hit_objects))*20)
            print(
                f"\rPre-rendering sliders: [{progress * '#'}{(20 - progress) * '-'}]", end='\r')
            if hit_object.type == HitObjectType.SLIDER:
                color = config.combo_colors[current_combo_color] \
                    if config.slider_track_override == SkinOption.CURRENT_COMBO_COLOR \
                    else config.slider_track_color
                hit_object.render(resolution.screen_size, resolution.actual_placement_offset,
                                  resolution.osu_pixel_multiplier, color, config.slider_border,
                                  round(5*resolution.osu_pixel_multiplier))
        print()

    def get_hit_objects_for_offset(self, offset):
        index = self.obj_offset
        objects = []
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
            objects.append(self.hit_objects[index-1])
        objects.reverse()
        return objects

    def get_opacity(self, hit_object, offset):
        # Time at which circle becomes 100% opacity
        clear = hit_object.time - self.preempt + self.fadein
        return 255 if offset >= clear else 255 - round(
            (clear - offset) / self.fadein * 255)

    def get_combo_color(self, hit_object):
        return self.hit_object_combo_colors[hit_object]

    def get_ac_multiplier(self, hit_object, offset):
        return (hit_object.time - offset) / self.preempt * 2 + 1

    def get_sliderball_position(self, current_offset, hit_object, resolution):
        index = min(math.floor((current_offset - hit_object.time) /
                               (hit_object.end_time - hit_object.time) *
                               len(hit_object.curve.curve_points)),
                len(hit_object.curve.curve_points)-1)
        return resolution.get_hitcircle_position(hit_object.curve.curve_points[index])


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
        self.time_after_last_modified_volume = pygame.time.get_ticks()
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


class GameStateManager:
    def __init__(self, beatmap=None, clock=None, object_manager=None):
        if clock is not None:
            self.clock = clock
        if object_manager is not None:
            self.object_manager = object_manager
        self.current_map = beatmap
        self.current_offset = 0 if beatmap is None else \
            min(0, beatmap.hit_objects[0].time - self.object_manager.preempt - 3000)
        self.current_combo_color = 0
        self.counted_objects = []
        self.cursor_pos = (0, 0)
        self.pekora_angle = 0
        self.background_fading = False

    def set_default(self, beatmap):
        self.__init__(beatmap)

    @property
    def can_skip(self):
        return self.current_offset < self.current_map.hit_objects[0].time - 3000

    @property
    def map_ended(self):
        last_obj = self.current_map.hit_objects[-1]
        return self.current_offset > (last_obj.time if not hasattr(last_obj, "end_time") else last_obj.end_time)

    def skip(self):
        self.current_offset = self.current_map.hit_objects[0].time - 2500

    def rotate_pekora(self):
        self.pekora_angle = 0 if self.pekora_angle >= 360 else self.pekora_angle + 0.555

    def begin_background_fade(self):
        self.background_fading = True

    def get_background_fade(self):
        opacity = round(max(50, (self.current_map.hit_objects[0].time - self.current_offset) / 500 * 255))
        if opacity == 50:
            self.background_fading = False
        return opacity

    def advance(self):
        self.current_offset += self.clock.get_time()


class GameFrameManager:
    def __init__(self, size, parent, debug_mode=DebugMode.NO):
        self.size = size
        self.window = parent.window
        self.clock = parent.clock
        self.debug_mode = debug_mode
        self.status_message = None

        self.resolution: ResolutionManager = parent.resolution
        self.resources: ResourceManager = parent.resources
        self.object_manager: ObjectManager = parent.object_manager
        self.state: GameStateManager = parent.state
        self.state.resources = self.resources
        self.audio_manager: AudioManager = parent.audio_manager

        self.plain_circles = []
        self.background = None

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

        self.object_manager.load_hit_objects(beatmap, self.resolution, self.resources)
        self.resolution.load_size(beatmap.difficulty.circle_size)
        self.resources.load_map(beatmap)
        self.state.set_default(beatmap)

        bg_path = self.get_background_path(beatmap)
        if bg_path:
            self.background = pygame.image.load(bg_path)
            background_ratio = self.size[1]/self.background.get_size()[1] + 0.1
            self.background = pygame.transform.smoothscale(self.background, (
                self.background.get_size()[0] * background_ratio,
                self.background.get_size()[1] * background_ratio)).convert()
            self.state.begin_background_fade()

    def debug_blit(self, *args, n=0, pixel_skip=19):
        self.window.blit(*args)
        return n + pixel_skip

    def render_debug(self):
        font = self.resources.font
        text_surface = font.render(f'Map: {self.state.current_map.metadata.artist} - '
                                        f'{self.state.current_map.metadata.title} '
                                        f'[{self.state.current_map.metadata.version}] '
                                        f'({self.state.current_map.metadata.creator}) '
                                        # f'{round(self.current_map.nm_sr, 2)}*, '  # TODO: star rating
                                        f'AR: {self.state.current_map.difficulty.approach_rate}, '
                                        f'CS: {self.state.current_map.difficulty.circle_size}'
                                        if self.state.current_map is not None else "No map loaded.", True,
                                        (255, 255, 255))
        font_size = self.resources.font_size
        debug_y_offset = 0
        debug_y_offset = self.debug_blit(
            text_surface, (0, debug_y_offset), n=debug_y_offset, pixel_skip=font_size)
        if self.debug_mode is DebugMode.FULL:
            # Render
            offset_render = font.render(
                f'Offset: {self.state.current_offset}', True, (255, 255, 255))
            tick_render = font.render(
                f'pygame.time.get_ticks(): {pygame.time.get_ticks()}', True, (255, 255, 255))

            # Blit
            debug_y_offset = self.debug_blit(
                offset_render, (0, debug_y_offset), n=debug_y_offset, pixel_skip=font_size)
            debug_y_offset = self.debug_blit(
                tick_render, (0, debug_y_offset), n=debug_y_offset, pixel_skip=font_size)

    def draw_fps(self):
        fps_render = self.resources.font.render(
            f'FPS: {round(self.clock.get_fps())}', True, (255, 255, 255))
        self.window.blit(fps_render, (self.size[0]-fps_render.get_width()-4,
                                      self.size[1]-fps_render.get_height()-4))

    def draw_pekora(self):
        rotated_image = pygame.transform.rotate(self.resources.pekora, self.state.pekora_angle)
        if self.status_message:
            pekora_status = self.resources.pekora_font.render(
                self.status_message, True, (255, 255, 255))
            self.window.blit(pekora_status,
                             (self.size[0]/2 - pekora_status.get_size()[0]/2,
                              self.size[1]/2 - pekora_status.get_size()[1]/2 + self.size[1] * 0.2)
                             )
        self.window.blit(rotated_image,
                         rotated_image.get_rect(
                             center=self.resources.pekora.get_rect(
                                 topleft=(self.size[0] / 2 - 64, self.size[1] / 2 - 64)).center).topleft)
        self.state.rotate_pekora()

    def draw_background(self):
        if self.background is None:
            return
        if self.state.background_fading:
            self.background.set_alpha(self.state.get_background_fade())
        self.window.blit(self.background, (self.size[0]/2-(self.background.get_size()[0]/2),
                                           self.size[1]/2-(self.background.get_size()[1]/2)))

    def draw_playfield(self):
        pygame.draw.rect(self.window, (255, 0, 0),
                         self.resolution.get_playfield_rect(),
                         width=1)
        pygame.draw.rect(self.window, (255, 0, 0),
                         self.resolution.get_actual_playfield_rect(),
                         width=1)

    def draw_objects(self):
        for hit_object in self.object_manager.get_hit_objects_for_offset(self.state.current_offset):
            # Spinners not yet implemented
            if hit_object.type == HitObjectType.SPINNER:
                return self.draw_spinner(hit_object)

            # Get opacity for hit object
            opacity = self.object_manager.get_opacity(hit_object, self.state.current_offset)
            combo_color = self.object_manager.get_combo_color(hit_object)

            # Draw slider body
            if hit_object.type == HitObjectType.SLIDER:
                hit_object.surf.set_alpha(opacity)
                self.window.blit(hit_object.surf, (0, 0))
                # Draw slider ball and follow circle
                if self.state.current_offset >= hit_object.time:
                    for element in (self.resources.skin.sliderball, self.resources.skin.sliderfollowcircle):
                        self.window.blit(self.resources.skin.config.get_animation_frame(
                            hit_object.time, self.state.current_offset, element,
                            combo_color if isinstance(element[0], list) else None),
                            self.object_manager.get_sliderball_position(self.state.current_offset, hit_object, self.resolution)
                        )
                hitcircle, hitcircleoverlay = self.resources.skin.get_circle_elements(combo_color, True)
            else:
                hitcircle, hitcircleoverlay = self.resources.skin.get_circle_elements(combo_color)

            hitcircle.set_alpha(opacity)
            hitcircleoverlay.set_alpha(opacity)

            # Draw the rest of the hit object
            position = self.resolution.get_hitcircle_position(hit_object)
            self.window.blit(hitcircle, position)
            self.window.blit(hitcircleoverlay, position)
            if self.state.current_offset <= hit_object.time:
                self.draw_approach_circle(hit_object, opacity, position, combo_color)

    def draw_approach_circle(self, hit_object, opacity, position, combo_color):
        # Get the size of the approach circle
        approachcircle_size = round(self.object_manager.get_ac_multiplier(
            hit_object, self.state.current_offset) * self.resolution.object_size)
        # Prepare the approach circle to the correct size
        self.resources.skin.make_approach_circle(approachcircle_size, combo_color)

        approachcircle = self.resources.skin.approachcircle

        # Set opacity and draw
        approachcircle.set_alpha(opacity)
        offset = (approachcircle_size - self.resolution.object_size) // 2
        self.window.blit(approachcircle, tuple(map(lambda x: x - offset, position)))

    def draw_spinner(self, hit_object):
        pass

    def draw_cursor(self):
        pygame.draw.circle(self.window, (255, 0, 0), self.resolution.get_cursor_position(self.state.cursor_pos), 4)

    def draw_volume(self):
        pygame.draw.rect(self.window, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, 100, 16), 1)
        pygame.draw.rect(self.window, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, self.audio_manager.volume*100, 16), 0)


class Game:
    def __init__(self, size: Sequence[int], fps: int, gamemode: GameMode, is_borderless: bool = False,
                 is_caching_enabled=True, is_background_enabled=True, should_reset_cache=False, is_audio_enabled=True,
                 default_volume=25, debug_mode=0):
        # Should be performed before initializing pygame
        self.config = ConfigurationManager.load()
        self.songs_folder = SongsFolder.from_path(self.config.get('songs_path')
                                                  if self.config.get('songs_path') is not None
                                                  else self.ask_songs_folder())

        # Game attributes
        self.is_borderless = is_borderless
        self.gamemode = gamemode
        self.current_map = None
        self.is_background_enabled = is_background_enabled
        # TO-DO: It still asks in terminal, should remove that.

        # Load settings
        self.fps = self.config.get("rendering").get("fps_cap") if fps == -1 else fps
        default_volume = self.config.get("audio").get("volume") if default_volume == -1 else default_volume
        if self.fps != self.config.get("rendering").get("fps_cap"):
            self.config.get("rendering").set("fps_cap", self.fps)
        if default_volume != self.config.get("audio").get("volume"):
            self.config.get("audio").set("volume", default_volume)

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

        self.object_manager = ObjectManager()
        self.resolution = ResolutionManager(size)
        self.resources = ResourceManager(self.resolution)
        self.state = GameStateManager(clock=self.clock, object_manager=self.object_manager)
        self.audio_manager = AudioManager(default_volume=default_volume, is_disabled=not is_audio_enabled)
        self.frame_manager = GameFrameManager(size, self, debug_mode=self.debug_mode)

        self.frame_manager.set_status_message(
            "Press R to select a random map.")

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

    def ask_songs_folder(self):
        folder = filedialog.askdirectory()
        self.config.set("songs_path", folder).save()
        return folder

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
        except IndexError as e:
            return self.frame_manager.set_status_message("No maps found. Load maps first.")
        except Exception as e:
            return self.frame_manager.set_status_message(f"{e}")

        self.on_start_screen = False
        self.frame_manager.load_map(self.current_map)
        self.clock.get_time()  # Get time so the offset doesn't add a bajillion milliseconds

    def on_toggle_debug(self, event):
        self.display_debug = not self.display_debug

    def on_skip(self, event):
        if self.state.can_skip:
            self.state.skip()

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

            self.frame_manager.draw_cursor()
            self.frame_manager.draw_objects()
            if self.state.map_ended:
                self.on_start_screen = True

        if self.audio_manager.time_after_last_modified_volume+750 > pygame.time.get_ticks():
            self.frame_manager.draw_volume()

        if self.display_debug and self.debug_mode is not DebugMode.NO:
            self.frame_manager.render_debug()
            if self.current_map is not None:
                self.frame_manager.draw_playfield()

        self.frame_manager.draw_fps()

    def handle_audio(self):
        if not self.on_start_screen and not self.audio_manager.beatmap_audio_playing and \
                self.state.current_offset >= 0:
            self.audio_manager.load_and_play_audio(
                self.current_map.general.audio_file, is_beatmap_audio=True)

    def handle_state(self):
        self.state.advance()

    def run(self):
        self.running = True

        while self.running:
            self.handle_events()
            self.handle_audio()
            self.draw()
            self.handle_state()

            pygame.display.update()
            self.clock.tick(self.fps)

        pygame.time.wait(10)
        pygame.quit()
