#!/usr/bin/env python3

# prerequisites: as described in https://alphacephei.com/vosk/install and also python module `sounddevice` (simply run command `pip install sounddevice`)
# Example usage using Dutch (nl) recognition model: `python test_microphone.py -m nl`
# For more help run: `python test_microphone.py -h`
# vosk_recognizer.py

#!/usr/bin/env python3
"""
Vosk microphone recognition as a reusable class.

- Press Ctrl+C to stop when running from CLI
- Optional raw PCM dump via --filename (same as your original script)
"""

import argparse
import os
import queue
import sys
import threading
from typing import Optional, Callable

import sounddevice as sd
from vosk import Model, KaldiRecognizer


def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text


class VoskMicRecognizer:
    """
    Simple wrapper around sounddevice + Vosk.

    Parameters
    ----------
    model : str
        Either a path to an unzipped Vosk model directory, or a language code for Model(lang=...).
    device : int | str | None
        Input device index or substring (sounddevice syntax).
    samplerate : int | None
        If None, uses the device's default input samplerate.
    blocksize : int
        Number of frames per block.
    filename : str | None
        If provided, raw PCM16 bytes are dumped here (same behavior as original script).
    on_partial : Callable[[str], None] | None
        Callback for partial results (JSON string from Vosk).
    on_result : Callable[[str], None] | None
        Callback for final results (JSON string from Vosk).
    """

    def __init__(
        self,
        model: str,
        device=None,
        samplerate: Optional[int] = None,
        blocksize: int = 8000,
        filename: Optional[str] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
    ):
        self.model_arg = model
        self.device = device
        self.blocksize = blocksize
        self.user_samplerate = samplerate
        self.filename = filename

        self.on_partial = on_partial
        self.on_result = on_result

        self._queue = queue.Queue()
        self._stream = None
        self._rec = None
        self._model = None
        self._samplerate = None
        self._dump_fh = None
        self._thread = None
        self._stop = threading.Event()

    # ---------- lifecycle ----------

    def start(self, background: bool = False):
        """Start the audio stream and recognition loop."""
        # samplerate
        if self.user_samplerate is None:
            device_info = sd.query_devices(self.device, "input")
            self._samplerate = int(device_info["default_samplerate"])
        else:
            self._samplerate = int(self.user_samplerate)

        # model
        if os.path.isdir(self.model_arg):
            self._model = Model(self.model_arg)
        else:
            # treat as language code (e.g. "en-us", "th")
            self._model = Model(lang=self.model_arg)

        # recognizer
        self._rec = KaldiRecognizer(self._model, self._samplerate)

        # optional dump file (raw PCM16, same as your original)
        if self.filename:
            self._dump_fh = open(self.filename, "wb")

        # audio stream
        self._stream = sd.RawInputStream(
            samplerate=self._samplerate,
            blocksize=self.blocksize,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )

        self._stop.clear()
        self._stream.start()

        if background:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        else:
            self._run_loop()

    def stop(self):
        """Stop recognition and close resources."""
        self._stop.set()
        # drain the queue quickly
        try:
            while not self._queue.empty():
                self._queue.get_nowait()
        except Exception:
            pass

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        if self._dump_fh:
            try:
                self._dump_fh.close()
            except Exception:
                pass
            self._dump_fh = None

        # keep model/rec around in case you want to restart; or set to None to free memory
        # self._rec = None
        # self._model = None

    # ---------- internals ----------

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self._queue.put(bytes(indata))

    def _run_loop(self):
        print("#" * 80)
        print(f"Listening at {self._samplerate} Hz (Ctrl+C to stop)")
        print("#" * 80)

        try:
            while not self._stop.is_set():
                try:
                    data = self._queue.get(timeout=0.25)
                except queue.Empty:
                    continue

                if self._rec.AcceptWaveform(data):
                    res = self._rec.Result()
                    if self.on_result:
                        self.on_result(res)
                    else:
                        print(res)
                else:
                    pres = self._rec.PartialResult()
                    if self.on_partial:
                        self.on_partial(pres)
                    else:
                        print(pres)

                if self._dump_fh is not None:
                    self._dump_fh.write(data)
        except KeyboardInterrupt:
            # allow Ctrl+C to bubble out when running in foreground
            pass

    # ---------- convenient properties ----------

    @property
    def samplerate(self) -> int:
        return self._samplerate or 0


# ---------------- CLI main ----------------

def build_arg_parser():
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("-l", "--list-devices", action="store_true",
                      help="show list of audio devices and exit")

    parser = argparse.ArgumentParser(
        description="Live microphone speech recognition with Vosk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[base],
    )
    parser.add_argument("-f", "--filename", type=str, metavar="FILENAME",
                        help="(optional) raw PCM16 file to store recording to")
    parser.add_argument("-d", "--device", type=int_or_str,
                        help="input device (numeric ID or substring)")
    parser.add_argument("-r", "--samplerate", type=int,
                        help="sampling rate (default: device default)")
    parser.add_argument("-m", "--model", type=str,
                        help="Vosk model path (unzipped dir) or language code (e.g., en-us, th). Default: en-us",
                        default="en-us")
    return base, parser


def main():
    base, parser = build_arg_parser()
    args, remaining = base.parse_known_args()

    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    args = parser.parse_args(remaining)

    rec = VoskMicRecognizer(
        model=args.model,             # path or language code
        device=args.device,
        samplerate=args.samplerate,
        filename=args.filename,
    )

    try:
        rec.start(background=False)   # Ctrl+C to stop
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        rec.stop()


if __name__ == "__main__":
    main()

