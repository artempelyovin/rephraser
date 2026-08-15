import time

import pyperclip
from openai import OpenAI
from pynput import keyboard
from pynput.keyboard import Controller, Key

from prompts import TRANSLATE_TO_RUSSIAN_SYSTEM_PROMPT, CORRECT_ENGLISH_SYSTEM_PROMPT
from utils import play_sound, ask_llm


class Handler:
    def __init__(self, system_prompt: str, model: str) -> None:
        self._system_prompt = system_prompt
        self._model = model

        self._openai_client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
        self._keyboard = Controller()

    def _get_selected_text(self) -> str:
        self._keyboard.press(Key.cmd)
        self._keyboard.press("c")
        self._keyboard.release("c")
        self._keyboard.release(Key.cmd)
        time.sleep(0.1)
        return pyperclip.paste().strip()

    def handle(self):
        selected_text = self._get_selected_text()
        if not selected_text:
            return

        play_sound("Funk")
        rephrased_text = ask_llm(
            client=self._openai_client, model=self._model, system_prompt=self._system_prompt, text=selected_text
        )

        if rephrased_text == selected_text:
            play_sound("Hero")
            pyperclip.copy("")
            return

        pyperclip.copy(rephrased_text)
        play_sound("Bottle")


if __name__ == "__main__":
    model = "translategemma:12b"
    translate_to_russian_handler = Handler(system_prompt=TRANSLATE_TO_RUSSIAN_SYSTEM_PROMPT, model=model)
    correct_english_handler = Handler(system_prompt=CORRECT_ENGLISH_SYSTEM_PROMPT, model=model)

    hotkeys = {
        '<ctrl>+<cmd>+r': translate_to_russian_handler.handle,
        '<ctrl>+<cmd>+e': correct_english_handler.handle,
    }

    with keyboard.GlobalHotKeys(hotkeys) as listener:
        listener.join()
