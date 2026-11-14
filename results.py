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


def GetAvailableOpponents() -> list[str]:
    """Returns ['All Opponents', 'Perft', ...sorted unique opponent names]."""
    EnsureResultsDir()
    opponents: set[str] = set()

    for entry in os.listdir(ResultsDirectory):
        if not entry.endswith(".json"):
            continue
        botName = os.path.splitext(entry)[0]
        data = LoadBotData(botName)
        opponents.add(data.get("botName", botName))
        for match in data.get("matches", []):
            opp = match.get("opponent")
            if opp:
                opponents.add(opp)

    return ["All Opponents", "Perft"] + sorted(opponents)


def GetLeaderboardSummary(opponentFilter: str = "All Opponents") -> list[dict]:
    """
    Aggregates W/D/L stats (optionally filtered to a single opponent)
    or Perft benchmark stats when opponentFilter == 'Perft'.
    """
    EnsureResultsDir()
    leaderboard: list[dict] = []

    for entry in sorted(os.listdir(ResultsDirectory)):
        if not entry.endswith(".json"):
            continue
        botName = os.path.splitext(entry)[0]
        data = LoadBotData(botName)
        displayName = data.get("botName", botName)

        if opponentFilter == "Perft":
            perftRuns = data.get("perft", [])
            if not perftRuns:
                continue
            bestRun = max(perftRuns, key=lambda p: (p.get("depth", 0), p.get("nps", 0)))
            bestNps = max((p.get("nps", 0) for p in perftRuns), default=0)
            leaderboard.append(
                {
                    "botName": displayName,
                    "runs": len(perftRuns),
                    "maxDepth": bestRun.get("depth", 0),
                    "nodes": bestRun.get("nodes", 0),
                    "timeSeconds": bestRun.get("timeSeconds", 0.0),
                    "bestPerftNps": bestNps,
                }
            )
        else:
            if displayName == opponentFilter:
                continue

            matches = data.get("matches", [])
            if opponentFilter != "All Opponents":
                matches = [m for m in matches if m.get("opponent") == opponentFilter]

            wins = sum(1 for m in matches if m.get("result") == "win")
            draws = sum(1 for m in matches if m.get("result") == "draw")
            losses = sum(1 for m in matches if m.get("result") == "loss")
            total = len(matches)
            score = wins + 0.5 * draws
            winRate = (score / total * 100.0) if total > 0 else 0.0

            leaderboard.append(
                {
                    "botName": displayName,
                    "games": total,
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "score": score,
                    "winRate": round(winRate, 1),
                }
            )

    if opponentFilter == "Perft":
        leaderboard.sort(key=lambda row: (row["maxDepth"], row["bestPerftNps"]), reverse=True)
    else:
        leaderboard.sort(key=lambda row: (row["score"], row["winRate"], row["games"]), reverse=True)

    return leaderboard