from game import BaseState
from util import ObjectManager
from os import path
from enums import DebugMode
from audio import AudioManager
from beatmap_reader import HitObjectType
import pygame


class GameStateManager:
    def __init__(self, beatmap=None, clock=None, object_manager=None):
        if beatmap is not None:
            self.beatmap = beatmap
        if clock is not None:
            self.clock = clock
        if object_manager is not None:
            self.object_manager = object_manager
        self.current_offset = min(0, self.beatmap.hit_objects[0].time - self.object_manager.preempt - 3000)
        self.current_combo_color = 0
        self.counted_objects = []
        self.cursor_pos = (0, 0)
        self.background_fading = True

    def set_default(self):
        self.__init__()

    @property
    def can_skip(self):
        return self.current_offset < self.beatmap.hit_objects[0].time - 3000

    @property
    def map_ended(self):
        last_obj = self.beatmap.hit_objects[-1]
        return self.current_offset > (last_obj.time if not hasattr(last_obj, "end_time") else last_obj.end_time)

    def skip(self):
        self.current_offset = self.beatmap.hit_objects[0].time - 2500

    def get_background_fade(self):
        opacity = round(max(50, (self.beatmap.hit_objects[0].time - self.current_offset) / 500 * 255))
        if opacity == 50:
            self.background_fading = False
        return opacity

    def advance(self):
        self.current_offset += self.clock.get_time()


class Gameplay(BaseState):
    def __init__(self, game, beatmap, debug_mode=DebugMode.NONE):
        self.game = game
        self.screen = game.screen
        self.size = self.screen.get_size()
        self.beatmap = beatmap
        self.debug_mode = debug_mode
        self.key_events = {
            pygame.K_ESCAPE: self.to_start_screen,
        }

        self.audio_started = False

        print("Loading beatmap...")
        beatmap.load()

        self.resolution = game.resolution
        self.resources = game.resources
        self.object_manager = ObjectManager(beatmap, self.resolution, self.resources)
        self.audio_manager = AudioManager(game.config.get("audio.volume"))
        self.state = GameStateManager(self.beatmap, game.clock, self.object_manager)

        # More map loading
        self.resolution.load_size(beatmap.difficulty.circle_size)
        self.resources.load_map(beatmap)
        self.background = self.get_background_path(beatmap)
        if self.background is not None:
            self.set_background(self.background)
        print("Beatmap loaded.")

    def to_start_screen(self):
        self.stop_and_cleanup()
        self.game.switch_state("start")

    def stop_and_cleanup(self):
        self.audio_manager.stop_audio()

    @staticmethod
    def get_background_path(beatmap):
        for event in beatmap.events:
            event = event.split(",")
            if len(event) == 5 and event[0] == "0" and event[1] == "0":
                return path.join(path.split(beatmap.path)[0], event[2] if '"' not in event[2] else event[2][1:-1])

    def set_background(self, bg_path):
        self.background = pygame.image.load(bg_path)
        background_ratio = self.size[1] / self.background.get_size()[1] + 0.1
        size = (self.background.get_size()[0] * background_ratio,
                self.background.get_size()[1] * background_ratio)
        try:
            self.background = pygame.transform.smoothscale(self.background, size).convert()
        except ValueError:
            self.background = pygame.transform.scale(self.background, size).convert()

    def debug_blit(self, *args, n=0, pixel_skip=19):
        self.screen.blit(*args)
        return n + pixel_skip

    def draw_debug(self):
        # TODO: make a helper class for creating and drawing debug so this looks cleaner
        font = self.resources.font
        text_surface = font.render(f'Map: {self.beatmap.metadata.artist} - '
                                        f'{self.beatmap.metadata.title} '
                                        f'[{self.beatmap.metadata.version}] '
                                        f'({self.beatmap.metadata.creator}) '
                                        # f'{round(self.beatmap.nm_sr, 2)}*, '  # TODO: star rating
                                        f'AR: {self.beatmap.difficulty.approach_rate}, '
                                        f'CS: {self.beatmap.difficulty.circle_size}'
                                        if self.beatmap is not None else "No map loaded.", True,
                                        (255, 255, 255))
        font_size = self.resources.font_size
        debug_y_offset = 0
        debug_y_offset = self.debug_blit(
            text_surface, (0, debug_y_offset), n=debug_y_offset, pixel_skip=font_size)
        if self.debug_mode is DebugMode.FULL:
            # Render
            offset_render = font.render(f'Offset: {self.state.current_offset}', True, (255, 255, 255))
            tick_render = font.render(f'pygame.time.get_ticks(): {pygame.time.get_ticks()}',
                                      True, (255, 255, 255))

            # Blit
            debug_y_offset = self.debug_blit(offset_render, (0, debug_y_offset),
                                             n=debug_y_offset, pixel_skip=font_size)
            self.debug_blit( tick_render, (0, debug_y_offset), n=debug_y_offset, pixel_skip=font_size)

    def draw_background(self):
        if self.background is None:
            return
        if self.state.background_fading:
            self.background.set_alpha(self.state.get_background_fade())
        self.screen.blit(self.background, (self.size[0]/2-(self.background.get_size()[0]/2),
                                           self.size[1]/2-(self.background.get_size()[1]/2)))

    def draw_playfield(self):
        pygame.draw.rect(self.screen, (255, 0, 0),
                         self.resolution.get_playfield_rect(),
                         width=1)
        pygame.draw.rect(self.screen, (255, 0, 0),
                         self.resolution.get_actual_playfield_rect(),
                         width=1)

    def draw_objects(self):
        for hit_object in self.object_manager.get_hit_objects_for_offset(self.state.current_offset):
            # Spinners not yet implemented
            if hit_object.type == HitObjectType.SPINNER:
                self.draw_spinner(hit_object)
                continue

            # Get opacity for hit object
            opacity = self.object_manager.get_opacity(hit_object, self.state.current_offset)
            combo_color = self.object_manager.get_combo_color(hit_object)

            # Draw slider body
            if hit_object.type == HitObjectType.SLIDER:
                hit_object.surf.set_alpha(opacity)
                self.screen.blit(hit_object.surf, (0, 0))
                # Draw slider ball and follow circle
                if self.state.current_offset >= hit_object.time:
                    for element in (self.resources.skin.sliderball, self.resources.skin.sliderfollowcircle):
                        self.screen.blit(self.resources.skin.config.get_animation_frame(
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
            self.screen.blit(hitcircle, position)
            if self.resources.skin.config.hit_circle_overlay_above_number:
                self.screen.blit(hitcircleoverlay, position)
                self.draw_number(hit_object, opacity, position)
            else:
                self.draw_number(hit_object, opacity, position)
                self.screen.blit(hitcircleoverlay, position)
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
        self.screen.blit(approachcircle, tuple(map(lambda x: x - offset, position)))

    def draw_number(self, hit_object, opacity, position):
        number = self.object_manager.get_combo_number(hit_object)
        num_pos_offset = self.resolution.object_size // (len(str(number))+1)
        num_pos_start = position[0] + num_pos_offset
        for i, num in enumerate(str(number)):
            img = self.resources.skin.defaults[int(num)]
            img.set_alpha(opacity)
            pos = (num_pos_start + i*num_pos_offset - img.get_size()[0] // 2,
                   position[1] + self.resolution.object_size // 2 - img.get_size()[1] // 2)
            self.screen.blit(img, pos)

    def draw_spinner(self, hit_object):
        pass

    def draw_cursor(self):
        pygame.draw.circle(self.screen, (255, 0, 0), self.resolution.get_cursor_position(self.state.cursor_pos), 4)

    def draw_volume(self):
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, 100, 16), 1)
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (self.size[0]-164, self.size[1]-64-25, self.audio_manager.volume*100, 16), 0)

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.draw_background()
        self.draw_objects()
        if self.debug_mode != DebugMode.NONE:
            self.draw_debug()

    def handle_state(self):
        if not self.audio_started and self.state.current_offset >= 0:
            self.audio_manager.load_and_play_audio(self.beatmap.general.audio_file,
                                                   offset=self.state.current_offset,
                                                   is_beatmap_audio=True)
            self.audio_started = True
        self.state.advance()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.key_events:
                self.key_events[event.key]()
