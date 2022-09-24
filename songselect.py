from game import BaseState


class SongSelect(BaseState):
    def __init__(self, game):
        self.game = game

        self.songs_folder = game.songs_folder

    def draw(self):
        pass
