import logging
import subprocess
import time

import pyperclip
from openai import OpenAI
from pynput import keyboard
from pynput.keyboard import Controller, Key

from prompts import TRANSLATE_TO_RUSSIAN_SYSTEM_PROMPT, CORRECT_ENGLISH_SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = "translategemma:12b"


class Handler:

    def __init__(self, system_prompt: str) -> None:
        self._system_prompt = system_prompt
        self._keyboard = Controller()

    def _get_selected_text(self) -> str:
        original_clipboard = pyperclip.paste()

        self._keyboard.press(Key.cmd)
        self._keyboard.press("c")
        self._keyboard.release("c")
        self._keyboard.release(Key.cmd)

        time.sleep(0.1)

        selected_text = pyperclip.paste()

        pyperclip.copy(original_clipboard)

        return selected_text

    def _play_sound(self, name: str) -> None:
        subprocess.Popen(
            [
                "afplay",
                f"/System/Library/Sounds/{name}.aiff",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _rephrase_text(self, text: str) -> str:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": self._system_prompt,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )

        return response.choices[0].message.content.strip()

    def handle(self):
        selected_text = self._get_selected_text()
        logger.info("Selected text: %s", selected_text)

        if not selected_text:
            logger.warning("No text selected")
            return

        self._play_sound("Funk")
        rephrased_text = self._rephrase_text(selected_text)

        pyperclip.copy(rephrased_text)
        self._play_sound("Bottle")


if __name__ == "__main__":
    translate_to_russian_handler = Handler(system_prompt=TRANSLATE_TO_RUSSIAN_SYSTEM_PROMPT)
    correct_english_handler = Handler(system_prompt=CORRECT_ENGLISH_SYSTEM_PROMPT)

    hotkeys = {
        '<ctrl>+<cmd>+r': translate_to_russian_handler.handle,
        '<ctrl>+<cmd>+e': correct_english_handler.handle,
    }

    with keyboard.GlobalHotKeys(hotkeys) as listener:
        listener.join()
