import os
import json
import math
from datetime import datetime, timezone
from typing import Optional
import chess

ResultsDirectory = os.path.join(os.path.dirname(__file__), "results")
AnchorBotName = "minimax"
AnchorBotRating = 100

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

def ComputePoolElos(
    allBotData: dict[str, dict],
    anchorBot: str = AnchorBotName,
    anchorRating: float = AnchorBotRating,
) -> dict[str, int]:
    """
    Computes global Maximum Likelihood (Ordo-style) Elo ratings across all bots
    using pairwise match results.
    """
    bots = sorted(allBotData.keys())
    if not bots:
        return {}

    if anchorBot not in allBotData:
        anchorBot = bots[0]

    # Aggregate pairwise wins, draws, losses (deduplicated from each bot's perspective)
    pairStats: dict[tuple[str, str], list[float]] = {}
    for botA, data in allBotData.items():
        for m in data.get("matches", []):
            botB = m.get("opponent")
            if not botB or botB == "Human" or botB not in allBotData or botB == botA:
                continue
            res = m.get("result")
            key = (botA, botB)
            if key not in pairStats:
                pairStats[key] = [0.0, 0.0]  # [points_for_A, total_games]
            if res == "win":
                pairStats[key][0] += 1.0
            elif res == "draw":
                pairStats[key][0] += 0.5
            pairStats[key][1] += 1.0

    # Ensure symmetry (average A->B and B->A in case only one side recorded a game)
    symmetricPairs: list[tuple[str, str, float, float]] = []
    visited: set[tuple[str, str]] = set()
    for (a, b), (ptsAB, gamesAB) in pairStats.items():
        if (a, b) in visited or (b, a) in visited:
            continue
        visited.add((a, b))
        ptsBA, gamesBA = pairStats.get((b, a), [0.0, 0.0])
        if gamesBA > 0:
            totalGames = 0.5 * (gamesAB + gamesBA)
            ptsA = 0.5 * (ptsAB + (gamesBA - ptsBA))
        else:
            totalGames = gamesAB
            ptsA = ptsAB

        # Laplace smoothing (+0.5 draw) prevents infinite Elo on 100% / 0% scores
        symmetricPairs.append((a, b, ptsA + 0.5, totalGames + 1.0))

    ratings = {b: anchorRating for b in bots}
    scale = math.log(10.0) / 400.0

    # Gradient ascent on logistic log-likelihood
    for _ in range(400):
        grads = {b: 0.0 for b in bots}
        maxStep = 0.0

        for a, b, ptsA, nGames in symmetricPairs:
            diff = (ratings[a] - ratings[b]) * scale
            expectedA = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, diff))))
            grad = (ptsA - nGames * expectedA) * scale
            grads[a] += grad
            grads[b] -= grad

        for b in bots:
            if b == anchorBot:
                continue
            step = grads[b] * 2500.0
            step = max(-50.0, min(50.0, step))
            ratings[b] += step
            maxStep = max(maxStep, abs(step))

        if maxStep < 0.01:
            break

    return {b: round(r) for b, r in ratings.items()}

def GetLeaderboardSummary(opponentFilter: str = "All Opponents") -> list[dict]:
    """
    Aggregates W/D/L stats and global pool Elo ratings (optionally filtered
    to a single opponent) or Perft benchmark stats when opponentFilter == 'Perft'.
    """
    EnsureResultsDir()
    leaderboard: list[dict] = []
    allBotData: dict[str, dict] = {}

    for entry in sorted(os.listdir(ResultsDirectory)):
        if not entry.endswith(".json"):
            continue
        botName = os.path.splitext(entry)[0]
        data = LoadBotData(botName)
        displayName = data.get("botName", botName)
        allBotData[displayName] = data

    poolElos = ComputePoolElos(allBotData) if opponentFilter != "Perft" else {}

    for displayName, data in allBotData.items():
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
                    "elo": poolElos.get(displayName, round(AnchorBotRating)),
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
        leaderboard.sort(key=lambda row: (row["elo"], row["winRate"], row["games"]), reverse=True)

    return leaderboard