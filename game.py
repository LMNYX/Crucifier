import pygame
import tkinter as tk
from tkinter import filedialog
from resource import ResourceManager
from util import ResolutionManager
from beatmap_reader import SongsFolder


class BaseState:
    def handle_event(self, event):
        pass

    def handle_state(self):
        pass

    def draw(self):
        pass

    def on_quit(self):
        pass


class GameLoop:
    def __init__(self, states, config):
        self.states = states
        self.config = config
        self.current_state = None
        self.running = False
        self.switched = False
        self.clock = pygame.time.Clock()
        self.fps_cap = config.get("rendering.fps_cap")

        print("Loading songs folder...")
        self.songs_folder = SongsFolder.from_path(config.get('songs_path')
                                                  if config.get('songs_path') is not None
                                                  else self.ask_songs_folder())
        print("Songs folder loaded.")

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("osu!simulation")
        res = config.get("rendering.resolution")
        self.screen = pygame.display.set_mode((res.get("width"), res.get("height")))

        self.resolution = ResolutionManager(self.screen.get_size())
        self.resources = ResourceManager(self.resolution)

    def ask_songs_folder(self):
        root = tk.Tk()
        root.withdraw()

        folder = filedialog.askdirectory()
        self.config.set("songs_path", folder).save()
        return folder

    def switch_state(self, state, *args, **kwargs):
        self.current_state = self.states[state](self, *args, **kwargs)
        self.switched = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.current_state.on_quit()
                return
            self.current_state.handle_event(event)

    def run(self, starting_state, *args, **kwargs):
        self.switch_state(starting_state, *args, **kwargs)
        self.running = True
        while self.running:
            self.handle_events()
            if not self.running: break
            if self.switched:
                self.switched = False
                continue
            self.current_state.handle_state()
            self.current_state.draw()

            pygame.display.update()
            self.clock.tick(self.fps_cap)

        pygame.quit()
