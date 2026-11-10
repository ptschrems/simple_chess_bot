import os
import sys
import ctypes
import pygame
import chess

# Constants
BoardSize = 8
SquareSize = 80
BoardPixelSize = BoardSize * SquareSize
ControlPanelWidth = 240
WindowWidth = BoardPixelSize + ControlPanelWidth
WindowHeight = BoardPixelSize
FramesPerSecond = 60

# DWM Attribute Constant for Windows 10/11 Dark Title Bar
DwmwaUseImmersiveDarkMode = 20

# Color Palette
ColorLight = pygame.Color(138, 138, 110)
ColorDark = pygame.Color(55, 50, 5)
ColorLabelLight = ColorDark
ColorLabelDark = ColorLight
ColorPanelBackground = pygame.Color(32, 32, 32)
ColorPanelText = pygame.Color(220, 220, 220)
ColorDropdownBackground = pygame.Color(45, 45, 45)
ColorDropdownBorder = pygame.Color(70, 70, 70)
ColorDropdownHover = pygame.Color(65, 65, 65)
ColorDropdownSelected = pygame.Color(80, 80, 80)
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
                botList.append(botName)

    return botList


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
        return "Human"

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


def DrawControlPanel(
    surface: pygame.Surface,
    headerFont: pygame.font.Font,
    whiteDropdown: DropdownMenu,
    blackDropdown: DropdownMenu,
    mousePosition: tuple[int, int],
) -> None:
    panelRect = pygame.Rect(
        BoardPixelSize, 0, ControlPanelWidth, WindowHeight
    )
    pygame.draw.rect(surface, ColorPanelBackground, panelRect)

    whiteLabel = headerFont.render("White Player", True, ColorPanelText)
    surface.blit(whiteLabel, (BoardPixelSize + 20, 30))

    blackLabel = headerFont.render("Black Player", True, ColorPanelText)
    surface.blit(blackLabel, (BoardPixelSize + 20, 120))

    whiteDropdown.Draw(surface, headerFont, mousePosition)
    blackDropdown.Draw(surface, headerFont, mousePosition)

    if whiteDropdown.isOpen:
        whiteDropdown.DrawExpandedList(surface, headerFont, mousePosition)
    elif blackDropdown.isOpen:
        blackDropdown.DrawExpandedList(surface, headerFont, mousePosition)


def Main() -> None:
    pygame.init()
    gameScreen = pygame.display.set_mode((WindowWidth, WindowHeight))
    pygame.display.set_caption("Chess")

    SetWindowDarkMode()

    gameClock = pygame.time.Clock()
    labelFont = pygame.font.SysFont("Segoe UI", 14, bold=True)
    uiFont = pygame.font.SysFont("Segoe UI", 14)
    pieceFont = pygame.font.SysFont("Segoe UI Symbol", 56)

    # Initialize chess model
    chessBoard = chess.Board()

    botOptions = LoadBotList()
    dropdownWidth = ControlPanelWidth - 40
    dropdownHeight = 36

    whiteDropdown = DropdownMenu(
        BoardPixelSize + 20, 58, dropdownWidth, dropdownHeight, botOptions
    )
    blackDropdown = DropdownMenu(
        BoardPixelSize + 20, 148, dropdownWidth, dropdownHeight, botOptions
    )

    isGameRunning = True
    while isGameRunning:
        mousePosition = pygame.mouse.get_pos()

        for currentEvent in pygame.event.get():
            if currentEvent.type == pygame.QUIT:
                isGameRunning = False
            elif currentEvent.type == pygame.KEYDOWN and currentEvent.key == pygame.K_ESCAPE:
                isGameRunning = False

            if whiteDropdown.isOpen:
                whiteDropdown.HandleEvent(currentEvent)
            elif blackDropdown.isOpen:
                blackDropdown.HandleEvent(currentEvent)
            else:
                whiteDropdown.HandleEvent(currentEvent)
                blackDropdown.HandleEvent(currentEvent)

        DrawBoard(gameScreen, labelFont)
        DrawPieces(gameScreen, chessBoard, pieceFont)
        DrawControlPanel(gameScreen, uiFont, whiteDropdown, blackDropdown, mousePosition)

        pygame.display.flip()
        gameClock.tick(FramesPerSecond)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    Main()