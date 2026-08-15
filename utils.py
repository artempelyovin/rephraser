import subprocess
from openai import OpenAI


# macOS only!
def play_sound(name: str) -> None:
    subprocess.Popen(
        [
            "afplay",
            f"/System/Library/Sounds/{name}.aiff",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ask_llm(client: OpenAI, model: str, system_prompt: str, text: str, ) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
    )

    return response.choices[0].message.content.strip()
