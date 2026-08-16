import sys
import time

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

from pynput import keyboard
import pyperclip


# Опционально: убираем приложение из Dock, если установлен pyobjc.
# Для настоящего background .app лучше дополнительно указать LSUIElement в Info.plist.
try:
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
except Exception:
    NSApplication = None


# macOS virtual key codes.
# Это помогает меньше зависеть от раскладки клавиатуры.
MACOS_VK_E = 0x0E  # физическая клавиша E
MACOS_VK_C = 0x08  # физическая клавиша C

try:
    C_KEY = keyboard.KeyCode.from_vk(MACOS_VK_C)
except Exception:
    C_KEY = "c"


CTRL_KEYS = {
    getattr(keyboard.Key, name)
    for name in ("ctrl", "ctrl_l", "ctrl_r")
    if hasattr(keyboard.Key, name)
}

CMD_KEYS = {
    getattr(keyboard.Key, name)
    for name in ("cmd", "cmd_l", "cmd_r")
    if hasattr(keyboard.Key, name)
}


class Overlay(QWidget):
    """
    Небольшая плашка, которая показывается поверх остальных окон
    и не забирает фокус.
    """

    def __init__(self):
        flags = (
            Qt.ToolTip
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )

        super().__init__(None, flags)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._label = QLabel(self)
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(360)
        self._label.setTextInteractionFlags(Qt.NoTextInteraction)
        self._label.setStyleSheet(
            """
            QLabel {
                background: rgba(28, 28, 30, 0.92);
                color: #ffffff;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        # На случай очень большого выделения.
        if len(text) > 800:
            text = text[:800] + "…"

        self._label.setText(text)
        self.adjustSize()

        # Показываем плашку около курсора мыши.
        # Это упрощение: реальные координаты выделения без Accessibility API получить сложно.
        pos = QCursor.pos()

        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()

        x = pos.x() - self.width() // 2
        y = pos.y() + 24

        # Не даем плашке уехать за пределы экрана.
        x = max(geo.left(), min(x, geo.right() - self.width()))
        y = max(geo.top(), min(y, geo.bottom() - self.height()))

        self.move(x, y)
        self.show()

        # Плашка исчезает через 2.5 секунды.
        self._timer.start(2500)


class HotkeyWatcher(QObject):
    """
    Слушает глобальные нажатия клавиш через pynput.

    pynput работает в отдельном потоке, поэтому для безопасного
    перехода в главный Qt-поток используем Qt Signal.
    """

    triggered = Signal()

    def __init__(self):
        super().__init__()

        self._pressed = set()
        self._last_trigger = 0.0

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def _key_id(self, key):
        """
        Приводим клавишу к удобному идентификатору.

        Для macOS дополнительно проверяем virtual key code,
        чтобы хоткей продолжал работать даже с другой раскладкой.
        """
        if isinstance(key, keyboard.KeyCode):
            # Физическая клавиша E на macOS.
            if getattr(key, "vk", None) == MACOS_VK_E:
                return "e"

            if key.char is not None:
                return key.char.lower()

            return key

        return key

    def _on_press(self, key):
        k = self._key_id(key)
        if k is None:
            return

        self._pressed.add(k)

        if self._pressed_match():
            now = time.monotonic()

            # Примитивный debounce, чтобы автоповтор не вызывал много срабатываний.
            if now - self._last_trigger > 0.7:
                self._last_trigger = now
                self.triggered.emit()

    def _on_release(self, key):
        self._pressed.discard(self._key_id(key))

    def _pressed_match(self):
        has_ctrl = bool(self._pressed & CTRL_KEYS)
        has_cmd = bool(self._pressed & CMD_KEYS)
        has_e = "e" in self._pressed

        return has_ctrl and has_cmd and has_e


def main():
    app = QApplication(sys.argv)

    # Чтобы приложение не выходило, когда скрыты все окна.
    app.setQuitOnLastWindowClosed(False)

    # Если есть pyobjc, делаем приложение accessory-типа:
    # без обычной иконки в Dock.
    if NSApplication is not None:
        try:
            NSApplication.sharedApplication().setActivationPolicy_(
                NSApplicationActivationPolicyAccessory
            )
        except Exception:
            pass

    overlay = Overlay()
    watcher = HotkeyWatcher()

    kb = keyboard.Controller()

    def show_clipboard():
        try:
            text = pyperclip.paste()
        except Exception:
            # Запасной вариант через Qt, если pyperclip вдруг не сработал.
            text = QGuiApplication.clipboard().text()

        overlay.show_text(text)

    def copy_selected_text():
        """
        Посылаем Cmd+C в активное приложение.

        Важно: после нажатия хоткей лучше быстро отпускать,
        иначе физически зажатый Ctrl/Cmd может повлиять на посылаемое событие.
        """
        with kb.pressed(keyboard.Key.cmd):
            kb.press(C_KEY)
            kb.release(C_KEY)

        # Даем приложению время положить текст в буфер.
        # Если в тяжелых приложениях текст не успевает скопироваться,
        # увеличьте значение, например до 350–500 мс.
        QTimer.singleShot(250, show_clipboard)

    def on_hotkey():
        # Небольшая задержка, чтобы пользователь успел отпустить хоткей.
        QTimer.singleShot(120, copy_selected_text)

    watcher.triggered.connect(on_hotkey)
    watcher.start()

    app.aboutToQuit.connect(watcher.stop)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()