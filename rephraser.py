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
    prompt = f"""
Rewrite the following text to make it more natural and clear.

Keep the original meaning.
Do not add any explanations.
Return only the rewritten text.

Text:
{text}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
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

    result = rephrase_text(selected_text)

    replace_selected_text(result)


hotkey = keyboard.HotKey(
    keyboard.HotKey.parse("<ctrl>+<cmd>+r"),
    on_activate,
)

# Это настоящий и очень важный тест

if __name__ == "__main__":
    with keyboard.Listener(
            on_press=hotkey.press,
            on_release=hotkey.release,
    ) as listener:
        listener.join()
