import sys
import random
import chess


def ParsePosition(board: chess.Board, tokens: list[str]) -> None:
    if "startpos" in tokens:
        board.reset()
    elif "fen" in tokens:
        fenIndex = tokens.index("fen") + 1
        movesIndex = tokens.index("moves") if "moves" in tokens else len(tokens)
        board.set_fen(" ".join(tokens[fenIndex:movesIndex]))

    if "moves" in tokens:
        movesIndex = tokens.index("moves") + 1
        for moveUci in tokens[movesIndex:]:
            board.push_uci(moveUci)


def Main() -> None:
    board = chess.Board()

    for rawLine in sys.stdin:
        line = rawLine.strip()
        if not line:
            continue

        tokens = line.split()
        command = tokens[0]

        if command == "uci":
            print("id name RandomBot")
            print("id author Patrick")
            print("uciok", flush=True)

        elif command == "isready":
            print("readyok", flush=True)

        elif command == "ucinewgame":
            board.reset()

        elif command == "position":
            ParsePosition(board, tokens)

        elif command == "go":
            legalMoves = list(board.legal_moves)
            if legalMoves:
                chosenMove = random.choice(legalMoves)
                print(f"bestmove {chosenMove.uci()}", flush=True)
            else:
                print("bestmove 0000", flush=True)

        elif command == "quit":
            break


if __name__ == "__main__":
    Main()