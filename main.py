import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import argparse
import time
from pathlib import Path
from threading import Thread

import pygame
from pydub import AudioSegment, playback
from rich.console import Console
from rich.progress import track


class App:
    def __init__(self):
        self.c = Console()

        pygame.init()
        pygame.joystick.init()
        self.joysticks = [
            pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())
        ]
        self.vibro_chunks = []

    def run(self, audio_file: str):
        if not self.joysticks:
            return self.c.print(
                "[red]No joysticks found. Please connect one and try again.[/]"
            )
        for j in self.joysticks:
            j.stop_rumble()
        if not Path(audio_file).exists():
            self.c.print(f"File {audio_file} does not exist", style="bold red")
            return
        audio = AudioSegment.from_file(audio_file)
        chunk_size = 100
        for i in track(
            range(0, len(audio), chunk_size),
            total=len(range(0, len(audio), chunk_size)),
            description="[b green]Chunking audio[/]",
        ):
            chunk = audio[i : i + chunk_size]

            low_hz = chunk.low_pass_filter(80)
            if low_hz.max > 12500:
                self.vibro_chunks.append(2)
            elif low_hz.max > 10000:
                self.vibro_chunks.append(1)
            else:
                self.vibro_chunks.append(0)
        t = Thread(
            target=self.thread_rumble,
            args=(
                self.vibro_chunks,
                chunk_size,
            ),
        )
        t2 = Thread(target=playback.play, args=(audio,))
        t.start()
        t2.start()

    def thread_rumble(self, chunks, chunk_size: int):
        for i in track(
            chunks,
            total=len(chunks),
            description="[b green]Playing audio[/]",
        ):
            if i == 2:
                self.joysticks[0].rumble(1, 1, chunk_size // 10)
            elif i == 1:
                self.joysticks[0].rumble(1, 1, chunk_size // 100)
            else:
                self.joysticks[0].stop_rumble()
            time.sleep(0.1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Turn your DualShock4 into "subwoofer"'
    )
    parser.add_argument("-i", "--input", help="Input audio file", required=True)
    args = parser.parse_args()
    ex = App()
    ex.run(args.input)
