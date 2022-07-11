from os import path
import pygame


class ResourceManager:
    def __init__(self, resolution):
        self.resolution = resolution
        self.path = "resources"
        self.skin = SkinManager(
            path.join(self.path, "default_skin"), resolution)
        self.beatmap = BeatmapResourceManager()

        pekora = pygame.image.load(path.join(self.path, "pekora.png"))
        self.pekora = pygame.transform.smoothscale(pekora, (128, 128))
        self.font = pygame.font.Font(
            path.join(self.path, "Torus.otf"), int(16 * self.resolution.screen_size[1] / 1080))
        self.pekora_font = pygame.font.Font(
            path.join(self.path, "Torus.otf"), int(24 * self.resolution.screen_size[1] / 1080))

    def load_skin(self, skin_path):
        self.skin.path = skin_path
        self.skin.load_skin()

    def load_map(self, map_path):
        self.beatmap.path = map_path
        self.beatmap.load_map()
        self.skin.on_new_beatmap()


class BaseManager:
    def load_image(self, name):
        a = name.split(".")
        base_name, ext = ".".join(a[:-1]), a[-1]
        hd = path.join(self.path, f"{base_name}@2x.{ext}")
        if path.exists(hd):
            return pygame.image.load(hd)
        return pygame.image.load(path.join(self.path, name))

    def load_audio(self, name):
        pass


class SkinManager(BaseManager):
    """
    Manages all the resources of a skin such as hit objects and hit sounds.
    """

    def __init__(self,  skin_path, resolution):
        self.resolution = resolution
        self.path = skin_path

        self.load_skin()

    def load_skin(self):
        self._hitcircle = self.load_image("hitcircle.png")
        self.hitcircle = None

    def on_new_beatmap(self):
        self.hitcircle = pygame.transform.smoothscale(self._hitcircle, (self.resolution.object_size,
                                                                        self.resolution.object_size))


class BeatmapResourceManager(BaseManager):
    """
    Manages all the resources of a beatmap such as background, custom skin elements, hit sounds, etc.
    """

    def __init__(self):
        pass

    def load_map(self):
        pass
