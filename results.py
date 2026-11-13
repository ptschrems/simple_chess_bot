import os
import json
from datetime import datetime, timezone
from typing import Optional
import chess


ResultsDirectory = os.path.join(os.path.dirname(__file__), "results")


def EnsureResultsDir() -> None:
    os.makedirs(ResultsDirectory, exist_ok=True)


def GetBotResultPath(botName: str) -> str:
    safeName = "".join(c for c in botName if c.isalnum() or c in ("_", "-", "."))
    return os.path.join(ResultsDirectory, f"{safeName}.json")


def LoadBotData(botName: str) -> dict:
    EnsureResultsDir()
    path = GetBotResultPath(botName)
    if not os.path.isfile(path):
        return {
            "botName": botName,
            "matches": [],
            "perft": [],
        }

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            data.setdefault("botName", botName)
            data.setdefault("matches", [])
            data.setdefault("perft", [])
            return data
    except (json.JSONDecodeError, OSError):
        return {
            "botName": botName,
            "matches": [],
            "perft": [],
        }


def SaveBotData(botName: str, data: dict) -> None:
    EnsureResultsDir()
    path = GetBotResultPath(botName)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def RecordMatchResult(
    whiteBot: str,
    blackBot: str,
    startFen: str,
    winner: Optional[chess.Color],
    reason: str,
    timeControl: str,
    plyCount: int,
) -> None:
    """
    Saves match results into both White's and Black's result files
    (skipping 'Human' if a human was playing).
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if winner == chess.WHITE:
        whiteOutcome, blackOutcome = "win", "loss"
    elif winner == chess.BLACK:
        whiteOutcome, blackOutcome = "loss", "win"
    else:
        whiteOutcome, blackOutcome = "draw", "draw"

    if whiteBot != "Human":
        whiteData = LoadBotData(whiteBot)
        whiteData["matches"].append(
            {
                "timestamp": timestamp,
                "opponent": blackBot,
                "color": "white",
                "startFen": startFen,
                "result": whiteOutcome,
                "reason": reason,
                "timeControl": timeControl,
                "plies": plyCount,
            }
        )
        SaveBotData(whiteBot, whiteData)

    if blackBot != "Human":
        blackData = LoadBotData(blackBot)
        blackData["matches"].append(
            {
                "timestamp": timestamp,
                "opponent": whiteBot,
                "color": "black",
                "startFen": startFen,
                "result": blackOutcome,
                "reason": reason,
                "timeControl": timeControl,
                "plies": plyCount,
            }
        )
        SaveBotData(blackBot, blackData)


def RecordPerftResult(
    botName: str,
    startFen: str,
    depth: int,
    nodes: int,
    timeSeconds: float,
) -> None:
    """
    Saves a perft benchmark entry (nodes at final depth & elapsed time)
    into the specified bot's result file.
    """
    if botName == "Human":
        return

    nps = int(nodes / timeSeconds) if timeSeconds > 0 else 0
    botData = LoadBotData(botName)
    botData["perft"].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "startFen": startFen,
            "depth": depth,
            "nodes": nodes,
            "timeSeconds": round(timeSeconds, 6),
            "nps": nps,
        }
    )
    SaveBotData(botName, botData)


def GetLeaderboardSummary() -> list[dict]:
    """
    Aggregates W/L/D stats, win rate, and best perft NPS across all bot files
    so a future leaderboard UI can render them directly.
    """
    EnsureResultsDir()
    leaderboard: list[dict] = []

    for entry in sorted(os.listdir(ResultsDirectory)):
        if not entry.endswith(".json"):
            continue
        botName = os.path.splitext(entry)[0]
        data = LoadBotData(botName)
        matches = data.get("matches", [])
        perftRuns = data.get("perft", [])

        wins = sum(1 for m in matches if m.get("result") == "win")
        losses = sum(1 for m in matches if m.get("result") == "loss")
        draws = sum(1 for m in matches if m.get("result") == "draw")
        total = len(matches)
        score = wins + 0.5 * draws
        winRate = (score / total * 100.0) if total > 0 else 0.0

        bestNps = max((p.get("nps", 0) for p in perftRuns), default=0)

        leaderboard.append(
            {
                "botName": data.get("botName", botName),
                "games": total,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "score": score,
                "winRate": round(winRate, 1),
                "bestPerftNps": bestNps,
            }
        )

    leaderboard.sort(key=lambda row: (row["score"], row["winRate"], row["bestPerftNps"]), reverse=True)
    return leaderboard