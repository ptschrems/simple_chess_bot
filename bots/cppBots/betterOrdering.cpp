#include <iostream>
#include <sstream>
#include <chrono>
#include <string>
#include <atomic>
#include <thread>
#include <vector>
#include <semaphore>

#include "chess-library/include/chess.hpp"

std::atomic<bool> timeFlag = false;
std::array<bool, 65536> killerMoves = {false};
std::binary_semaphore bestLock(1);
std::binary_semaphore ttLock(1);
std::atomic<uint64_t> nodes = 0;


/**
 * Class for transposition table entries
 */
class TranspositionEntry {
public:
    uint64_t hash;
    int16_t eval;
};

const size_t TranspositionEntries = 0x1000000;
std::array<TranspositionEntry, TranspositionEntries> transpositionTable;

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
 * Look up in transposition table
 * @param board const reference to board to lookup in table
 * @return eval, bool pair, where true if in table
 */
inline std::pair<int16_t, bool> TranspositionLookup(const chess::Board &board) {
    auto hash = board.hash();

    ttLock.acquire();
    auto lookup = transpositionTable[hash % TranspositionEntries];
    ttLock.release();

    if (lookup.hash != hash) {
        return {0, false};
    }
    return {lookup.eval, true};
}

/**
 * Insert a value into the transposition table
 * @param board const reference to board to add to table
 * @param eval evaluation of board
 */
inline void TranspositionInsert(const chess::Board &board, int16_t eval) {
    auto hash = board.hash();

    ttLock.acquire();
    transpositionTable[hash % TranspositionEntries] = TranspositionEntry(hash, eval);
    ttLock.release();
}

inline std::vector<chess::Square> GetPieceLocations(
    const chess::Board &board, 
    chess::PieceType pieceType, 
    chess::Color color
) {
    std::vector<chess::Square> locations;
    chess::Bitboard bb = board.pieces(pieceType, color);
    locations.reserve(bb.count());

    while (bb) {
        locations.push_back(bb.pop());
    }

    return locations;
}

inline int16_t EvaluatePawns(const chess::Board &board) {
    int16_t score = 0;
    const std::array<int16_t, 64> pawnEvals = {
        0, 0, 0, 0, 0, 0, 0, 0,
        150, 150, 150, 150, 150, 150, 150, 150,
        110, 110, 120, 130, 130, 120, 110, 110,
        105, 105, 110, 125, 125, 110, 105, 105,
        100, 100, 100, 120, 120, 100, 100, 100,
        105, 95, 90, 100, 100, 90, 95, 105,
        105, 110, 110, 80, 80, 110, 110, 105,
        0, 0, 0, 0, 0, 0, 0, 0
    };
    for (auto sq : GetPieceLocations(board, chess::PieceType::PAWN, chess::Color::WHITE)) {
        score += pawnEvals[sq.flip().index()];
    }
    for (auto sq : GetPieceLocations(board, chess::PieceType::PAWN, chess::Color::BLACK)) {
        score -= pawnEvals[sq.index()];
    }
    return score;
}

inline int16_t EvaluateKnights(const chess::Board &board) {
    int16_t score = 0;
    const std::array<int16_t, 64> knightEvals = {
        250,260,270,270,270,270,260,250,
        260,280,300,300,300,300,280,260,
        270,300,310,315,315,310,300,270,
        270,305,315,320,320,315,305,270,
        270,305,315,320,320,315,305,270,
        270,300,310,315,315,310,300,270,
        260,280,300,300,300,300,280,260,
        250,260,270,270,270,270,260,250
    };
    for (auto sq : GetPieceLocations(board, chess::PieceType::KNIGHT, chess::Color::WHITE)) {
        score += knightEvals[sq.flip().index()];
    }
    for (auto sq : GetPieceLocations(board, chess::PieceType::KNIGHT, chess::Color::BLACK)) {
        score -= knightEvals[sq.index()];
    }
    return score;
}

inline int16_t EvaluateBishops(const chess::Board &board) {
    int16_t score = 0;
    const std::array<int16_t, 64> bishopEvals = {
        280, 290, 290, 290, 290, 290, 290, 280, 290, 300, 300, 300, 300,
        300, 300, 290, 290, 300, 305, 310, 310, 305, 300, 290, 290, 305,
        305, 310, 310, 305, 305, 290, 290, 300, 310, 310, 310, 310, 300,
        290, 290, 310, 310, 310, 310, 310, 310, 290, 290, 305, 300, 300,
        300, 300, 305, 290, 280, 290, 290, 290, 290, 290, 290, 280
    };
    for (auto sq : GetPieceLocations(board, chess::PieceType::BISHOP, chess::Color::WHITE)) {
        score += bishopEvals[sq.flip().index()];
    }
    for (auto sq : GetPieceLocations(board, chess::PieceType::BISHOP, chess::Color::BLACK)) {
        score -= bishopEvals[sq.index()];
    }
    return score;
}

inline int16_t EvaluateRooks(const chess::Board &board) {
    int16_t score = 0;
    const std::array<int16_t, 64> rookEvals = {
        500, 500, 500, 500, 500, 500, 500, 500, 505, 510, 510, 510, 510,
        510, 510, 505, 495, 500, 500, 500, 500, 500, 500, 495, 495, 500,
        500, 500, 500, 500, 500, 495, 495, 500, 500, 500, 500, 500, 500,
        495, 495, 500, 500, 500, 500, 500, 500, 495, 495, 500, 500, 500,
        500, 500, 500, 495, 500, 500, 500, 505, 505, 500, 500, 500
    };
    for (auto sq : GetPieceLocations(board, chess::PieceType::ROOK, chess::Color::WHITE)) {
        score += rookEvals[sq.flip().index()];
    }
    for (auto sq : GetPieceLocations(board, chess::PieceType::ROOK, chess::Color::BLACK)) {
        score -= rookEvals[sq.index()];
    }
    return score;
}

inline int16_t EvaluateQueens(const chess::Board &board) {
    int16_t score = 0;
    const std::array<int16_t, 64> queenEvals = {
        880, 890, 890, 895, 895, 890, 890, 880, 890, 900, 900, 900, 900,
        900, 900, 890, 890, 900, 905, 905, 905, 905, 900, 890, 895, 900,
        905, 905, 905, 905, 900, 895, 900, 900, 905, 905, 905, 905, 900,
        895, 890, 905, 905, 905, 905, 905, 900, 890, 890, 900, 905, 900,
        900, 900, 900, 890, 880, 890, 890, 895, 895, 890, 890, 880
    };
    for (auto sq : GetPieceLocations(board, chess::PieceType::QUEEN, chess::Color::WHITE)) {
        score += queenEvals[sq.flip().index()];
    }
    for (auto sq : GetPieceLocations(board, chess::PieceType::QUEEN, chess::Color::BLACK)) {
        score -= queenEvals[sq.index()];
    }
    return score;
}

/**
 * Compute material score for a board
 * @param board const reference board to compute material for
 */
inline chess::Move Evaluate(const chess::Board &board) {
    auto cached = TranspositionLookup(board);
    if (cached.second) {
        chess::Move move = chess::Move::NO_MOVE;
        move.setScore(cached.first);
        return move;
    }

    int16_t score = 0;
    score += EvaluatePawns(board);
    score += EvaluateKnights(board);
    score += EvaluateBishops(board);
    score += EvaluateRooks(board);
    score += EvaluateQueens(board);

    if (board.kingSq(chess::Color::WHITE) == chess::Square::SQ_G1 || board.kingSq(chess::Color::WHITE) == chess::Square::SQ_C1) {
        score++;
    }

    if (board.kingSq(chess::Color::BLACK) == chess::Square::SQ_G8 || board.kingSq(chess::Color::BLACK) == chess::Square::SQ_C8) {
        score--;
    }

    chess::Move move = chess::Move::NO_MOVE;
    move.setScore((board.sideToMove() == chess::Color::WHITE) ? score : -score);
    TranspositionInsert(board, move.score());
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
        if (killerMoves[moves[i].move()] || moves[i].typeOf() == chess::Move::PROMOTION) {
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
    nodes++;
    if (board.isRepetition(2) || board.isHalfMoveDraw() || board.isInsufficientMaterial()) {
        return chess::Move::NO_MOVE; // Draw
    }

    if (depth == 0) {
        return Evaluate(board);
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
        } 
        if (abs(eval.score()) > 10000) {
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
        {
            std::vector<std::jthread> threads;
            threads.reserve(moves.size());

            for (auto &move : moves) {
                threads.emplace_back([&, move]() mutable {
                    chess::Board localBoard = board;
                    localBoard.makeMove(move);

                    bestLock.acquire();
                    int16_t currentBeta = -depthBest.score();
                    bestLock.release();
                    
                    auto result = Search(localBoard, start + time, depth, -32767, currentBeta);
                    if (!timeFlag) {
                        move.setScore(-result.score());
                        bestLock.acquire();
                        if (move > depthBest) {
                            depthBest = move;
                        }
                        bestLock.release();
                    }
                });
            }
        }

        if (!timeFlag) {
            bestMove = depthBest;
        }
        depth++;
    }
    return bestMove;
}

/**
 * Parallel benchmarking
 * @param board reference to board to search in
 * @param time time allocated for move
 * @param depth the depth to test
 * @return best move & score
 */
chess::Move ParallelBenchmark(chess::Board &board, uint16_t time, int depth) {
    auto moves = LegalMoves(board);
    if (moves.empty()) {
        return chess::Move::NO_MOVE;
    }
    auto bestMove = moves[0];
    bestMove.setScore(-32767);
    auto start = GetTime();

    while (GetTime() - start < time) {
        chess::Move depthBest = chess::Move::NULL_MOVE;
        depthBest.setScore(-32767);
        {
            std::vector<std::jthread> threads;
            threads.reserve(moves.size());

            for (auto &move : moves) {
                nodes++;
                threads.emplace_back([&, move]() mutable {
                    chess::Board localBoard = board;
                    localBoard.makeMove(move);

                    bestLock.acquire();
                    int16_t currentBeta = -depthBest.score();
                    bestLock.release();
                    
                    auto result = Search(localBoard, start + 9999999, depth - 1, -32767, currentBeta);
                    if (!timeFlag) {
                        move.setScore(-result.score());
                        bestLock.acquire();
                        if (move > depthBest) {
                            depthBest = move;
                        }
                        bestLock.release();
                    }
                });
            }
        }

        if (!timeFlag) {
            bestMove = depthBest;
        }
        break;
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
            std::cout << "id name BotBetterOrdering\n";
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
            int movetime = -1, wtime = -1, btime = -1, winc = 0, binc = 0, maxDepth = 0;
            std::string param;
            while (iss >> param) {
                if (param == "movetime") iss >> movetime;
                else if (param == "wtime") iss >> wtime;
                else if (param == "btime") iss >> btime;
                else if (param == "winc") iss >> winc;
                else if (param == "binc") iss >> binc;
                else if (param == "depth") iss >> maxDepth;
            }

            nodes = 0;
            auto t0 = GetTime();

            if (maxDepth > 0) {
                timeFlag = false;
                chess::Move bestMove = ParallelBenchmark(board, t0 + 90000000, maxDepth); 
                auto elapsed = std::max<int64_t>(1, GetTime() - t0);
                uint64_t nps = (nodes * 1000ULL) / elapsed;

                std::cout << "info depth " << maxDepth
                        << " score cp " << bestMove.score()
                        << " nodes " << nodes
                        << " time " << elapsed
                        << " nps " << nps << "\n";
                std::cout << "bestmove " << chess::uci::moveToUci(bestMove) << "\n" << std::flush;
            } else {
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
            }
            ResetKillerMoves(killerMoves);
        } else if (token == "quit") {
            break;
        }
    }

    return 0;
}