import pygame


class AudioManager:
    def __init__(self, volume=0.25, is_disabled=False, channel_amount=32):
        pygame.mixer.init()

        self.channel_amount = channel_amount

        # for overlapping sounds, channel 0 is reserved for beatmap music
        pygame.mixer.set_num_channels(channel_amount)

        self.time_after_last_modified_volume = -750
        self.is_disabled = is_disabled
        self.volume = volume if not is_disabled else 0

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
            pygame.mixer.Channel(1).load(pathto)
        return channel if not is_beatmap_audio else 0

    def play_audio(self, offset=0, channel=0):
        if self.is_disabled:
            return
        if channel == 0:
            pygame.mixer.music.play()
            pygame.mixer.music.set_pos(offset / 1000)
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

    def load_and_play_audio(self, pathto, offset=0, is_beatmap_audio=False):
        if self.is_disabled or (is_beatmap_audio and self.beatmap_audio_playing):
            return
        if is_beatmap_audio:
            self.beatmap_audio_playing = True
        channel = self.load_audio(pathto, is_beatmap_audio=is_beatmap_audio)
        self.play_audio(offset=offset, channel=channel)
