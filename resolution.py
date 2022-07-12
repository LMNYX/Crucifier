from constants import osu_pixel_window


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
        self.osu_pixel_multiplier = self.playfield_size[0] / \
                                    osu_pixel_window[0]
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

    def get_hitcircle_position(self, pos):
        if hasattr(pos, "x") and hasattr(pos, "y"):
            x, y = pos.x, pos.y
        else:
            x, y = pos
        return (x * self.osu_pixel_multiplier + self.actual_placement_offset[0] - self.object_size // 2,
                y * self.osu_pixel_multiplier + self.actual_placement_offset[1] - self.object_size // 2)

    def get_cursor_position(self, position):
        return (self.actual_placement_offset[0]+position[0],
                self.actual_placement_offset[1]+position[1])
