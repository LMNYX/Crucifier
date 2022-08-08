from constants import osu_pixel_window
from enums import SkinOption
from beatmap_reader import HitObjectType
import math
import threading


class ResolutionManager:
    def __init__(self, screen_size):
        w = screen_size[0] * 0.8
        h = screen_size[1] * 0.8
        # Visual playfield size
        # Scale playfield size by the osu_pixel_window
        # Size is limited based on resolution of width and height
        self.screen_size = screen_size
        self.playfield_size = (h / osu_pixel_window[1] * osu_pixel_window[0], h) \
            if w / osu_pixel_window[0] * osu_pixel_window[1] > h \
            else (w, w / osu_pixel_window[0] * osu_pixel_window[1])
        self.playfield_size = tuple(map(round, self.playfield_size))
        self.placement_offset = tuple([
            round((screen_size[i] - self.playfield_size[i]) / 2) for i in (0, 1)
        ])
        self.osu_pixel_multiplier = self.playfield_size[0] / osu_pixel_window[0]
        # Playfield size for all objects
        self.actual_playfield_size = (
            512 * self.osu_pixel_multiplier, 384 * self.osu_pixel_multiplier
        )
        self.actual_placement_offset = tuple([
            round((screen_size[i] - self.actual_playfield_size[i]) / 2) for i in (0, 1)
        ])

        self.object_size = None

    def load_size(self, cs):
        self.object_size = round((54.4 - 4.48 * cs) * 2 * self.osu_pixel_multiplier)

    def get_playfield_rect(self):
        return self.placement_offset + self.playfield_size

    def get_actual_playfield_rect(self):
        return self.actual_placement_offset + self.actual_playfield_size

    def get_hitcircle_position(self, hit_obj):
        x, y = hit_obj.stacked_position
        return (x * self.osu_pixel_multiplier + self.actual_placement_offset[0] - self.object_size // 2,
                y * self.osu_pixel_multiplier + self.actual_placement_offset[1] - self.object_size // 2)

    def get_cursor_position(self, position):
        return (self.actual_placement_offset[0]+position[0],
                self.actual_placement_offset[1]+position[1])


class ObjectManager:
    def __init__(self, beatmap, resolution, resources):
        self.hit_object_combo_colors = {}
        self.hit_object_combos = []
        ar = float(beatmap.difficulty.approach_rate)
        self.preempt = 1200 + 600 * (5 - ar) / 5 if ar < 5 else 1200 - 750 * (ar - 5) / 5
        self.fadein = 800 + 400 * (5 - ar) / 5 if ar < 5 else 800 - 500 * (ar - 5) / 5
        self.hit_objects = list(beatmap.hit_objects)  # new list object
        self.obj_offset = 0
        threading.Thread(target=self._do_hit_object_load, args=(resources, resolution)).start()

    def _do_hit_object_load(self, resources, resolution):
        main_thread = threading.current_thread()
        config = resources.skin.config
        current_combo_color = 0
        current_combo = 1
        for i, hit_object in enumerate(self.hit_objects):
            if not main_thread.is_alive():
                return print("Hit object loading thread killed itself D:")

            if hit_object.new_combo:
                current_combo_color = (current_combo_color + 1) % len(config.combo_colors)
                current_combo = 1
            self.hit_object_combo_colors[hit_object] = current_combo_color
            self.hit_object_combos.append(current_combo)
            if hit_object.type != HitObjectType.SPINNER:
                current_combo += 1

            if hit_object.type == HitObjectType.SLIDER:
                color = config.combo_colors[current_combo_color] \
                    if config.slider_track_override == SkinOption.CURRENT_COMBO_COLOR \
                    else config.slider_track_color
                hit_object.render(resolution.screen_size, resolution.actual_placement_offset,
                                  resolution.osu_pixel_multiplier, color, config.slider_border,
                                  round(5*resolution.osu_pixel_multiplier))
        print("Finished loading all hit objects!")

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
        return 200 if offset >= clear else 200 - round(
            (clear - offset) / self.fadein * 200)

    def get_combo_color(self, hit_object):
        return self.hit_object_combo_colors[hit_object]

    def get_combo_number(self, hit_object):
        return self.hit_object_combos[self.hit_objects.index(hit_object)]

    def get_ac_multiplier(self, hit_object, offset):
        return (hit_object.time - offset) / self.preempt * 2 + 1

    @staticmethod
    def get_sliderball_position(current_offset, hit_object, resolution):
        index = min(math.floor((current_offset - hit_object.time) /
                               (hit_object.end_time - hit_object.time) *
                               len(hit_object.curve.curve_points)),
                    len(hit_object.curve.curve_points)-1)
        return resolution.get_hitcircle_position(hit_object.nested_objects[index])
