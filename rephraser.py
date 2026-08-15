import logging
import subprocess
import time
from difflib import SequenceMatcher

import pyperclip
from openai import OpenAI
from pynput import keyboard
from pynput.keyboard import Controller, Key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = "translategemma:12b"
SYSTEM_PROMPT = """
You are an English teacher helping an A2 (Pre-Intermediate) English learner.

Check the text provided by the user.

Your task:
- If the text is correct and natural, return it EXACTLY unchanged.
- If the text contains grammar mistakes, incorrect words, unnatural expressions, or Russian words that should be in English, correct them.
- When correcting the text, use simple and natural A2-level English.

Rules:
- Preserve the original meaning exactly.
- Do not add or remove information.
- Do not rewrite text that is already correct.
- Do not simplify correct sentences just because they could be written in simpler English.
- Make only necessary corrections.
- Do not use rare words or unnecessary idioms.
- Preserve names, dates, numbers, URLs, and Obsidian Markdown formatting.
- Preserve the original Markdown structure.
- If Russian text appears inside the text, translate it into English when necessary.
- Return ONLY the resulting text.
- Do not add explanations, comments, labels, quotes, or Markdown code fences.

The output must be either:
1. The original text, character-for-character unchanged, if no correction is needed.
2. The corrected A2-level text, if corrections are needed.
"""

keyboard_ = Controller()

def play_sound(name: str) -> None:
    subprocess.Popen(
        [
            "afplay",
            f"/System/Library/Sounds/{name}.aiff",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_selected_text() -> str:
    original_clipboard = pyperclip.paste()

    keyboard_.press(Key.cmd)
    keyboard_.press("c")
    keyboard_.release("c")
    keyboard_.release(Key.cmd)

    time.sleep(0.05)

    selected_text = pyperclip.paste()

    pyperclip.copy(original_clipboard)

    return selected_text


def rephrase_text(text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
    )

    return response.choices[0].message.content.strip()



def apply_diff(current: str, target: str):
    sm = SequenceMatcher(None, current, target)
    opcodes = sm.get_opcodes()
    pos = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            length = i2 - i1
            for _ in range(length):
                keyboard_.press(Key.right)
                keyboard_.release(Key.right)
                time.sleep(0.075)
            pos += length

        elif tag == 'delete':
            length = i2 - i1
            for _ in range(length):
                keyboard_.press(Key.delete)
                keyboard_.release(Key.delete)
                time.sleep(0.075)
        elif tag == 'insert':
            text = target[j1:j2]
            for symbol in text:
                keyboard_.type(symbol)
                time.sleep(0.075)
            pos += len(text)

        elif tag == 'replace':
            length = i2 - i1
            for _ in range(length):
                keyboard_.press(Key.delete)
                keyboard_.release(Key.delete)
                time.sleep(0.075)
            text = target[j1:j2]
            keyboard_.type(text)
            pos += len(text)


def on_activate():
    selected_text = get_selected_text()
    logger.info("Selected text: %s", selected_text)

    if not selected_text:
        logger.warning("No text selected")
        return

    play_sound("Tink")
    rephrased_text = rephrase_text(selected_text)

    if selected_text == rephrased_text:
        play_sound("Funk")
        return

    # Сворачиваем выделение в начало (курсор становится в начале бывшего selection)
    keyboard_.press(Key.left)
    keyboard_.release(Key.left)
    time.sleep(0.02)
    apply_diff(selected_text, rephrased_text)


hotkey = keyboard.HotKey(
    keyboard.HotKey.parse("<ctrl>+<cmd>+r"),
    on_activate,
)


if __name__ == "__main__":
    with keyboard.Listener(
            on_press=hotkey.press,
            on_release=hotkey.release,
    ) as listener:
        listener.join()
