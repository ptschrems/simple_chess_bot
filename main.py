import os
import sys
import time
import ctypes
import threading
from typing import Optional, Callable
import pygame
import chess
import chess.engine
from results import RecordMatchResult, GetLeaderboardSummary, GetAvailableOpponents
from suite import SelectFenFile, LoadFenList, FenSuiteRunner

# Constants
BoardSize = 8
SquareSize = 80
BoardPixelSize = BoardSize * SquareSize
ControlPanelWidth = 240
WindowWidth = BoardPixelSize + ControlPanelWidth
WindowHeight = BoardPixelSize
FramesPerSecond = 60

# Custom Pygame event for thread-safe engine move dispatch
EngineMoveEventType = pygame.USEREVENT + 1

# DWM Attribute Constant for Windows 10/11 Dark Title Bar
DwmwaUseImmersiveDarkMode = 20

# Time Control Presets
TimeControlPresets: dict[str, dict] = {
    "0.1s / move": {"mode": "movetime", "time": 0.1},
    "0.2s / move": {"mode": "movetime", "time": 0.2},
    "0.5s / move": {"mode": "movetime", "time": 0.5},
    "1s / move":   {"mode": "movetime", "time": 1.0},
    "3s / move":   {"mode": "movetime", "time": 3.0},
    "5s / move":   {"mode": "movetime", "time": 5.0},
    "1+0":         {"mode": "clock", "base": 60.0,  "inc": 0.0},
    "1+1":         {"mode": "clock", "base": 60.0,  "inc": 1.0},
    "3+0":         {"mode": "clock", "base": 180.0, "inc": 0.0},
    "3+2":         {"mode": "clock", "base": 180.0, "inc": 2.0},
    "5+0":         {"mode": "clock", "base": 300.0, "inc": 0.0},
}

# Color Palette
ColorLight = pygame.Color(138, 138, 110)
ColorDark = pygame.Color(55, 50, 5)
ColorLabelLight = ColorDark
ColorLabelDark = ColorLight
ColorPanelBackground = pygame.Color(32, 32, 32)
ColorPanelText = pygame.Color(220, 220, 220)
ColorClockBackground = pygame.Color(24, 24, 24)
ColorClockActive = pygame.Color(255, 255, 255)
ColorClockInactive = pygame.Color(130, 130, 130)
ColorDropdownBackground = pygame.Color(45, 45, 45)
ColorDropdownBorder = pygame.Color(70, 70, 70)
ColorDropdownHover = pygame.Color(65, 65, 65)
ColorDropdownSelected = pygame.Color(80, 80, 80)
ColorStartButton = pygame.Color(46, 125, 50)
ColorStartButtonHover = pygame.Color(56, 142, 60)
ColorResetButton = pygame.Color(150, 50, 50)
ColorResetButtonHover = pygame.Color(175, 60, 60)
ColorSuiteButton = pygame.Color(45, 95, 155)
ColorSuiteButtonHover = pygame.Color(55, 115, 185)
ColorLeaderboardBg = pygame.Color(26, 26, 26)
ColorLeaderboardRowAlt = pygame.Color(34, 34, 34)
ColorWhitePiece = pygame.Color(245, 245, 245)
ColorBlackPiece = pygame.Color(18, 18, 18)

# Unicode Chess Piece Symbols
PieceUnicodeMap = {
    chess.PAWN: "♟",
    chess.KNIGHT: "♞",
    chess.BISHOP: "♝",
    chess.ROOK: "♜",
    chess.QUEEN: "♛",
    chess.KING: "♚",
}


def SetWindowDarkMode() -> None:
    try:
        windowHandle = pygame.display.get_wm_info().get("window")
        if windowHandle:
            renderingPolicy = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                windowHandle,
                DwmwaUseImmersiveDarkMode,
                ctypes.byref(renderingPolicy),
                ctypes.sizeof(renderingPolicy),
            )
    except Exception:
        pass


def LoadBotList() -> list[str]:
    botsDirectory = os.path.join(os.path.dirname(__file__), "bots")
    botList = ["Human"]

    if os.path.exists(botsDirectory) and os.path.isdir(botsDirectory):
        for entry in sorted(os.listdir(botsDirectory)):
            fullPath = os.path.join(botsDirectory, entry)
            if os.path.isfile(fullPath) and (
                entry.endswith(".py") or entry.endswith(".exe")
            ):
                botName = os.path.splitext(entry)[0]
                if botName not in botList:
                    botList.append(botName)

    return botList


def FormatClockTime(seconds: float) -> str:
    clamped = max(0.0, seconds)
    minutes = int(clamped // 60)
    remainingSeconds = clamped % 60
    if clamped < 10.0:
        return f"{minutes}:{remainingSeconds:04.1f}"
    return f"{minutes}:{int(remainingSeconds):02d}"


class EngineWorker:
    def __init__(self, botName: str) -> None:
        self.botName = botName
        self.engine: Optional[chess.engine.SimpleEngine] = None
        self.isSearching = False
        self.InitEngine()

    def GetCommand(self) -> Optional[list[str]]:
        botsDirectory = os.path.join(os.path.dirname(__file__), "bots")
        exePath = os.path.join(botsDirectory, f"{self.botName}.exe")
        pyPath = os.path.join(botsDirectory, f"{self.botName}.py")

        if os.path.isfile(exePath):
            return [exePath]
        elif os.path.isfile(pyPath):
            return [sys.executable, pyPath]
        return None

    def InitEngine(self) -> None:
        if self.botName == "Human":
            return

        command = self.GetCommand()
        if not command:
            print(f"Engine file not found for: {self.botName}")
            return

        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(command)
            print(f"Connected to UCI engine: {self.botName}")
        except Exception as error:
            print(f"Failed to launch UCI engine '{self.botName}': {error}")
            self.engine = None

    def RequestMoveAsync(
        self,
        board: chess.Board,
        searchLimit: chess.engine.Limit,
        gameId: int,
        onMoveComplete: Callable[[Optional[chess.Move], int], None],
    ) -> None:
        if not self.engine or self.isSearching:
            return

        self.isSearching = True
        boardCopy = board.copy()

        def SearchThread() -> None:
            bestMove = None
            try:
                searchResult = self.engine.play(boardCopy, searchLimit)
                bestMove = searchResult.move
            except Exception as error:
                print(f"Engine search error ({self.botName}): {error}")
            finally:
                self.isSearching = False
                onMoveComplete(bestMove, gameId)

        threading.Thread(target=SearchThread, daemon=True).start()

    def Quit(self) -> None:
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass
            self.engine = None


class DropdownMenu:
    def __init__(
        self,
        xPosition: int,
        yPosition: int,
        width: int,
        height: int,
        options: list[str],
        selectedIndex: int = 0,
    ) -> None:
        self.rect = pygame.Rect(xPosition, yPosition, width, height)
        self.options = options
        self.selectedIndex = selectedIndex
        self.isOpen = False

    def HandleEvent(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mousePosition = event.pos

            if self.isOpen:
                for optionIndex in range(len(self.options)):
                    optionRect = pygame.Rect(
                        self.rect.x,
                        self.rect.y + (optionIndex + 1) * self.rect.height,
                        self.rect.width,
                        self.rect.height,
                    )
                    if optionRect.collidepoint(mousePosition):
                        self.selectedIndex = optionIndex
                        self.isOpen = False
                        return True

                self.isOpen = False
                return False

            elif self.rect.collidepoint(mousePosition):
                self.isOpen = True
                return False

        return False

    def GetSelectedOption(self) -> str:
        if 0 <= self.selectedIndex < len(self.options):
            return self.options[self.selectedIndex]
        return self.options[0] if self.options else "Human"

    def SetSelectedOption(self, value: str) -> None:
        if value in self.options:
            self.selectedIndex = self.options.index(value)

    def SetOptions(self, newOptions: list[str]) -> None:
        current = self.GetSelectedOption()
        self.options = newOptions if newOptions else ["All Opponents"]
        if current in self.options:
            self.selectedIndex = self.options.index(current)
        else:
            self.selectedIndex = 0

    def Draw(
        self, surface: pygame.Surface, font: pygame.font.Font, mousePosition: tuple[int, int]
    ) -> None:
        isHovered = self.rect.collidepoint(mousePosition)
        baseColor = ColorDropdownHover if isHovered else ColorDropdownBackground
        pygame.draw.rect(surface, baseColor, self.rect, border_radius=4)
        pygame.draw.rect(surface, ColorDropdownBorder, self.rect, width=1, border_radius=4)

        currentText = self.GetSelectedOption()
        textSurface = font.render(currentText, True, ColorPanelText)
        textRect = textSurface.get_rect(
            midleft=(self.rect.left + 10, self.rect.centery)
        )
        surface.blit(textSurface, textRect)

        arrow = "▲" if self.isOpen else "▼"
        arrowSurface = font.render(arrow, True, ColorPanelText)
        arrowRect = arrowSurface.get_rect(
            midright=(self.rect.right - 10, self.rect.centery)
        )
        surface.blit(arrowSurface, arrowRect)

    def DrawExpandedList(
        self, surface: pygame.Surface, font: pygame.font.Font, mousePosition: tuple[int, int]
    ) -> None:
        if not self.isOpen:
            return

        for optionIndex, optionText in enumerate(self.options):
            optionRect = pygame.Rect(
                self.rect.x,
                self.rect.y + (optionIndex + 1) * self.rect.height,
                self.rect.width,
                self.rect.height,
            )
            isHovered = optionRect.collidepoint(mousePosition)
            isSelected = optionIndex == self.selectedIndex

            optionColor = (
                ColorDropdownSelected
                if isSelected
                else (ColorDropdownHover if isHovered else ColorDropdownBackground)
            )

            pygame.draw.rect(surface, optionColor, optionRect)
            pygame.draw.rect(surface, ColorDropdownBorder, optionRect, width=1)

            textSurface = font.render(optionText, True, ColorPanelText)
            textRect = textSurface.get_rect(
                midleft=(optionRect.left + 10, optionRect.centery)
            )
            surface.blit(textSurface, textRect)


def DrawBoard(surface: pygame.Surface, font: pygame.font.Font) -> None:
    files = "abcdefgh"
    ranks = "87654321"

    for rankIndex in range(BoardSize):
        for fileIndex in range(BoardSize):
            isLightSquare = (rankIndex + fileIndex) % 2 == 0
            squareColor = ColorLight if isLightSquare else ColorDark

            squareRect = pygame.Rect(
                fileIndex * SquareSize,
                rankIndex * SquareSize,
                SquareSize,
                SquareSize,
            )
            pygame.draw.rect(surface, squareColor, squareRect)

            if rankIndex == BoardSize - 1:
                labelColor = ColorLabelLight if isLightSquare else ColorLabelDark
                textSurface = font.render(files[fileIndex], True, labelColor)
                textRect = textSurface.get_rect(
                    bottomright=(squareRect.right - 4, squareRect.bottom - 2)
                )
                surface.blit(textSurface, textRect)

            if fileIndex == 0:
                labelColor = ColorLabelLight if isLightSquare else ColorLabelDark
                textSurface = font.render(ranks[rankIndex], True, labelColor)
                textRect = textSurface.get_rect(
                    topleft=(squareRect.left + 4, squareRect.top + 2)
                )
                surface.blit(textSurface, textRect)


def DrawPieces(surface: pygame.Surface, board: chess.Board, pieceFont: pygame.font.Font) -> None:
    for squareIndex in chess.SQUARES:
        piece = board.piece_at(squareIndex)
        if piece is None:
            continue

        fileIndex = chess.square_file(squareIndex)
        rankIndex = 7 - chess.square_rank(squareIndex)

        symbol = PieceUnicodeMap.get(piece.piece_type, "")
        color = ColorWhitePiece if piece.color == chess.WHITE else ColorBlackPiece

        pieceSurface = pieceFont.render(symbol, True, color)
        pieceRect = pieceSurface.get_rect(
            center=(
                fileIndex * SquareSize + SquareSize // 2,
                rankIndex * SquareSize + SquareSize // 2,
            )
        )
        surface.blit(pieceSurface, pieceRect)


def DrawLeaderboardView(
    surface: pygame.Surface,
    titleFont: pygame.font.Font,
    headerFont: pygame.font.Font,
    rowFont: pygame.font.Font,
    opponentDropdown: DropdownMenu,
    leaderboardData: list[dict],
    scrollOffset: int,
    mousePosition: tuple[int, int],
) -> None:
    areaRect = pygame.Rect(0, 0, BoardPixelSize, BoardPixelSize)
    pygame.draw.rect(surface, ColorLeaderboardBg, areaRect)

    selectedFilter = opponentDropdown.GetSelectedOption()
    isPerftMode = selectedFilter == "Perft"

    # Header Title & Opponent Filter Dropdown
    titleSurface = titleFont.render("Leaderboard", True, ColorClockActive)
    surface.blit(titleSurface, (20, 22))

    filterLabel = headerFont.render("Opponent:", True, ColorPanelText)
    surface.blit(filterLabel, (335, 28))
    opponentDropdown.Draw(surface, headerFont, mousePosition)

    if isPerftMode:
        columns = [
            ("#", 24),
            ("Bot", 64),
            ("Runs", 240),
            ("Depth", 305),
            ("Nodes", 375),
            ("Time (s)", 480),
            ("Best NPS", 555),
        ]
    else:
        columns = [
            ("#", 24),
            ("Bot", 64),
            ("Games", 260),
            ("W", 335),
            ("D", 390),
            ("L", 445),
            ("Score", 500),
            ("Win %", 565),
        ]

    headerY = 82
    headerRect = pygame.Rect(16, headerY - 6, BoardPixelSize - 32, 32)
    pygame.draw.rect(surface, ColorDropdownBackground, headerRect, border_radius=4)
    pygame.draw.rect(surface, ColorDropdownBorder, headerRect, width=1, border_radius=4)

    for colLabel, colX in columns:
        colSurf = headerFont.render(colLabel, True, ColorClockActive)
        surface.blit(colSurf, (colX, headerY))

    if not leaderboardData:
        emptyMsg = (
            "No perft benchmarks recorded yet."
            if isPerftMode
            else f"No matches recorded against '{selectedFilter}' yet."
        )
        emptySurf = rowFont.render(emptyMsg, True, ColorClockInactive)
        emptyRect = emptySurf.get_rect(center=(BoardPixelSize // 2, BoardPixelSize // 2))
        surface.blit(emptySurf, emptyRect)
    else:
        rowHeight = 34
        startY = headerY + 34
        maxVisibleRows = (BoardPixelSize - startY - 16) // rowHeight
        visibleSlice = leaderboardData[scrollOffset : scrollOffset + maxVisibleRows]

        for idx, entry in enumerate(visibleSlice):
            rank = scrollOffset + idx + 1
            rowY = startY + idx * rowHeight
            rowRect = pygame.Rect(16, rowY, BoardPixelSize - 32, rowHeight - 2)

            if idx % 2 == 1:
                pygame.draw.rect(surface, ColorLeaderboardRowAlt, rowRect, border_radius=3)

            if isPerftMode:
                values = [
                    (str(rank), 24),
                    (entry["botName"][:18], 64),
                    (str(entry["runs"]), 240),
                    (str(entry["maxDepth"]), 305),
                    (f"{entry['nodes']:,}", 375),
                    (f"{entry['timeSeconds']:.3f}", 480),
                    (f"{entry['bestPerftNps']:,}", 555),
                ]
            else:
                values = [
                    (str(rank), 24),
                    (entry["botName"][:20], 64),
                    (str(entry["games"]), 260),
                    (str(entry["wins"]), 335),
                    (str(entry["draws"]), 390),
                    (str(entry["losses"]), 445),
                    (f"{entry['score']:g}", 500),
                    (f"{entry['winRate']:.1f}%", 565),
                ]

            for valText, valX in values:
                valSurf = rowFont.render(valText, True, ColorPanelText)
                surface.blit(valSurf, (valX, rowY + 7))

    # Draw opponent dropdown list on top of the table rows if open
    if opponentDropdown.isOpen:
        opponentDropdown.DrawExpandedList(surface, headerFont, mousePosition)


def DrawClockBox(
    surface: pygame.Surface,
    clockFont: pygame.font.Font,
    yPosition: int,
    timeText: str,
    isActive: bool,
) -> None:
    boxRect = pygame.Rect(BoardPixelSize + 20, yPosition, ControlPanelWidth - 40, 44)
    pygame.draw.rect(surface, ColorClockBackground, boxRect, border_radius=6)
    pygame.draw.rect(surface, ColorDropdownBorder, boxRect, width=1, border_radius=6)

    textColor = ColorClockActive if isActive else ColorClockInactive
    textSurface = clockFont.render(timeText, True, textColor)
    textRect = textSurface.get_rect(center=boxRect.center)
    surface.blit(textSurface, textRect)


def DrawButton(
    surface: pygame.Surface,
    font: pygame.font.Font,
    buttonRect: pygame.Rect,
    label: str,
    baseColor: pygame.Color,
    hoverColor: pygame.Color,
    mousePosition: tuple[int, int],
) -> None:
    isHovered = buttonRect.collidepoint(mousePosition)
    bgColor = hoverColor if isHovered else baseColor

    pygame.draw.rect(surface, bgColor, buttonRect, border_radius=5)
    pygame.draw.rect(surface, ColorDropdownBorder, buttonRect, width=1, border_radius=5)

    textSurface = font.render(label, True, ColorClockActive)
    textRect = textSurface.get_rect(center=buttonRect.center)
    surface.blit(textSurface, textRect)


def DrawControlPanel(
    surface: pygame.Surface,
    headerFont: pygame.font.Font,
    buttonFont: pygame.font.Font,
    clockFont: pygame.font.Font,
    whiteDropdown: DropdownMenu,
    blackDropdown: DropdownMenu,
    timeDropdown: DropdownMenu,
    actionButtonRect: pygame.Rect,
    suiteButtonRect: pygame.Rect,
    leaderboardButtonRect: pygame.Rect,
    showLeaderboard: bool,
    gameStarted: bool,
    suiteActive: bool,
    statusText: str,
    suiteStatusText: str,
    whiteTimeText: str,
    blackTimeText: str,
    currentTurn: chess.Color,
    isGameActive: bool,
    mousePosition: tuple[int, int],
) -> None:
    panelRect = pygame.Rect(
        BoardPixelSize, 0, ControlPanelWidth, WindowHeight
    )
    pygame.draw.rect(surface, ColorPanelBackground, panelRect)

    # White Controls
    whiteLabel = headerFont.render("White Player", True, ColorPanelText)
    surface.blit(whiteLabel, (BoardPixelSize + 20, 20))
    whiteDropdown.Draw(surface, headerFont, mousePosition)

    # Black Controls
    blackLabel = headerFont.render("Black Player", True, ColorPanelText)
    surface.blit(blackLabel, (BoardPixelSize + 20, 100))
    blackDropdown.Draw(surface, headerFont, mousePosition)

    # Time Control Dropdown
    timeLabel = headerFont.render("Time Control", True, ColorPanelText)
    surface.blit(timeLabel, (BoardPixelSize + 20, 180))
    timeDropdown.Draw(surface, headerFont, mousePosition)

    # Start / Reset Button
    if not gameStarted and not suiteActive:
        DrawButton(
            surface,
            buttonFont,
            actionButtonRect,
            "Start Game",
            ColorStartButton,
            ColorStartButtonHover,
            mousePosition,
        )
    else:
        DrawButton(
            surface,
            buttonFont,
            actionButtonRect,
            "Reset / Stop",
            ColorResetButton,
            ColorResetButtonHover,
            mousePosition,
        )

    # Run FEN Suite Button
    DrawButton(
        surface,
        buttonFont,
        suiteButtonRect,
        "Run FEN Suite",
        ColorSuiteButton,
        ColorSuiteButtonHover,
        mousePosition,
    )

    # Leaderboard Toggle Button
    DrawButton(
        surface,
        buttonFont,
        leaderboardButtonRect,
        "Back to Board" if showLeaderboard else "Leaderboard",
        ColorDropdownSelected if showLeaderboard else ColorDropdownBackground,
        ColorDropdownHover,
        mousePosition,
    )

    # Game Status Label
    statusSurface = headerFont.render(statusText, True, ColorPanelText)
    statusRect = statusSurface.get_rect(
        center=(BoardPixelSize + ControlPanelWidth // 2, leaderboardButtonRect.bottom + 20)
    )
    surface.blit(statusSurface, statusRect)

    if suiteStatusText:
        suiteSurface = headerFont.render(suiteStatusText, True, ColorClockActive)
        suiteRect = suiteSurface.get_rect(
            center=(BoardPixelSize + ControlPanelWidth // 2, leaderboardButtonRect.bottom + 42)
        )
        surface.blit(suiteSurface, suiteRect)

    # Clocks at bottom of panel
    blackClockLabel = headerFont.render("Black Clock", True, ColorPanelText)
    surface.blit(blackClockLabel, (BoardPixelSize + 20, WindowHeight - 165))
    DrawClockBox(
        surface,
        clockFont,
        WindowHeight - 140,
        blackTimeText,
        isGameActive and currentTurn == chess.BLACK,
    )

    whiteClockLabel = headerFont.render("White Clock", True, ColorPanelText)
    surface.blit(whiteClockLabel, (BoardPixelSize + 20, WindowHeight - 85))
    DrawClockBox(
        surface,
        clockFont,
        WindowHeight - 60,
        whiteTimeText,
        isGameActive and currentTurn == chess.WHITE,
    )

    # Render whichever dropdown is expanded on top of all other UI elements
    for dropdown in (whiteDropdown, blackDropdown, timeDropdown):
        if dropdown.isOpen:
            dropdown.DrawExpandedList(surface, headerFont, mousePosition)


def PostEngineMoveEvent(move: Optional[chess.Move], gameId: int) -> None:
    event = pygame.event.Event(EngineMoveEventType, {"move": move, "gameId": gameId})
    pygame.event.post(event)


def Main() -> None:
    pygame.init()
    gameScreen = pygame.display.set_mode((WindowWidth, WindowHeight))
    pygame.display.set_caption("Chess")

    SetWindowDarkMode()

    gameClock = pygame.time.Clock()
    labelFont = pygame.font.SysFont("Segoe UI", 14, bold=True)
    uiFont = pygame.font.SysFont("Segoe UI", 14)
    buttonFont = pygame.font.SysFont("Segoe UI", 15, bold=True)
    titleFont = pygame.font.SysFont("Segoe UI", 22, bold=True)
    tableHeaderFont = pygame.font.SysFont("Segoe UI", 14, bold=True)
    tableRowFont = pygame.font.SysFont("Consolas", 14)
    clockFont = pygame.font.SysFont("Consolas", 22, bold=True)
    pieceFont = pygame.font.SysFont("Segoe UI Symbol", 56)

    chessBoard = chess.Board()

    botOptions = LoadBotList()
    timeOptions = list(TimeControlPresets.keys())
    dropdownWidth = ControlPanelWidth - 40
    dropdownHeight = 34

    whiteDropdown = DropdownMenu(
        BoardPixelSize + 20, 44, dropdownWidth, dropdownHeight, botOptions
    )
    blackDropdown = DropdownMenu(
        BoardPixelSize + 20, 124, dropdownWidth, dropdownHeight, botOptions
    )
    timeDropdown = DropdownMenu(
        BoardPixelSize + 20, 204, dropdownWidth, dropdownHeight, timeOptions, selectedIndex=1
    )
    opponentDropdown = DropdownMenu(
        415, 20, 205, 34, GetAvailableOpponents()
    )
    actionButtonRect = pygame.Rect(
        BoardPixelSize + 20, 256, dropdownWidth, 34
    )
    suiteButtonRect = pygame.Rect(
        BoardPixelSize + 20, 298, dropdownWidth, 34
    )
    leaderboardButtonRect = pygame.Rect(
        BoardPixelSize + 20, 340, dropdownWidth, 34
    )

    whiteEngine: Optional[EngineWorker] = None
    blackEngine: Optional[EngineWorker] = None
    suiteRunner = FenSuiteRunner()

    gameStarted = False
    gameId = 0
    whiteTimeRemaining = 0.0
    blackTimeRemaining = 0.0
    flaggedColor: Optional[chess.Color] = None
    gameStartFen = chess.STARTING_FEN
    resultRecorded = False
    customStatusOverride: Optional[str] = None
    showLeaderboard = False
    leaderboardData: list[dict] = []
    leaderboardScroll = 0
    lastFrameTimestamp = time.perf_counter()

    def RefreshLeaderboard() -> None:
        nonlocal leaderboardData, leaderboardScroll
        opponentDropdown.SetOptions(GetAvailableOpponents())
        leaderboardData = GetLeaderboardSummary(opponentDropdown.GetSelectedOption())
        maxScroll = max(0, len(leaderboardData) - 14)
        leaderboardScroll = min(leaderboardScroll, maxScroll)

    def ResetClocks() -> None:
        nonlocal whiteTimeRemaining, blackTimeRemaining, flaggedColor, lastFrameTimestamp
        preset = TimeControlPresets[timeDropdown.GetSelectedOption()]
        if preset["mode"] == "clock":
            whiteTimeRemaining = preset["base"]
            blackTimeRemaining = preset["base"]
        else:
            whiteTimeRemaining = preset["time"]
            blackTimeRemaining = preset["time"]
        flaggedColor = None
        lastFrameTimestamp = time.perf_counter()

    def RefreshEngines() -> None:
        nonlocal whiteEngine, blackEngine
        whiteSelection = whiteDropdown.GetSelectedOption()
        blackSelection = blackDropdown.GetSelectedOption()

        if not whiteEngine or whiteEngine.botName != whiteSelection:
            if whiteEngine:
                whiteEngine.Quit()
            whiteEngine = EngineWorker(whiteSelection) if whiteSelection != "Human" else None

        if not blackEngine or blackEngine.botName != blackSelection:
            if blackEngine:
                blackEngine.Quit()
            blackEngine = EngineWorker(blackSelection) if blackSelection != "Human" else None

    def ResetGameState() -> None:
        nonlocal gameStarted, gameId, gameStartFen, resultRecorded, customStatusOverride
        suiteRunner.Stop()
        gameId += 1
        gameStarted = False
        resultRecorded = False
        customStatusOverride = None
        chessBoard.reset()
        gameStartFen = chessBoard.fen()
        ResetClocks()

    def StartGameState(startFen: str = chess.STARTING_FEN) -> None:
        nonlocal gameStarted, gameId, gameStartFen, resultRecorded, customStatusOverride
        gameId += 1
        resultRecorded = False
        customStatusOverride = None
        chessBoard.set_fen(startFen)
        gameStartFen = chessBoard.fen()
        ResetClocks()
        gameStarted = True

    def LaunchNextSuiteGame() -> bool:
        nextMatch = suiteRunner.PopNextMatch()
        if nextMatch is None:
            return False
        fen, wBot, bBot = nextMatch
        whiteDropdown.SetSelectedOption(wBot)
        blackDropdown.SetSelectedOption(bBot)
        RefreshEngines()
        StartGameState(fen)
        return True

    def BuildSearchLimit() -> chess.engine.Limit:
        preset = TimeControlPresets[timeDropdown.GetSelectedOption()]
        if preset["mode"] == "movetime":
            return chess.engine.Limit(time=preset["time"])
        return chess.engine.Limit(
            white_clock=max(0.01, whiteTimeRemaining),
            black_clock=max(0.01, blackTimeRemaining),
            white_inc=preset["inc"],
            black_inc=preset["inc"],
        )

    def GetStatusText(isGameOver: bool) -> str:
        if customStatusOverride:
            return customStatusOverride
        if not gameStarted:
            return "Ready to Start"
        if flaggedColor == chess.WHITE:
            return "Black Wins on Time"
        if flaggedColor == chess.BLACK:
            return "White Wins on Time"
        if isGameOver:
            outcome = chessBoard.outcome()
            if outcome and outcome.winner == chess.WHITE:
                return "White Wins"
            if outcome and outcome.winner == chess.BLACK:
                return "Black Wins"
            return "Draw"
        return "White to Move" if chessBoard.turn == chess.WHITE else "Black to Move"

    ResetClocks()

    isGameRunning = True
    while isGameRunning:
        now = time.perf_counter()
        deltaSeconds = now - lastFrameTimestamp
        lastFrameTimestamp = now

        mousePosition = pygame.mouse.get_pos()
        currentPreset = TimeControlPresets[timeDropdown.GetSelectedOption()]
        isGameOver = chessBoard.is_game_over() or flaggedColor is not None
        isGameActive = gameStarted and not isGameOver

        for currentEvent in pygame.event.get():
            if currentEvent.type == pygame.QUIT:
                isGameRunning = False
            elif currentEvent.type == pygame.KEYDOWN and currentEvent.key == pygame.K_ESCAPE:
                if showLeaderboard:
                    showLeaderboard = False
                else:
                    isGameRunning = False
            elif currentEvent.type == pygame.MOUSEWHEEL and showLeaderboard:
                maxScroll = max(0, len(leaderboardData) - 14)
                leaderboardScroll = max(0, min(maxScroll, leaderboardScroll - currentEvent.y))

            activeDropdowns = [whiteDropdown, blackDropdown, timeDropdown]
            if showLeaderboard:
                activeDropdowns.append(opponentDropdown)

            openDropdown = next((d for d in activeDropdowns if d.isOpen), None)

            if openDropdown is not None:
                if openDropdown.HandleEvent(currentEvent):
                    if openDropdown is opponentDropdown:
                        leaderboardScroll = 0
                        RefreshLeaderboard()
                    elif openDropdown is timeDropdown:
                        ResetGameState()
                    else:
                        ResetGameState()
                        RefreshEngines()
            else:
                if showLeaderboard and opponentDropdown.HandleEvent(currentEvent):
                    leaderboardScroll = 0
                    RefreshLeaderboard()
                elif whiteDropdown.HandleEvent(currentEvent):
                    ResetGameState()
                    RefreshEngines()
                elif blackDropdown.HandleEvent(currentEvent):
                    ResetGameState()
                    RefreshEngines()
                elif timeDropdown.HandleEvent(currentEvent):
                    ResetGameState()
                elif (
                    currentEvent.type == pygame.MOUSEBUTTONDOWN
                    and currentEvent.button == 1
                    and actionButtonRect.collidepoint(currentEvent.pos)
                ):
                    showLeaderboard = False
                    if not gameStarted and not suiteRunner.isActive:
                        StartGameState()
                    else:
                        ResetGameState()
                elif (
                    currentEvent.type == pygame.MOUSEBUTTONDOWN
                    and currentEvent.button == 1
                    and suiteButtonRect.collidepoint(currentEvent.pos)
                ):
                    wBot = whiteDropdown.GetSelectedOption()
                    bBot = blackDropdown.GetSelectedOption()
                    if wBot == "Human" or bBot == "Human":
                        customStatusOverride = "Select 2 Bots First"
                    else:
                        showLeaderboard = False
                        ResetGameState()
                        selectedFile = SelectFenFile()
                        lastFrameTimestamp = time.perf_counter()
                        if selectedFile:
                            fenList = LoadFenList(selectedFile)
                            if fenList and suiteRunner.Start(fenList, wBot, bBot):
                                LaunchNextSuiteGame()
                            else:
                                customStatusOverride = "No Valid FENs Found"
                elif (
                    currentEvent.type == pygame.MOUSEBUTTONDOWN
                    and currentEvent.button == 1
                    and leaderboardButtonRect.collidepoint(currentEvent.pos)
                ):
                    showLeaderboard = not showLeaderboard
                    if showLeaderboard:
                        leaderboardScroll = 0
                        RefreshLeaderboard()

            if (
                currentEvent.type == EngineMoveEventType
                and isGameActive
                and getattr(currentEvent, "gameId", None) == gameId
            ):
                engineMove = currentEvent.move
                if engineMove and engineMove in chessBoard.legal_moves:
                    moverColor = chessBoard.turn
                    chessBoard.push(engineMove)
                    if currentPreset["mode"] == "clock":
                        if moverColor == chess.WHITE:
                            whiteTimeRemaining += currentPreset["inc"]
                        else:
                            blackTimeRemaining += currentPreset["inc"]
                    print(f"Executed Engine Move: {engineMove.uci()}")

        # Update active clock only while game is actively running
        if isGameActive and currentPreset["mode"] == "clock":
            if chessBoard.turn == chess.WHITE:
                whiteTimeRemaining -= deltaSeconds
                if whiteTimeRemaining <= 0.0:
                    whiteTimeRemaining = 0.0
                    flaggedColor = chess.WHITE
                    print("White flagged on time!")
            else:
                blackTimeRemaining -= deltaSeconds
                if blackTimeRemaining <= 0.0:
                    blackTimeRemaining = 0.0
                    flaggedColor = chess.BLACK
                    print("Black flagged on time!")

        isGameOver = chessBoard.is_game_over() or flaggedColor is not None
        isGameActive = gameStarted and not isGameOver

        # Record match outcome once when the game ends
        if gameStarted and isGameOver and not resultRecorded:
            if flaggedColor == chess.WHITE:
                winnerColor = chess.BLACK
                endReason = "time"
            elif flaggedColor == chess.BLACK:
                winnerColor = chess.WHITE
                endReason = "time"
            else:
                outcome = chessBoard.outcome()
                winnerColor = outcome.winner if outcome else None
                endReason = outcome.termination.name.lower() if outcome else "unknown"

            RecordMatchResult(
                whiteBot=whiteDropdown.GetSelectedOption(),
                blackBot=blackDropdown.GetSelectedOption(),
                startFen=gameStartFen,
                winner=winnerColor,
                reason=endReason,
                timeControl=timeDropdown.GetSelectedOption(),
                plyCount=chessBoard.ply(),
            )
            resultRecorded = True

            if showLeaderboard:
                RefreshLeaderboard()

            # Advance to next game if running a FEN suite
            if suiteRunner.isActive:
                if not LaunchNextSuiteGame():
                    gameStarted = False
                    customStatusOverride = "Suite Complete!"

        # Request bot move only while game is actively running
        if isGameActive:
            if chessBoard.turn == chess.WHITE and whiteEngine and not whiteEngine.isSearching:
                whiteEngine.RequestMoveAsync(
                    chessBoard, BuildSearchLimit(), gameId, PostEngineMoveEvent
                )
            elif chessBoard.turn == chess.BLACK and blackEngine and not blackEngine.isSearching:
                blackEngine.RequestMoveAsync(
                    chessBoard, BuildSearchLimit(), gameId, PostEngineMoveEvent
                )

        if currentPreset["mode"] == "clock":
            whiteClockDisplay = FormatClockTime(whiteTimeRemaining)
            blackClockDisplay = FormatClockTime(blackTimeRemaining)
        else:
            fixedText = f"{currentPreset['time']:g}s / move"
            whiteClockDisplay = fixedText
            blackClockDisplay = fixedText

        if showLeaderboard:
            DrawLeaderboardView(
                gameScreen,
                titleFont,
                tableHeaderFont,
                tableRowFont,
                opponentDropdown,
                leaderboardData,
                leaderboardScroll,
                mousePosition,
            )
        else:
            DrawBoard(gameScreen, labelFont)
            DrawPieces(gameScreen, chessBoard, pieceFont)

        DrawControlPanel(
            gameScreen,
            uiFont,
            buttonFont,
            clockFont,
            whiteDropdown,
            blackDropdown,
            timeDropdown,
            actionButtonRect,
            suiteButtonRect,
            leaderboardButtonRect,
            showLeaderboard,
            gameStarted,
            suiteRunner.isActive,
            GetStatusText(isGameOver),
            suiteRunner.GetProgressText(),
            whiteClockDisplay,
            blackClockDisplay,
            chessBoard.turn,
            isGameActive,
            mousePosition,
        )

        pygame.display.flip()
        gameClock.tick(FramesPerSecond)

    if whiteEngine:
        whiteEngine.Quit()
    if blackEngine:
        blackEngine.Quit()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    Main()