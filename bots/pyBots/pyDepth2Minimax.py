import sys
import chess

# Standard material values (centipawns)
PieceValues = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Piece-square tables from White's perspective (a1 = 0 .. h8 = 63)
PawnTable = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10, -20, -20,  10,  10,   5,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,   5,  10,  25,  25,  10,   5,   5,
    10,  10,  20,  30,  30,  20,  10,  10,
    50,  50,  50,  50,  50,  50,  50,  50,
     0,   0,   0,   0,   0,   0,   0,   0,
]

KnightTable = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BishopTable = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

RookTable = [
      0,   0,   0,   5,   5,   0,   0,   0,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      5,  10,  10,  10,  10,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0,
]

QueenTable = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
      0,   0,   5,   5,   5,   5,   0,  -5,
     -5,   0,   5,   5,   5,   5,   0,  -5,
    -10,   0,   5,   5,   5,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]

KingTable = [
     20,  30,  10,   0,   0,  10,  30,  20,
     20,  20,   0,   0,   0,   0,  20,  20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
]

PieceTables = {
    chess.PAWN: PawnTable,
    chess.KNIGHT: KnightTable,
    chess.BISHOP: BishopTable,
    chess.ROOK: RookTable,
    chess.QUEEN: QueenTable,
    chess.KING: KingTable,
}

MateScore = 30000


def EvaluateBoard(board: chess.Board, plyFromRoot: int) -> int:
    if board.is_checkmate():
        return -MateScore + plyFromRoot if board.turn == chess.WHITE else MateScore - plyFromRoot

    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_fifty_moves()
        or board.is_repetition(2)
    ):
        return 0

    score = 0
    for square, piece in board.piece_map().items():
        value = PieceValues[piece.piece_type]
        table = PieceTables[piece.piece_type]
        if piece.color == chess.WHITE:
            score += value + table[square]
        else:
            score -= value + table[chess.square_mirror(square)]

    return score


def Minimax(board: chess.Board, depth: int, plyFromRoot: int) -> int:
    if depth == 0 or board.is_game_over(claim_draw=True):
        return EvaluateBoard(board, plyFromRoot)

    legalMoves = list(board.legal_moves)
    if not legalMoves:
        return EvaluateBoard(board, plyFromRoot)

    if board.turn == chess.WHITE:
        bestScore = -999999
        for move in legalMoves:
            board.push(move)
            score = Minimax(board, depth - 1, plyFromRoot + 1)
            board.pop()
            if score > bestScore:
                bestScore = score
        return bestScore
    else:
        bestScore = 999999
        for move in legalMoves:
            board.push(move)
            score = Minimax(board, depth - 1, plyFromRoot + 1)
            board.pop()
            if score < bestScore:
                bestScore = score
        return bestScore


def SelectBestMove(board: chess.Board, searchDepth: int = 2) -> chess.Move:
    legalMoves = list(board.legal_moves)
    bestMove = legalMoves[0]

    if board.turn == chess.WHITE:
        bestScore = -999999
        for move in legalMoves:
            board.push(move)
            score = Minimax(board, searchDepth - 1, 1)
            board.pop()
            if score > bestScore:
                bestScore = score
                bestMove = move
    else:
        bestScore = 999999
        for move in legalMoves:
            board.push(move)
            score = Minimax(board, searchDepth - 1, 1)
            board.pop()
            if score < bestScore:
                bestScore = score
                bestMove = move

    return bestMove


def RunUciLoop() -> None:
    board = chess.Board()

    for rawLine in sys.stdin:
        line = rawLine.strip()
        if not line:
            continue

        tokens = line.split()
        command = tokens[0]

        if command == "uci":
            print("id name BaselineMinimax2", flush=True)
            print("id author Patrick", flush=True)
            print("uciok", flush=True)

        elif command == "isready":
            print("readyok", flush=True)

        elif command == "ucinewgame":
            board.reset()

        elif command == "position":
            if len(tokens) > 1 and tokens[1] == "startpos":
                board.reset()
                movesIndex = tokens.index("moves") + 1 if "moves" in tokens else len(tokens)
            elif len(tokens) > 1 and tokens[1] == "fen":
                movesIndex = tokens.index("moves") if "moves" in tokens else len(tokens)
                fenString = " ".join(tokens[2:movesIndex])
                board.set_fen(fenString)
                if "moves" in tokens:
                    movesIndex += 1
            else:
                movesIndex = len(tokens)

            for moveUci in tokens[movesIndex:]:
                board.push_uci(moveUci)

        elif command == "go":
            bestMove = SelectBestMove(board, searchDepth=2)
            print(f"bestmove {bestMove.uci()}", flush=True)

        elif command == "quit":
            break


if __name__ == "__main__":
    RunUciLoop()