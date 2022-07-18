import pygame
import random
from game import BaseState


class StartScreen(BaseState):
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.size = self.screen.get_size()
        self.clock = game.clock
        self.resources = game.resources
        self.songs_folder = game.songs_folder

        self.pekora_angle = 0
        self.status_message = ""

    def get_random_beatmapset(self):
        return random.choice(self.songs_folder.beatmapsets)

    def get_random_beatmap(self):
        return random.choice(self.get_random_beatmapset().beatmaps)

    def get_testing_map(self):
        for beatmapset in self.songs_folder.beatmapsets:
            for beatmap in beatmapset.beatmaps:
                if beatmap.path.endswith("ReeK - Sweets Rave Party (ft. L4hee) (mitsukai) [KAWAII RAVE COLLAB].osu"):
                    return beatmap

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.switch_state("play", self.get_random_beatmap())

    def handle_state(self):
        self.rotate_pekora()

    def rotate_pekora(self):
        self.pekora_angle += 1
        if self.pekora_angle > 360:
            self.pekora_angle = 0

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.draw_pekora()
        self.draw_fps()

    def draw_fps(self):
        fps_render = self.resources.font.render(
            f'FPS: {round(self.clock.get_fps())}', True, (255, 255, 255))
        self.screen.blit(fps_render, (self.size[0] - fps_render.get_width() - 4,
                                      self.size[1] - fps_render.get_height() - 4))

    def draw_pekora(self):
        rotated_image = pygame.transform.rotate(self.resources.pekora, self.pekora_angle)
        if self.status_message:
            pekora_status = self.resources.pekora_font.render(
                self.status_message, True, (255, 255, 255))
            self.screen.blit(pekora_status,
                             (self.size[0] / 2 - pekora_status.get_size()[0] / 2,
                              self.size[1] / 2 - pekora_status.get_size()[1] / 2 + self.size[1] * 0.2)
                             )
        self.screen.blit(rotated_image,
                         rotated_image.get_rect(
                             center=self.resources.pekora.get_rect(
                                 topleft=(self.size[0] / 2 - 64, self.size[1] / 2 - 64)).center).topleft)
