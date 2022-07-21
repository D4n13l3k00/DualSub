import subprocess
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


class DualSub:
    def __init__(self):
        self.c = Console()

        pygame.init()
        pygame.joystick.init()
        self.joysticks = [
            pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())
        ]
        self.bass_chunks = []

    def chunk_bass_audio(self, audio: AudioSegment, chunk_size: int):
        for i in track(
            list(range(0, len(audio), chunk_size)),
            description="[b green]Chunking audio[/]",
        ):
            chunk = audio[i : i + chunk_size]  # type: AudioSegment

            low_hz = chunk.low_pass_filter(80)  # type: AudioSegment
            if low_hz.max > 12500:
                self.bass_chunks.append(2)
            elif low_hz.max > 10000:
                self.bass_chunks.append(1)
            else:
                self.bass_chunks.append(0)

    def run(self, args):
        if os.name != "posix":
            self.c.print("[--led] `{}` is not supported yet".format(os.name))
            args.led = False
        if not self.joysticks:
            if args.led:
                self.c.print(
                    "[red]No joystick found. Please connect a joystick and try again. Program still work with LED arg[/red]"
                )
            else:
                return self.c.print(
                    "[red]No joysticks found. Please connect one and try again.[/]"
                )
        for j in self.joysticks:
            j.stop_rumble()
        audio_file = args.input  # type: str
        if not Path(audio_file).exists():
            self.c.print(f"File {audio_file} does not exist", style="bold red")
            return
        audio = AudioSegment.from_file(audio_file)  # type: AudioSegment
        chunk_size = 100  # ms
        self.chunk_bass_audio(audio, chunk_size)

        play_thread = Thread(target=playback.play, args=(audio,))
        if self.joysticks:
            vibro_thread = Thread(
                target=self.thread_rumble,
                args=(
                    self.bass_chunks,
                    chunk_size,
                ),
            )
            vibro_thread.start()
        if args.led:
            led_thread = Thread(
                target=self.thread_led,
                args=(self.bass_chunks,),
            )
            led_thread.start()
        play_thread.start()

    @staticmethod
    def thread_led(chunks):
        for i in chunks:
            if i == 2:
                subprocess.call(["xset", "led", "named", "Scroll Lock"])
            else:
                subprocess.call(["xset", "-led", "named", "Scroll Lock"])
            time.sleep(0.1)

    def thread_rumble(self, chunks, chunk_size: int):
        for i in track(
            chunks,
            total=len(chunks),
            description="[b green]Playing audio[/]",
        ):
            if i == 2:
                self.joysticks[0].rumble(1, 1, chunk_size // 10)
            elif i == 1:
                self.joysticks[0].rumble(0.5, 0.5, chunk_size // 100)
            else:
                self.joysticks[0].stop_rumble()
            time.sleep(0.1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Turn your DualShock4 into "subwoofer"'
    )
    parser.add_argument("-i", "--input", help="Input audio file", required=True)
    parser.add_argument(
        "-l",
        "--led",
        help="Turn keyboard blinking (If ur kbd use ScrollLock for LED)",
        default=False,
        action="store_true",
    )

    args = parser.parse_args()
    ex = DualSub()
    ex.run(args)
