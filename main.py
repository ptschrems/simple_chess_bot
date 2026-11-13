import os
import sys
import time
import ctypes
import threading
from typing import Optional, Callable
import pygame
import chess
import chess.engine
from results import RecordMatchResult

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


def DrawActionButton(
    surface: pygame.Surface,
    font: pygame.font.Font,
    buttonRect: pygame.Rect,
    gameStarted: bool,
    mousePosition: tuple[int, int],
) -> None:
    isHovered = buttonRect.collidepoint(mousePosition)
    if not gameStarted:
        bgColor = ColorStartButtonHover if isHovered else ColorStartButton
        label = "Start Game"
    else:
        bgColor = ColorResetButtonHover if isHovered else ColorResetButton
        label = "Reset Game"

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
    gameStarted: bool,
    statusText: str,
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
    DrawActionButton(surface, buttonFont, actionButtonRect, gameStarted, mousePosition)

    # Game Status Label
    statusSurface = headerFont.render(statusText, True, ColorPanelText)
    statusRect = statusSurface.get_rect(
        center=(BoardPixelSize + ControlPanelWidth // 2, actionButtonRect.bottom + 24)
    )
    surface.blit(statusSurface, statusRect)

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
    actionButtonRect = pygame.Rect(
        BoardPixelSize + 20, 260, dropdownWidth, 38
    )

    whiteEngine: Optional[EngineWorker] = None
    blackEngine: Optional[EngineWorker] = None

    gameStarted = False
    gameId = 0
    whiteTimeRemaining = 0.0
    blackTimeRemaining = 0.0
    flaggedColor: Optional[chess.Color] = None
    gameStartFen = chess.STARTING_FEN
    resultRecorded = False
    lastFrameTimestamp = time.perf_counter()

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

    def ResetGameState() -> None:
        nonlocal gameStarted, gameId, gameStartFen, resultRecorded
        gameId += 1
        gameStarted = False
        resultRecorded = False
        chessBoard.reset()
        gameStartFen = chessBoard.fen()
        ResetClocks()

    def StartGameState() -> None:
        nonlocal gameStarted, gameId, gameStartFen, resultRecorded
        gameId += 1
        resultRecorded = False
        chessBoard.reset()
        gameStartFen = chessBoard.fen()
        ResetClocks()
        gameStarted = True

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

    def RefreshEngines() -> None:
        nonlocal whiteEngine, blackEngine
        if whiteEngine:
            whiteEngine.Quit()
        if blackEngine:
            blackEngine.Quit()

        whiteSelection = whiteDropdown.GetSelectedOption()
        blackSelection = blackDropdown.GetSelectedOption()

        whiteEngine = EngineWorker(whiteSelection) if whiteSelection != "Human" else None
        blackEngine = EngineWorker(blackSelection) if blackSelection != "Human" else None

    def GetStatusText(isGameOver: bool) -> str:
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
                isGameRunning = False

            # Route clicks to whichever dropdown is open first
            openDropdown = next(
                (d for d in (whiteDropdown, blackDropdown, timeDropdown) if d.isOpen),
                None,
            )

            if openDropdown is not None:
                if openDropdown.HandleEvent(currentEvent):
                    if openDropdown is timeDropdown:
                        ResetGameState()
                    else:
                        ResetGameState()
                        RefreshEngines()
            else:
                if whiteDropdown.HandleEvent(currentEvent):
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
                    if not gameStarted:
                        StartGameState()
                    else:
                        ResetGameState()

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
            gameStarted,
            GetStatusText(isGameOver),
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