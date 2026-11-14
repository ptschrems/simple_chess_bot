#include <iostream>
#include <sstream>
#include <chrono>
#include <string>

#include "chess-library/include/chess.hpp"

bool timeFlag = false;
std::array<bool, 65536> killerMoves = {false};

namespace chess {
    /**
     * Define operator> for Move
     * @param a first
     * @param b second
     * @return true if a's score > b's score
     */
    inline bool operator>(const Move &a, const Move &b) {
        return a.score() > b.score();
    }

    /**
     * Define operator< for Move
     * @param a first
     * @param b second
     * @return true if a's score < b's score
     */
    inline bool operator<(const Move &a, const Move &b) {
        return a.score() < b.score();
    }
}

/**
 * Compute material score for a board
 * @param board const reference board to compute material for
 */
inline chess::Move Evaluate(const chess::Board &board) {
    int16_t score = 0;

    score += 100 * (board.pieces(chess::PieceType::PAWN,   chess::Color::WHITE).count() - board.pieces(chess::PieceType::PAWN,   chess::Color::BLACK).count());
    score += 300 * (board.pieces(chess::PieceType::KNIGHT, chess::Color::WHITE).count() - board.pieces(chess::PieceType::KNIGHT, chess::Color::BLACK).count());
    score += 300 * (board.pieces(chess::PieceType::BISHOP, chess::Color::WHITE).count() - board.pieces(chess::PieceType::BISHOP, chess::Color::BLACK).count());
    score += 500 * (board.pieces(chess::PieceType::ROOK,   chess::Color::WHITE).count() - board.pieces(chess::PieceType::ROOK,   chess::Color::BLACK).count());
    score += 900 * (board.pieces(chess::PieceType::QUEEN,  chess::Color::WHITE).count() - board.pieces(chess::PieceType::QUEEN,  chess::Color::BLACK).count());

    if (board.kingSq(chess::Color::WHITE) == chess::Square::SQ_G1 || board.kingSq(chess::Color::WHITE) == chess::Square::SQ_C1) {
        score++;
    }

    if (board.kingSq(chess::Color::BLACK) == chess::Square::SQ_G8 || board.kingSq(chess::Color::BLACK) == chess::Square::SQ_C8) {
        score--;
    }

    chess::Move move = chess::Move::NO_MOVE;
    move.setScore((board.sideToMove() == chess::Color::WHITE) ? score : -score);
    return move;
}

/**
 * Gets the current time in miliseconds
 * @return time in ms
 */
inline auto GetTime() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

/**
 * Order the moves for better pruning odds
 * @param moves reference to the moves to order
 */
inline void OrderMoves(chess::Movelist &moves) {
    int pos = 0;
    for (auto i = 0; i < moves.size(); i++) {
        if (killerMoves[moves[i].move()]) {
            std::swap(moves[pos++], moves[i]);
        }
    }
}

/**
 * Generate legal moves
 * @param board reference to board to generate legal moves for
 * @return legal moves as chess::Movelist
 */
inline chess::Movelist LegalMoves(chess::Board &board) {
    chess::Movelist moves;
    chess::movegen::legalmoves(moves, board);
    OrderMoves(moves);
    return moves;
}

/**
 * Search using iterative deepening
 * @param board reference to board to search in
 * @param time time allocated for move
 * @param depth remaining depth in search
 * @return best move & score
 */
chess::Move Search(chess::Board &board, uint64_t time, uint8_t depth, int16_t alpha, int16_t beta) {
    if (depth == 0) {
        return Evaluate(board);
    }

    if (board.isRepetition(2) || board.isHalfMoveDraw() || board.isInsufficientMaterial()) {
        return chess::Move::NO_MOVE; // Draw
    }

    if (GetTime() > time) {
        // Invalid search
        timeFlag = true;
        return chess::Move::NULL_MOVE;
    }

    auto moves = LegalMoves(board);

    chess::Move returnMove = chess::Move::NO_MOVE;

    if (moves.empty()) {
        if (board.inCheck()) {
            returnMove.setScore(-32767 + 1000 - depth); // NOT -32768 to prevent any potential overflow
        }
        return returnMove;
    }

    returnMove = moves[0];
    returnMove.setScore(-32767);

    for (auto &move : moves) {
        board.makeMove(move);
        auto eval = Search(board, time, depth - 1, -beta, -alpha);
        eval.setScore(-eval.score());
        if (eval > returnMove) {
            returnMove = move;
            returnMove.setScore(eval.score());
        } else if (eval.score() < -10000) {
            killerMoves[move.move()] = true;
        }
        board.unmakeMove(move);

        if (eval.score() > alpha) {
            alpha = eval.score();
        }
        if (alpha >= beta) {
            break; // snip
        }
    }

    return returnMove;
}

/**
 * Search using iterative deepening
 * @param board reference to board to search in
 * @param time time allocated for move
 * @return best move & score
 */
chess::Move IterativeSearch(chess::Board &board, uint16_t time) {
    auto moves = LegalMoves(board);
    if (moves.empty()) {
        return chess::Move::NO_MOVE;
    }
    auto bestMove = moves[0];
    bestMove.setScore(-32767);
    auto start = GetTime();
    int depth = 1;

    while (GetTime() - start < time) {
        chess::Move depthBest = chess::Move::NULL_MOVE;
        depthBest.setScore(-32767);
        for (auto &move : moves) {
            board.makeMove(move);
            auto result = Search(board, start + time, depth, -32767, 32767);
            if (!timeFlag) {
                move.setScore(-result.score());
            }
            if (move > depthBest) {
                depthBest = move;
            }
            board.unmakeMove(move);
        }
        if (!timeFlag) {
            bestMove = depthBest;
        }
        depth++;
    }
    return bestMove;
}

/**
 * Reset a killer moves array
 * @param killerMoves reference to the array to reset
 */
inline void ResetKillerMoves(std::array<bool, 65536> &killerMoves) {
    killerMoves.fill(false);
}

int main() {
    chess::Board board;
    std::string line;

    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string token;
        iss >> token;

        if (token == "uci") {
            std::cout << "id name BotKillerMove\n";
            std::cout << "id author Patrick\n";
            std::cout << "uciok\n" << std::flush;
        } else if (token == "isready") {
            std::cout << "readyok\n" << std::flush;
        } else if (token == "ucinewgame") {
            board = chess::Board();
        } else if (token == "position") {
            std::string sub;
            iss >> sub;
            if (sub == "startpos") {
                board = chess::Board();
                iss >> sub;
            } else if (sub == "fen") {
                std::string fen, part;
                while (iss >> part && part != "moves") {
                    if (!fen.empty()) fen += " ";
                    fen += part;
                }
                board = chess::Board(fen);
                sub = part;
            }
            if (sub == "moves") {
                std::string moveStr;
                while (iss >> moveStr) {
                    board.makeMove(chess::uci::uciToMove(board, moveStr));
                }
            }
        } else if (token == "go") {
            int movetime = -1, wtime = -1, btime = -1, winc = 0, binc = 0;
            std::string param;
            while (iss >> param) {
                if (param == "movetime") iss >> movetime;
                else if (param == "wtime") iss >> wtime;
                else if (param == "btime") iss >> btime;
                else if (param == "winc") iss >> winc;
                else if (param == "binc") iss >> binc;
            }

            int timeMS = 100;
            if (movetime > 0) {
                timeMS = std::max(1, movetime - 10);
            } else {
                int myTime = (board.sideToMove() == chess::Color::WHITE) ? wtime : btime;
                int myInc = (board.sideToMove() == chess::Color::WHITE) ? winc : binc;
                if (myTime > 0) {
                    timeMS = std::max(10, (myTime / 30) + (myInc / 2) - 10);
                }
            }

            timeFlag = false;
            chess::Move bestMove = IterativeSearch(board, timeMS);
            std::cout << "bestmove " << chess::uci::moveToUci(bestMove) << "\n" << std::flush;
            ResetKillerMoves(killerMoves);
        } else if (token == "quit") {
            break;
        }
    }

    return 0;
}