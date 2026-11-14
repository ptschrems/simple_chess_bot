import os
import sys
import time
import ctypes
import threading
from typing import Optional, Callable
import pygame
import chess
import chess.engine

# Constants
WindowWidth = 920
WindowHeight = 640
ControlPanelWidth = 240
TableAreaWidth = WindowWidth - ControlPanelWidth
FramesPerSecond = 60

# Custom Pygame events for thread-safe benchmark updates
BenchStepEventType = pygame.USEREVENT + 1
BenchDoneEventType = pygame.USEREVENT + 2

# DWM Attribute Constant for Windows 10/11 Dark Title Bar
DwmwaUseImmersiveDarkMode = 20

# Color Palette (matching main.py)
ColorBackground = pygame.Color(26, 26, 26)
ColorRowAlt = pygame.Color(34, 34, 34)
ColorPanelBackground = pygame.Color(32, 32, 32)
ColorPanelText = pygame.Color(220, 220, 220)
ColorTextActive = pygame.Color(255, 255, 255)
ColorTextMuted = pygame.Color(130, 130, 130)
ColorDropdownBackground = pygame.Color(45, 45, 45)
ColorDropdownBorder = pygame.Color(70, 70, 70)
ColorDropdownHover = pygame.Color(65, 65, 65)
ColorDropdownSelected = pygame.Color(80, 80, 80)
ColorStartButton = pygame.Color(46, 125, 50)
ColorStartButtonHover = pygame.Color(56, 142, 60)
ColorStopButton = pygame.Color(150, 50, 50)
ColorStopButtonHover = pygame.Color(175, 60, 60)
ColorClearButton = pygame.Color(45, 95, 155)
ColorClearButtonHover = pygame.Color(55, 115, 185)
ColorProgressFill = pygame.Color(46, 125, 50)

DepthOptions = ["Depth 4", "Depth 5", "Depth 6", "Depth 7", "Depth 8", "Depth 9", "Depth 10"]

BenchPositions: list[tuple[str, str]] = [
    ("Startpos", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("Rook Endgame", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"),
    ("Promotions & Pins", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"),
    ("Sharp Tactical", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"),
    ("Quiet Middlegame", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"),
    ("King Attack", "2rr3k/pp3pp1/1nnqbN1p/3pN3/2pP4/2P3Q1/PPB4P/R4RK1 w - - 0 1"),
    ("Closed Center", "4rrk1/pp1n3p/3q2pQ/2p1pb2/2PP4/2P3N1/P2B2PP/4RRK1 b - - 0 1"),
    ("Ruy Lopez", "r2q1rk1/1b2bppp/p2p1n2/1ppPp3/4P3/2P2N1P/PPB2PP1/RNBQR1K1 w - - 0 11"),
    ("Q+R Middlegame", "3r2k1/p1rq1pp1/1p2pn1p/8/2PP4/P3P1P1/1B1Q1PBP/3R2K1 w - - 0 20"),
    ("Pawn Endgame", "8/5pk1/6p1/3P3p/P4P2/6P1/5K2/8 w - - 0 40"),
    ("Opposite Bishops", "8/8/4kpp1/3p1b2/p6P/2B5/6P1/6K1 b - - 0 47"),
]


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
    botList: list[str] = []

    if os.path.exists(botsDirectory) and os.path.isdir(botsDirectory):
        for entry in sorted(os.listdir(botsDirectory)):
            fullPath = os.path.join(botsDirectory, entry)
            if os.path.isfile(fullPath) and (
                entry.endswith(".py") or entry.endswith(".exe")
            ):
                botName = os.path.splitext(entry)[0]
                if botName not in botList:
                    botList.append(botName)

    return botList if botList else ["No Bots Found"]


def GetBotCommand(botName: str) -> Optional[list[str]]:
    botsDirectory = os.path.join(os.path.dirname(__file__), "bots")
    exePath = os.path.join(botsDirectory, f"{botName}.exe")
    pyPath = os.path.join(botsDirectory, f"{botName}.py")

    if os.path.isfile(exePath):
        return [exePath]
    elif os.path.isfile(pyPath):
        return [sys.executable, pyPath]
    return None


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
        return self.options[0] if self.options else ""

    def Draw(
        self, surface: pygame.Surface, font: pygame.font.Font, mousePosition: tuple[int, int]
    ) -> None:
        isHovered = self.rect.collidepoint(mousePosition)
        baseColor = ColorDropdownHover if isHovered else ColorDropdownBackground
        pygame.draw.rect(surface, baseColor, self.rect, border_radius=4)
        pygame.draw.rect(surface, ColorDropdownBorder, self.rect, width=1, border_radius=4)

        currentText = self.GetSelectedOption()
        textSurface = font.render(currentText, True, ColorPanelText)
        textRect = textSurface.get_rect(midleft=(self.rect.left + 10, self.rect.centery))
        surface.blit(textSurface, textRect)

        arrow = "▲" if self.isOpen else "▼"
        arrowSurface = font.render(arrow, True, ColorPanelText)
        arrowRect = arrowSurface.get_rect(midright=(self.rect.right - 10, self.rect.centery))
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
            textRect = textSurface.get_rect(midleft=(optionRect.left + 10, optionRect.centery))
            surface.blit(textSurface, textRect)


class BenchmarkRunner:
    def __init__(self) -> None:
        self.isRunning = False
        self.stopRequested = False
        self.runId = 0

    def Start(
        self,
        botName: str,
        targetDepth: int,
        onStep: Callable[[int, str, str, int, float, int], None],
        onDone: Callable[[int, str, int, int, float, bool], None],
    ) -> None:
        if self.isRunning:
            return

        command = GetBotCommand(botName)
        if not command:
            return

        self.runId += 1
        activeRunId = self.runId
        self.isRunning = True
        self.stopRequested = False

        def Worker() -> None:
            engine: Optional[chess.engine.SimpleEngine] = None
            totalNodes = 0
            totalSeconds = 0.0
            cancelled = False

            try:
                engine = chess.engine.SimpleEngine.popen_uci(command)
                searchLimit = chess.engine.Limit(depth=targetDepth)

                # Warmup pass on Kiwipete so CPU boost clocks and OS scheduling settle
                warmupBoard = chess.Board(BenchPositions[1][1])
                engine.play(warmupBoard, chess.engine.Limit(depth=max(1, targetDepth - 1)))

                for label, fen in BenchPositions:
                    if self.stopRequested:
                        cancelled = True
                        break

                    board = chess.Board(fen)
                    startTime = time.perf_counter()
                    result = engine.play(board, searchLimit, info=chess.engine.INFO_ALL)
                    elapsedSeconds = time.perf_counter() - startTime

                    nodes = result.info.get("nodes", 0)
                    moveUci = result.move.uci() if result.move else "-"

                    totalNodes += nodes
                    totalSeconds += elapsedSeconds
                    onStep(activeRunId, label, moveUci, nodes, elapsedSeconds, len(BenchPositions))

            except Exception as error:
                print(f"Benchmark error ({botName}): {error}")
                cancelled = True
            finally:
                if engine:
                    try:
                        engine.quit()
                    except Exception:
                        pass
                self.isRunning = False
                onDone(activeRunId, botName, targetDepth, totalNodes, totalSeconds, cancelled)

        threading.Thread(target=Worker, daemon=True).start()

    def Stop(self) -> None:
        self.stopRequested = True


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

    textSurface = font.render(label, True, ColorTextActive)
    textRect = textSurface.get_rect(center=buttonRect.center)
    surface.blit(textSurface, textRect)


def DrawResultsArea(
    surface: pygame.Surface,
    titleFont: pygame.font.Font,
    headerFont: pygame.font.Font,
    rowFont: pygame.font.Font,
    summaryHistory: list[dict],
    currentSteps: list[dict],
    activeBotName: str,
    activeDepth: int,
    isRunning: bool,
) -> None:
    areaRect = pygame.Rect(0, 0, TableAreaWidth, WindowHeight)
    pygame.draw.rect(surface, ColorBackground, areaRect)

    # Top Section: Run Comparison Summary
    titleSurf = titleFont.render("Search Benchmark", True, ColorTextActive)
    surface.blit(titleSurf, (20, 18))

    summaryCols = [
        ("#", 24),
        ("Bot", 56),
        ("Depth", 230),
        ("Nodes", 295),
        ("Time (ms)", 415),
        ("NPS", 525),
        ("Delta", 615),
    ]

    summaryHeaderY = 58
    summaryHeaderRect = pygame.Rect(16, summaryHeaderY - 5, TableAreaWidth - 32, 28)
    pygame.draw.rect(surface, ColorDropdownBackground, summaryHeaderRect, border_radius=4)
    pygame.draw.rect(surface, ColorDropdownBorder, summaryHeaderRect, width=1, border_radius=4)

    for colLabel, colX in summaryCols:
        colSurf = headerFont.render(colLabel, True, ColorTextActive)
        surface.blit(colSurf, (colX, summaryHeaderY))

    if not summaryHistory:
        emptySurf = rowFont.render(
            "Select a bot and depth on the right, then click Run Benchmark.",
            True,
            ColorTextMuted,
        )
        surface.blit(emptySurf, (24, summaryHeaderY + 36))
    else:
        rowHeight = 28
        startY = summaryHeaderY + 28
        visibleRuns = summaryHistory[-5:]
        baselineMs = visibleRuns[0]["timeMs"]

        for idx, run in enumerate(visibleRuns):
            rowY = startY + idx * rowHeight
            rowRect = pygame.Rect(16, rowY, TableAreaWidth - 32, rowHeight - 2)
            if idx % 2 == 1:
                pygame.draw.rect(surface, ColorRowAlt, rowRect, border_radius=3)

            if idx == 0 or baselineMs <= 0:
                deltaText = "base"
            else:
                pctChange = ((run["timeMs"] - baselineMs) / baselineMs) * 100.0
                deltaText = f"{pctChange:+.1f}%"

            values = [
                (str(idx + 1), 24),
                (run["botName"][:18], 56),
                (str(run["depth"]), 230),
                (f"{run['nodes']:,}", 295),
                (f"{run['timeMs']:,.1f}", 415),
                (f"{run['nps']:,}", 525),
                (deltaText, 615),
            ]
            for valText, valX in values:
                valSurf = rowFont.render(valText, True, ColorPanelText)
                surface.blit(valSurf, (valX, rowY + 5))

    # Bottom Section: Per-Position Breakdown for Active / Latest Run
    breakdownTitleY = 235
    breakdownLabel = (
        f"Position Breakdown — {activeBotName} (Depth {activeDepth})"
        if activeBotName
        else "Position Breakdown"
    )
    subTitleSurf = headerFont.render(breakdownLabel, True, ColorTextActive)
    surface.blit(subTitleSurf, (20, breakdownTitleY))

    posCols = [
        ("#", 24),
        ("Position", 56),
        ("Best Move", 250),
        ("Nodes", 355),
        ("Time (ms)", 480),
        ("NPS", 585),
    ]

    posHeaderY = breakdownTitleY + 28
    posHeaderRect = pygame.Rect(16, posHeaderY - 5, TableAreaWidth - 32, 28)
    pygame.draw.rect(surface, ColorDropdownBackground, posHeaderRect, border_radius=4)
    pygame.draw.rect(surface, ColorDropdownBorder, posHeaderRect, width=1, border_radius=4)

    for colLabel, colX in posCols:
        colSurf = headerFont.render(colLabel, True, ColorTextActive)
        surface.blit(colSurf, (colX, posHeaderY))

    posRowHeight = 27
    posStartY = posHeaderY + 28
    for idx, (label, _) in enumerate(BenchPositions):
        rowY = posStartY + idx * posRowHeight
        rowRect = pygame.Rect(16, rowY, TableAreaWidth - 32, posRowHeight - 2)
        if idx % 2 == 1:
            pygame.draw.rect(surface, ColorRowAlt, rowRect, border_radius=3)

        if idx < len(currentSteps):
            step = currentSteps[idx]
            values = [
                (str(idx + 1), 24),
                (label[:22], 56),
                (step["move"], 250),
                (f"{step['nodes']:,}", 355),
                (f"{step['timeMs']:,.2f}", 480),
                (f"{step['nps']:,}", 585),
            ]
            textColor = ColorPanelText
        else:
            statusMarker = "Searching..." if (isRunning and idx == len(currentSteps)) else "-"
            values = [
                (str(idx + 1), 24),
                (label[:22], 56),
                (statusMarker, 250),
                ("-", 355),
                ("-", 480),
                ("-", 585),
            ]
            textColor = ColorTextActive if statusMarker == "Searching..." else ColorTextMuted

        for valText, valX in values:
            valSurf = rowFont.render(valText, True, textColor)
            surface.blit(valSurf, (valX, rowY + 5))


def DrawControlPanel(
    surface: pygame.Surface,
    headerFont: pygame.font.Font,
    buttonFont: pygame.font.Font,
    botDropdown: DropdownMenu,
    depthDropdown: DropdownMenu,
    runButtonRect: pygame.Rect,
    clearButtonRect: pygame.Rect,
    isRunning: bool,
    completedCount: int,
    totalCount: int,
    statusText: str,
    mousePosition: tuple[int, int],
) -> None:
    panelRect = pygame.Rect(TableAreaWidth, 0, ControlPanelWidth, WindowHeight)
    pygame.draw.rect(surface, ColorPanelBackground, panelRect)

    botLabel = headerFont.render("Engine Bot", True, ColorPanelText)
    surface.blit(botLabel, (TableAreaWidth + 20, 20))
    botDropdown.Draw(surface, headerFont, mousePosition)

    depthLabel = headerFont.render("Search Depth", True, ColorPanelText)
    surface.blit(depthLabel, (TableAreaWidth + 20, 100))
    depthDropdown.Draw(surface, headerFont, mousePosition)

    if not isRunning:
        DrawButton(
            surface,
            buttonFont,
            runButtonRect,
            "Run Benchmark",
            ColorStartButton,
            ColorStartButtonHover,
            mousePosition,
        )
    else:
        DrawButton(
            surface,
            buttonFont,
            runButtonRect,
            "Stop Benchmark",
            ColorStopButton,
            ColorStopButtonHover,
            mousePosition,
        )

    DrawButton(
        surface,
        buttonFont,
        clearButtonRect,
        "Clear History",
        ColorClearButton,
        ColorClearButtonHover,
        mousePosition,
    )

    # Progress Bar
    barRect = pygame.Rect(TableAreaWidth + 20, clearButtonRect.bottom + 22, ControlPanelWidth - 40, 14)
    pygame.draw.rect(surface, ColorDropdownBackground, barRect, border_radius=4)
    if totalCount > 0 and completedCount > 0:
        fillWidth = int((barRect.width - 2) * min(1.0, completedCount / totalCount))
        fillRect = pygame.Rect(barRect.x + 1, barRect.y + 1, fillWidth, barRect.height - 2)
        pygame.draw.rect(surface, ColorProgressFill, fillRect, border_radius=3)
    pygame.draw.rect(surface, ColorDropdownBorder, barRect, width=1, border_radius=4)

    statusSurf = headerFont.render(statusText, True, ColorPanelText)
    statusRect = statusSurf.get_rect(
        center=(TableAreaWidth + ControlPanelWidth // 2, barRect.bottom + 20)
    )
    surface.blit(statusSurf, statusRect)

    for dropdown in (botDropdown, depthDropdown):
        if dropdown.isOpen:
            dropdown.DrawExpandedList(surface, headerFont, mousePosition)


def PostStepEvent(
    runId: int, label: str, move: str, nodes: int, elapsedSeconds: float, totalCount: int
) -> None:
    event = pygame.event.Event(
        BenchStepEventType,
        {
            "runId": runId,
            "label": label,
            "move": move,
            "nodes": nodes,
            "elapsedSeconds": elapsedSeconds,
            "totalCount": totalCount,
        },
    )
    pygame.event.post(event)


def PostDoneEvent(
    runId: int,
    botName: str,
    depth: int,
    totalNodes: int,
    totalSeconds: float,
    cancelled: bool,
) -> None:
    event = pygame.event.Event(
        BenchDoneEventType,
        {
            "runId": runId,
            "botName": botName,
            "depth": depth,
            "totalNodes": totalNodes,
            "totalSeconds": totalSeconds,
            "cancelled": cancelled,
        },
    )
    pygame.event.post(event)


def Main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WindowWidth, WindowHeight))
    pygame.display.set_caption("Chess Search Benchmark")

    SetWindowDarkMode()

    clock = pygame.time.Clock()
    uiFont = pygame.font.SysFont("Segoe UI", 14)
    buttonFont = pygame.font.SysFont("Segoe UI", 15, bold=True)
    titleFont = pygame.font.SysFont("Segoe UI", 22, bold=True)
    tableHeaderFont = pygame.font.SysFont("Segoe UI", 14, bold=True)
    tableRowFont = pygame.font.SysFont("Consolas", 13)

    botOptions = LoadBotList()
    dropdownWidth = ControlPanelWidth - 40
    dropdownHeight = 34

    botDropdown = DropdownMenu(
        TableAreaWidth + 20, 44, dropdownWidth, dropdownHeight, botOptions
    )
    depthDropdown = DropdownMenu(
        TableAreaWidth + 20, 124, dropdownWidth, dropdownHeight, DepthOptions, selectedIndex=3
    )
    runButtonRect = pygame.Rect(
        TableAreaWidth + 20, 180, dropdownWidth, 34
    )
    clearButtonRect = pygame.Rect(
        TableAreaWidth + 20, 222, dropdownWidth, 34
    )

    runner = BenchmarkRunner()
    summaryHistory: list[dict] = []
    currentSteps: list[dict] = []
    activeBotName = ""
    activeDepth = 7
    statusText = "Ready"

    isAppRunning = True
    while isAppRunning:
        mousePosition = pygame.mouse.get_pos()

        for currentEvent in pygame.event.get():
            if currentEvent.type == pygame.QUIT:
                runner.Stop()
                isAppRunning = False
            elif currentEvent.type == pygame.KEYDOWN and currentEvent.key == pygame.K_ESCAPE:
                runner.Stop()
                isAppRunning = False

            openDropdown = next((d for d in (botDropdown, depthDropdown) if d.isOpen), None)

            if openDropdown is not None:
                openDropdown.HandleEvent(currentEvent)
            else:
                botDropdown.HandleEvent(currentEvent)
                depthDropdown.HandleEvent(currentEvent)

                if (
                    currentEvent.type == pygame.MOUSEBUTTONDOWN
                    and currentEvent.button == 1
                    and runButtonRect.collidepoint(currentEvent.pos)
                ):
                    if not runner.isRunning:
                        selectedBot = botDropdown.GetSelectedOption()
                        selectedDepth = int(depthDropdown.GetSelectedOption().split()[-1])
                        if GetBotCommand(selectedBot):
                            currentSteps = []
                            activeBotName = selectedBot
                            activeDepth = selectedDepth
                            statusText = f"Running 0/{len(BenchPositions)}..."
                            runner.Start(selectedBot, selectedDepth, PostStepEvent, PostDoneEvent)
                        else:
                            statusText = "Bot File Not Found"
                    else:
                        runner.Stop()
                        statusText = "Stopping..."

                elif (
                    currentEvent.type == pygame.MOUSEBUTTONDOWN
                    and currentEvent.button == 1
                    and clearButtonRect.collidepoint(currentEvent.pos)
                ):
                    if not runner.isRunning:
                        summaryHistory = []
                        currentSteps = []
                        activeBotName = ""
                        statusText = "Ready"

            if (
                currentEvent.type == BenchStepEventType
                and getattr(currentEvent, "runId", None) == runner.runId
            ):
                dtSec = currentEvent.elapsedSeconds
                nodes = currentEvent.nodes
                nps = int(nodes / dtSec) if dtSec > 0 else 0
                currentSteps.append(
                    {
                        "label": currentEvent.label,
                        "move": currentEvent.move,
                        "nodes": nodes,
                        "timeMs": dtSec * 1000.0,
                        "nps": nps,
                    }
                )
                statusText = f"Running {len(currentSteps)}/{currentEvent.totalCount}..."

            elif (
                currentEvent.type == BenchDoneEventType
                and getattr(currentEvent, "runId", None) == runner.runId
            ):
                if currentEvent.cancelled:
                    statusText = "Stopped"
                else:
                    dtSec = currentEvent.totalSeconds
                    nodes = currentEvent.totalNodes
                    nps = int(nodes / dtSec) if dtSec > 0 else 0
                    summaryHistory.append(
                        {
                            "botName": currentEvent.botName,
                            "depth": currentEvent.depth,
                            "nodes": nodes,
                            "timeMs": dtSec * 1000.0,
                            "nps": nps,
                        }
                    )
                    statusText = "Complete"

        DrawResultsArea(
            screen,
            titleFont,
            tableHeaderFont,
            tableRowFont,
            summaryHistory,
            currentSteps,
            activeBotName,
            activeDepth,
            runner.isRunning,
        )

        DrawControlPanel(
            screen,
            uiFont,
            buttonFont,
            botDropdown,
            depthDropdown,
            runButtonRect,
            clearButtonRect,
            runner.isRunning,
            len(currentSteps),
            len(BenchPositions),
            statusText,
            mousePosition,
        )

        pygame.display.flip()
        clock.tick(FramesPerSecond)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    Main()