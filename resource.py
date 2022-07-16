from os import path
import pygame
import math
from enums import SkinOption


class ResourceManager:
    def __init__(self, resolution):
        self.resolution = resolution
        self.path = "resources"
        self.skin = SkinManager(
            path.join(self.path, "default_skin"), resolution)
        self.beatmap = BeatmapResourceManager()

        pekora = pygame.image.load(path.join(self.path, "pekora.png"))
        self.pekora = pygame.transform.smoothscale(pekora, (128, 128)).convert_alpha()
        self.font_size = int(16 * self.resolution.screen_size[1] / 1080)
        self.font = pygame.font.Font(path.join(self.path, "Torus.otf"), self.font_size)
        self.pekora_font = pygame.font.Font(path.join(self.path, "Torus.otf"),
                                            int(24 * self.resolution.screen_size[1] / 1080))

    def load_skin(self, skin_path):
        self.skin.load_skin(skin_path)

    def load_map(self, map_path):
        self.beatmap.path = map_path
        self.beatmap.load_map()
        self.skin.on_new_beatmap()


class BaseManager:
    def parse_file_name(self, name, animation=False):
        a = name.split(".")
        base_name, ext = ".".join(a[:-1]), a[-1]
        ret = (path.join(self.path, name), path.join(self.path, f"{base_name}@2x.{ext}"))
        if animation:
            ret += (path.join(self.path, f"{base_name}0.{ext}"), path.join(self.path, f"{base_name}0@2x.{ext}"))
        return ret

    def format_animation_name(self, a_path, i):
        root, name = path.split(a_path)
        name = name.split(".")
        base_name, ext = ".".join(name[:-1]), name[-1]
        if base_name.endswith("@2x"):
            return path.join(root, f"{base_name[:-3]}{str(i)}@2x.{ext}")
        return path.join(root, f"{base_name}{str(i)}.{ext}")

    def get_animations(self, a_path):
        i = 0
        while True:
            frame = self.format_animation_name(a_path, i)
            if not path.exists(frame):
                break
            yield pygame.image.load(frame).convert_alpha()
            i += 1

    def load_animation(self, name):
        sd, hd, sd_a, hd_a = self.parse_file_name(name, True)
        for a in ((hd_a, hd), (sd_a, sd)):
            if path.exists(a[0]):
                return list(self.get_animations(a[1]))
        for s in (hd, sd):
            if path.exists(s):
                return [pygame.image.load(s).convert_alpha()]

    def load_image(self, name):
        sd, hd = self.parse_file_name(name)
        if path.exists(hd):
            return pygame.image.load(hd).convert_alpha()
        if path.exists(sd):
            return pygame.image.load(sd).convert_alpha()

    def load_audio(self, name):
        pass


class SkinManager(BaseManager):
    """
    Manages all the resources of a skin such as hit objects and hit sounds.
    """

    def __init__(self,  skin_path=None, resolution=None):
        if skin_path is not None:
            self.resolution = resolution
            self.path = skin_path
            self.config = SkinConfigParser(path.join(skin_path, "skin.ini"))

        self._hitcircles = self.create_combo_color_surfaces(self.load_image("hitcircle.png"))
        self.hitcircles = []
        self._hitcircleoverlay = self.load_image("hitcircleoverlay.png")
        self.hitcircleoverlay = None
        self._approachcircle = self.create_combo_color_surfaces(self.load_image("approachcircle.png"))
        self.approachcircle = None
        self._sliderstartcircles = self.create_combo_color_surfaces(self.load_image("sliderstartcircle.png"))
        self.sliderstartcircles = []
        self._sliderstartcircleoverlay = self.load_image("sliderstartcircleoverlay.png")
        self.sliderstartcircleoverlay = None
        self._sliderball = self.load_animation("sliderb.png")
        self.sliderball = []
        self._sliderfollowcircle = self.load_animation("sliderfollowcircle.png")
        self.sliderfollowcircle = []
        self._defaults = [self.load_image(f"default-{num}.png") for num in range(0, 10)]
        self.defaults = []

    def load_skin(self, path):
        self.path = path
        self.__init__()

    def resize(self, img):
        return pygame.transform.smoothscale(img, (self.resolution.object_size, self.resolution.object_size))

    def scale(self, num_img, direction="v", downscale=1.0):
        w, h = num_img.get_size()
        if direction == "v":
            size = (self.resolution.object_size / h * w * downscale,
                    self.resolution.object_size * downscale)
        elif direction == "h":
            size = (self.resolution.object_size * downscale,
                    self.resolution.object_size / w * h * downscale)
        else:
            raise ValueError("direction must be either 'v' or 'h'")
        return pygame.transform.smoothscale(num_img, size)

    def create_combo_color_surfaces(self, surf):
        if surf is None:
            return
        surfs = [surf.copy() for _ in range(len(self.config.combo_colors))]
        self.tint(surfs)
        return surfs

    def tint(self, imgs):
        for surf, color in zip(imgs, self.config.combo_colors):
            surf.fill(color, special_flags=pygame.BLEND_RGBA_MULT)

    def on_new_beatmap(self):
        self.hitcircles = list(map(self.resize, self._hitcircles))
        if self.sliderstartcircles:
            self.sliderstartcircles = [self.resize(sliderstartcircles) for sliderstartcircles in self._sliderstartcircles]
        self.hitcircleoverlay = self.resize(self._hitcircleoverlay)
        if self.sliderstartcircleoverlay is not None:
            self.sliderstartcircleoverlay = self.resize(self._sliderstartcircleoverlay)
        self.sliderball = list(map(self.create_combo_color_surfaces, map(self.resize, self._sliderball)))
        self.sliderfollowcircle = list(map(self.resize, self._sliderfollowcircle))
        self.defaults = list(map(lambda d: self.scale(d, downscale=0.4), self._defaults))

    def make_approach_circle(self, size, combo_color):
        self.approachcircle = pygame.transform.smoothscale(self._approachcircle[combo_color], (size, size))

    def get_circle_elements(self, combo_color, is_slider=False):
        hitcircle = self.hitcircles[combo_color]
        hitcircleoverlay = self.hitcircleoverlay
        if is_slider and self.sliderstartcircleoverlay is not None:
            hitcircleoverlay = self.sliderstartcircleoverlay
        if is_slider and self.sliderstartcircles:
            hitcircle = self.sliderstartcircles[combo_color]
        return hitcircle, hitcircleoverlay


class SkinConfigParser:
    LATEST_VERSION = "2.7"
    VALID_VERSIONS = ["1.0", "2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"]
    configs = {  # {"Config name": "default value"}
        "Name": "",
        "Author": "",
        "Version": "1.0",
        "AnimationFramerate": -1,
        "AllowSliderBallTint": False,  # TODO: implement
        "ComboBurstRandom": False,
        "CursorCentre": True,
        "CursorRotate": True,
        "CursorTrailRotate": True,
        "CustomComboBurstSounds": [],
        "HitCircleOverlayAboveNumber": True,
        "LayeredHitSounds": True,
        "SliderBallFlip": True,  # TODO: implement
        "SpinnerFadePlayfield": False,
        "SpinnerFrequencyModule": True,
        "SpinnerNoBlink": False,
        "Combo1": (255, 192, 0),
        "Combo2": (0, 202, 0),
        "Combo3": (18, 124, 255),
        "Combo4": (242, 24, 57),
        "Combo5": None,
        "Combo6": None,
        "Combo7": None,
        "Combo8": None,
        "InputOverlayText": (0, 0, 0),
        "MenuGlow": (0, 78, 155),
        "SliderBall": (2, 170, 255),
        "SliderBorder": (255, 255, 255),
        "SliderTrackOverride": SkinOption.CURRENT_COMBO_COLOR,
        "SongSelectActiveText": (0, 0, 0),
        "SongSelectInactiveText": (255, 255, 255),
        "SpinnerBackground": (100, 100, 100),
        "StarBreakAdditive": (255, 182, 193),
        "HitCirclePrefix": "default",  # TODO: look into
        "HitCircleOverlap": -2,  # TODO: look into
        "ScorePrefix": "score",
        "ScoreOverlap": 0,
        "ComboPrefix": "score",
        "ComboOverlap": 0,

        # TODO: CatchTheBeat and Mania sections
    }

    def __init__(self, skin_ini_path):
        self.path = skin_ini_path

        file_exists = path.exists(self.path)

        # Default values
        self.version = self.LATEST_VERSION if not file_exists else self.configs["Version"]
        for config, default in self.configs.items():
            if config == "Version":
                continue
            setattr(self, self.format_name(config), default)

        if file_exists:
            self.load_config()

        self.combo_colors = []
        for i in (2, 3, 4, 5, 6, 7, 8, 1):
            color = getattr(self, f"combo_{i}")
            if color is not None:
                self.combo_colors.append(color)

    def load_config(self):
        with open(self.path, "r") as f:
            for line in f.readlines():
                if not line.strip():
                    continue
                split = line.split(":")
                var = split[0].strip()
                if var not in self.configs:
                    continue

                value = ":".join(split[1:]).strip()
                default_value = self.configs[var]
                if isinstance(default_value, tuple):
                    value = tuple(map(lambda n: int(n.strip()), value.split(",")))
                elif isinstance(default_value, int):
                    value = int(value)
                elif isinstance(default_value, bool):
                    value = bool(value)
                elif isinstance(default_value, list):
                    value = list(map(str.strip, value.split(",")))

                if var == "Version" and value not in self.VALID_VERSIONS:
                    self.version = "1.0"
                    continue

                setattr(self, self.format_name(var), value)

    @staticmethod
    def format_name(name):
        name = name[0].lower() + name[1:]
        return "".join([char if char.islower() else "_"+char.lower() for char in name])

    def get_animation_frame(self, start, current, frames, combo_color=None):
        framerate = self.animation_framerate
        if framerate == -1:
            framerate = len(frames)
        frame = frames[math.ceil((current - start) / 1000 * framerate) % len(frames)]
        if isinstance(frame, list):
            return frame[combo_color]
        return frame


class BeatmapResourceManager(BaseManager):
    """
    Manages all the resources of a beatmap such as background, custom skin elements, hit sounds, etc.
    """

    def __init__(self):
        pass

    def load_map(self):
        pass
