import subprocess
import time

DEVICE = "plughw:CARD=Device,DEV=0"
FREQUENCY = "1200"
PAUSE_SECONDS = 0.2


def beep_once():
    subprocess.run(
        [
            "speaker-test",
            "-D", DEVICE,
            "-t", "sine",
            "-f", FREQUENCY,
            "-l", "1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def main():
    try:
        while True:
            beep_once()
            time.sleep(PAUSE_SECONDS)
    except KeyboardInterrupt:
        print("Stopped beep test.")


if __name__ == "__main__":
    main()
