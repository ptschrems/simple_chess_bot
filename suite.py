import os
import tkinter as tk
from tkinter import filedialog
from typing import Optional
import chess


def SelectFenFile(initialDir: Optional[str] = None) -> Optional[str]:
    """Opens a native Windows file dialog to pick a FEN suite file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filePath = filedialog.askopenfilename(
        parent=root,
        title="Select FEN Test Suite File",
        initialdir=initialDir or os.path.dirname(__file__),
        filetypes=(
            ("FEN / Text files", "*.fen *.txt *.epd"),
            ("All files", "*.*"),
        ),
    )
    root.destroy()
    return filePath if filePath else None


def LoadFenList(filePath: str) -> list[str]:
    """Reads valid FEN strings from a file (one per line, ignoring blanks and # comments)."""
    fens: list[str] = []
    if not filePath or not os.path.isfile(filePath):
        return fens

    with open(filePath, "r", encoding="utf-8") as file:
        for rawLine in file:
            line = rawLine.strip()
            if not line or line.startswith("#"):
                continue
            # Validate FEN via python-chess before queuing
            try:
                chess.Board(line)
                fens.append(line)
            except ValueError:
                print(f"Skipping invalid FEN in suite: {line}")

    return fens


class FenSuiteRunner:
    """
    Queues two matches per FEN (swapping White and Black) for the two selected bots.
    """

    def __init__(self) -> None:
        self.queue: list[tuple[str, bool]] = []  # (fen, swapColors)
        self.totalGames = 0
        self.completedGames = 0
        self.isActive = False
        self.baseWhiteBot = "Human"
        self.baseBlackBot = "Human"

    def Start(self, fens: list[str], whiteBot: str, blackBot: str) -> bool:
        if not fens or whiteBot == "Human" or blackBot == "Human":
            return False

        self.baseWhiteBot = whiteBot
        self.baseBlackBot = blackBot
        self.queue = []
        for fen in fens:
            self.queue.append((fen, False))  # Game 1: whiteBot as White, blackBot as Black
            self.queue.append((fen, True))   # Game 2: blackBot as White, whiteBot as Black

        self.totalGames = len(self.queue)
        self.completedGames = 0
        self.isActive = True
        return True

    def Stop(self) -> None:
        self.queue.clear()
        self.totalGames = 0
        self.completedGames = 0
        self.isActive = False

    def PopNextMatch(self) -> Optional[tuple[str, str, str]]:
        """
        Returns (fen, whiteBotName, blackBotName) for the next queued game,
        or None if the suite has finished.
        """
        if not self.isActive or not self.queue:
            self.isActive = False
            return None

        fen, swap = self.queue.pop(0)
        self.completedGames += 1
        if swap:
            return fen, self.baseBlackBot, self.baseWhiteBot
        return fen, self.baseWhiteBot, self.baseBlackBot

    def GetProgressText(self) -> str:
        if not self.isActive:
            return ""
        return f"Suite: {self.completedGames}/{self.totalGames}"