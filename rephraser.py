import subprocess
import time

import pyperclip
from openai import OpenAI
from pynput import keyboard
from pynput.keyboard import Controller, Key

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

    keyboard_ = Controller()
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


def replace_selected_text(text: str) -> None:
    keyboard_ = Controller()
    keyboard_.type(text)


def on_activate():
    selected_text = get_selected_text()

    if not selected_text:
        return

    play_sound("Tink")
    result = rephrase_text(selected_text)
    if selected_text == result:
        play_sound("Funk")
        return

    replace_selected_text(result)


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
