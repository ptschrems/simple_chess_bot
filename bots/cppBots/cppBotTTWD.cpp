#include <iostream>
#include <sstream>
#include <chrono>
#include <string>
#include <unordered_map>
#include <bit>
#include <array>
#include <random>
#include <algorithm>

#include "chess-library/include/chess.hpp"

auto getTime() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

static const std::array<int16_t, 64> PAWN_TABLE = {
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
};

static const std::array<int16_t, 64> KNIGHT_TABLE = {
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
};

static const std::array<int16_t, 64> BISHOP_TABLE = {
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
};

static const std::array<int16_t, 64> ROOK_TABLE = {
    0,  0,  0,  0,  0,  0,  0,  0,
    5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    0,  0,  0,  5,  5,  0,  0,  0
};

static const std::array<int16_t, 64> QUEEN_TABLE = {
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
};

int16_t material3(const chess::Board &board, int depth = 0) {
    if (board.isRepetition(3) || board.isHalfMoveDraw()) {
        return 0;
    }
    chess::Movelist moves;
    chess::movegen::legalmoves(moves, board);
    if (moves.size() == 0) {
        if (board.inCheck()) {
            return board.sideToMove() ? 32767 - depth : -32767 + depth;
        }
        return 0;
    }

    int16_t m = 0;

    std::array<int16_t, 64> KING_TABLE;
    if (board.pieces(chess::PieceType::QUEEN).getBits()) {
        KING_TABLE = {
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -20,-30,-30,-40,-40,-30,-30,-20,
            -10,-20,-20,-20,-20,-20,-20,-10,
            20, 20,  0,  0,  0,  0, 20, 20,
            20, 30, 10,  0,  0, 10, 30, 20
        };
    } else {
        KING_TABLE = {
            -50,-40,-30,-20,-20,-30,-40,-50,
            -30,-20,-10,  0,  0,-10,-20,-30,
            -30,-10, 20, 30, 30, 20,-10,-30,
            -30,-10, 30, 40, 40, 30,-10,-30,
            -30,-10, 30, 40, 40, 30,-10,-30,
            -30,-10, 20, 30, 30, 20,-10,-30,
            -30,-30,  0,  0,  0,  0,-30,-30,
            -50,-30,-30,-30,-30,-30,-30,-50
        };
    }

    auto wPawnBB = board.pieces(chess::PieceType::PAWN, chess::Color::WHITE).getBits();
    auto bPawnBB = board.pieces(chess::PieceType::PAWN, chess::Color::BLACK).getBits();
    auto index = std::countr_zero(wPawnBB);
    while (wPawnBB) {
        m += PAWN_TABLE[63 - index] + 100;
        wPawnBB = wPawnBB >> (index + 1);
        index += std::countr_zero(wPawnBB);
    }
    index = std::countr_zero(bPawnBB);
    while (bPawnBB) {
        m -= PAWN_TABLE[index] + 100;
        bPawnBB = bPawnBB >> (index + 1);
        index += std::countr_zero(bPawnBB);
    }

    auto wKnightBB = board.pieces(chess::PieceType::KNIGHT, chess::Color::WHITE).getBits();
    auto bKnightBB = board.pieces(chess::PieceType::KNIGHT, chess::Color::BLACK).getBits();
    index = std::countr_zero(wKnightBB);
    while (wKnightBB) {
        m += KNIGHT_TABLE[63 - index] + 300;
        wKnightBB = wKnightBB >> (index + 1);
        index += std::countr_zero(wKnightBB);
    }
    index = std::countr_zero(bKnightBB);
    while (bKnightBB) {
        m -= KNIGHT_TABLE[index] + 300;
        bKnightBB = bKnightBB >> (index + 1);
        index += std::countr_zero(bKnightBB);
    }

    auto wBishopBB = board.pieces(chess::PieceType::BISHOP, chess::Color::WHITE).getBits();
    auto bBishopBB = board.pieces(chess::PieceType::BISHOP, chess::Color::BLACK).getBits();
    index = std::countr_zero(wBishopBB);
    while (wBishopBB) {
        m += BISHOP_TABLE[63 - index] + 300;
        wBishopBB = wBishopBB >> (index + 1);
        index += std::countr_zero(wBishopBB);
    }
    index = std::countr_zero(bBishopBB);
    while (bBishopBB) {
        m -= BISHOP_TABLE[index] + 300;
        bBishopBB = bBishopBB >> (index + 1);
        index += std::countr_zero(bBishopBB);
    }
    
    auto wRookBB = board.pieces(chess::PieceType::ROOK, chess::Color::WHITE).getBits(); 
    auto bRookBB = board.pieces(chess::PieceType::ROOK, chess::Color::BLACK).getBits();
    index = std::countr_zero(wRookBB);
    while (wRookBB) {
        m += ROOK_TABLE[63 - index] + 500;
        wRookBB = wRookBB >> (index + 1);
        index += std::countr_zero(wRookBB);
    }
    index = std::countr_zero(bRookBB);
    while (bRookBB) {
        m -= ROOK_TABLE[index] + 500;
        bRookBB = bRookBB >> (index + 1);
        index += std::countr_zero(bRookBB);
    }
    
    auto wQueenBB = board.pieces(chess::PieceType::QUEEN, chess::Color::WHITE).getBits();
    auto bQueenBB = board.pieces(chess::PieceType::QUEEN, chess::Color::BLACK).getBits();
    index = std::countr_zero(wQueenBB);
    while (wQueenBB) {
        m += QUEEN_TABLE[63 - index] + 900;
        wQueenBB = wQueenBB >> (index + 1);
        index += std::countr_zero(wQueenBB);
    }
    index = std::countr_zero(bQueenBB);
    while (bQueenBB) {
        m -= QUEEN_TABLE[index] + 900;
        bQueenBB = bQueenBB >> (index + 1);
        index += std::countr_zero(bQueenBB);
    }

    auto wKingBB = board.pieces(chess::PieceType::KING, chess::Color::WHITE).getBits();
    auto bKingBB = board.pieces(chess::PieceType::KING, chess::Color::BLACK).getBits();
    index = std::countr_zero(wKingBB);
    m += KING_TABLE[63 - index];
    index = std::countr_zero(bKingBB);
    m -= KING_TABLE[index];
    
    return m;
}

std::unordered_map<uint64_t, int16_t> transpositionTableM3;
int16_t transTableEvalM3(const chess::Board &board, int maxDepth) {
    if (transpositionTableM3.find(board.hash()) != transpositionTableM3.end()) {
        return transpositionTableM3[board.hash()];
    }
    auto eval = material3(board, maxDepth);
    transpositionTableM3[board.hash()] = eval;
    return eval;
}

// Stores hash as key and pair of evaluation and depth (in that order) as value.
std::unordered_map<uint64_t, std::pair<int16_t, int16_t>> transpositionTableWD;

std::pair<int16_t, bool> minimaxTTWD(chess::Board board, int depth, auto endTime, int16_t alpha, int16_t beta, int maxDepth) {
    if (getTime() > endTime) {
        return std::make_pair(0, true);
    }
    if (board.isRepetition(2) || board.isHalfMoveDraw() || board.isInsufficientMaterial()) {
        return std::make_pair(0, false);
    }
    if (depth <= 0) {
        return std::make_pair(transTableEvalM3(board, maxDepth - depth), false);
    }

    chess::Movelist moves;
    chess::movegen::legalmoves(moves, board);

    if (moves.size() == 0) {
        if (board.inCheck()) {
            return board.sideToMove() ? std::make_pair((32767 - maxDepth) + depth, false) : std::make_pair((-32767 + maxDepth) - depth, false);
        }
        return std::make_pair(0, false);
    }

    auto loc = transpositionTableWD.find(board.hash());
    if (loc != transpositionTableWD.end()) {
        if (loc->second.second >= depth) {
            return std::make_pair(loc->second.first, false);
        }
    }

    int16_t eval;
    if (board.sideToMove()) {
        eval = 32767;
    } else {
        eval = -32767;
    }

    for (const auto &move : moves) {
        board.makeMove(move);
        if (board.sideToMove()) {
            auto newEval = minimaxTTWD(board, depth - 1, endTime, alpha, beta, maxDepth);
            if (!newEval.second) {
                eval = std::max(eval, newEval.first);
                if (eval >= beta) {
                    return std::make_pair(beta, false);
                }
                alpha = std::max(alpha, eval);
            } else {
                return std::make_pair(0, true);
            }
        } else {
            auto newEval = minimaxTTWD(board, depth - 1, endTime, alpha, beta, maxDepth);
            if (!newEval.second) {
                eval = std::min(eval, newEval.first);
                if (eval <= alpha) {
                    return std::make_pair(alpha, false);
                }
                beta = std::min(beta, eval);
            } else {
                return std::make_pair(0, true);
            }
        }
        board.unmakeMove(move);
    }
    transpositionTableWD[board.hash()] = std::make_pair(eval, depth);
    return std::make_pair(eval, false);
}

chess::Move searchTTWD(chess::Board board, int timeMS) {
    auto endTime = getTime() + timeMS;
    chess::Movelist moves;
    chess::movegen::legalmoves(moves, board);
    std::vector<std::pair<chess::Move, int16_t>> scores;
    for (const auto &move : moves) {
        board.makeMove(move);
        scores.push_back({move, minimaxTTWD(board, 0, 1000000, -32767, 32767, 0).first});
        board.unmakeMove(move);
    }
    int count{1};
    while (getTime() < endTime) {
        int16_t maxScore;
        if (board.sideToMove()) {
            maxScore = 32767;
        } else {
            maxScore = -32767;
        }
        for (const auto &move : moves) {
            board.makeMove(move);
            // Find pair where move is the first element in the pair
            auto it = std::find_if(scores.begin(), scores.end(), [move](const std::pair<chess::Move, int16_t> &pair) {
                return pair.first == move;
            });
            std::pair<int16_t, bool> re;
            if (!board.sideToMove()) {
                if (maxScore > 0 && it->second > abs(maxScore * 2)) {
                    re = minimaxTTWD(board, count - 1, endTime, -32767, 32767, count - 1);
                }
                else {
                    re = minimaxTTWD(board, count, endTime, -32767, 32767, count);
                }
            }
            else {
                if (maxScore > 0 && it->second < -abs(maxScore * 2)) {
                    re = minimaxTTWD(board, count - 1, endTime, -32767, 32767, count - 1);
                }
                else {
                    re = minimaxTTWD(board, count, endTime, -32767, 32767, count);
                }
            }
            if (!re.second) {
                if (it != scores.end()) {
                    it->second = re.first;
                }
            }
            if (!board.sideToMove()) {
                maxScore = std::min(maxScore, re.first);
            } else {
                maxScore = std::max(maxScore, re.first);
            }
            board.unmakeMove(move);
        }
        count++;
    }
    transpositionTableWD.clear();
    if (board.sideToMove()) {
        std::sort(scores.begin(), scores.end(), [](const std::pair<chess::Move, int16_t> &a, const std::pair<chess::Move, int16_t> &b) {
            return a.second < b.second;
        });
    } else {
        std::sort(scores.begin(), scores.end(), [](const std::pair<chess::Move, int16_t> &a, const std::pair<chess::Move, int16_t> &b) {
            return a.second > b.second;
        });
    }
    return scores[0].first;
}

int main() {
    chess::Board board;
    std::string line;

    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string token;
        iss >> token;

        if (token == "uci") {
            std::cout << "id name BotTTWD\n";
            std::cout << "id author Patrick\n";
            std::cout << "uciok\n" << std::flush;
        } else if (token == "isready") {
            std::cout << "readyok\n" << std::flush;
        } else if (token == "ucinewgame") {
            transpositionTableM3.clear();
            transpositionTableWD.clear();
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

            chess::Move bestMove = searchTTWD(board, timeMS);
            std::cout << "bestmove " << chess::uci::moveToUci(bestMove) << "\n" << std::flush;
        } else if (token == "quit") {
            break;
        }
    }

    return 0;
}