"""Deterministic tournament functions. No database, network, or wall-clock access."""
from collections import defaultdict


class DomainError(Exception):
    def __init__(self, message, code="invalid", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def round_robin(entries):
    entries = list(entries)
    if not 2 <= len(entries) <= 16:
        raise DomainError("A round robin needs 2–16 entries.")
    if len(entries) % 2:
        entries.append(None)
    rounds = []
    for _ in range(len(entries) - 1):
        rounds.append([(entries[i], entries[-1-i]) for i in range(len(entries)//2)
                       if entries[i] is not None and entries[-1-i] is not None])
        entries = [entries[0], entries[-1], *entries[1:-1]]
    return rounds


def seed_positions(count):
    if not 2 <= count <= 16:
        raise DomainError("An elimination draw needs 2–16 entries.")
    slots = [1, 2]
    while len(slots) < count:
        size = len(slots) * 2
        slots = [x for seed in slots for x in (seed, size+1-seed)]
    return slots


def elimination_graph(entries, double=False):
    """Nodes use entry IDs or (earlier node index, 'winner'/'loser') slots."""
    entries = list(entries)
    positions = seed_positions(len(entries))
    slots = [entries[p-1] if p <= len(entries) else None for p in positions]
    nodes, winners = [], []

    def add(a, b, stage, round_number):
        nodes.append({"a": a, "b": b, "stage": stage, "round": round_number})
        return len(nodes)-1

    current = [add(slots[i], slots[i+1], "winners", 1) for i in range(0, len(slots), 2)]
    winners.append(current)
    round_number = 2
    while len(current) > 1:
        current = [add((current[i], "winner"), (current[i+1], "winner"), "winners", round_number)
                   for i in range(0, len(current), 2)]
        winners.append(current)
        round_number += 1
    if double:
        if len(winners[0]) == 1:
            loser_slot = (winners[0][0], "loser")
        else:
            current = [add((winners[0][i], "loser"), (winners[0][i+1], "loser"), "losers", 1)
                       for i in range(0, len(winners[0]), 2)]
            lr = 2
            for wi in range(1, len(winners)):
                opponents = list(reversed(winners[wi]))
                current = [add((m, "winner"), (opponents[i], "loser"), "losers", lr)
                           for i, m in enumerate(current)]
                lr += 1
                if wi < len(winners)-1:
                    current = [add((current[i], "winner"), (current[i+1], "winner"), "losers", lr)
                               for i in range(0, len(current), 2)]
                    lr += 1
            loser_slot = (current[0], "winner")
        final = add((winners[-1][0], "winner"), loser_slot, "final", 1)
        add((final, "winner"), (final, "loser"), "reset", 2)
    return nodes


def snake_pools(entries, count):
    if not 2 <= count <= 8 or len(entries) < 2*count:
        raise DomainError("Choose at least two entries per pool and 2–8 pools.")
    pools = [[] for _ in range(count)]
    for i, entry in enumerate(entries):
        group, column = divmod(i, count)
        pools[column if group % 2 == 0 else count-1-column].append(entry)
    return pools


def validate_games(games, target=11, best_of=1, outcome="played", winner=None, incomplete_game=None):
    if target not in (11, 15, 21) or best_of not in (1, 3):
        raise DomainError("This scoring profile is not supported.")
    if outcome not in ("played", "retirement", "walkover", "disqualification", "void"):
        raise DomainError("Choose a supported match outcome.")
    if not isinstance(games, list) or len(games) > best_of:
        raise DomainError("Too many games for this match.")
    if incomplete_game is not None:
        if outcome not in ("retirement", "disqualification") or not isinstance(incomplete_game, list) or len(incomplete_game) != 2 or any(type(x) is not int or x < 0 or x > 999 for x in incomplete_game):
            raise DomainError("Incomplete game scores are only available for retirement or disqualification.")
        high, low = max(incomplete_game), min(incomplete_game)
        if high >= target and high-low >= 2:
            raise DomainError("This game is already complete; enter it under completed games.")
        if len(games) >= best_of:
            raise DomainError("There is no remaining game for an incomplete score.")
    wins = [0, 0]
    required = best_of//2+1
    for game in games:
        if max(wins) >= required:
            raise DomainError("The match already has a winner; remove the extra game.")
        if not isinstance(game, list) or len(game) != 2 or any(type(x) is not int or x < 0 for x in game):
            raise DomainError("Enter two nonnegative whole-number scores per game.")
        w, l = max(game), min(game)
        if not ((w == target and l <= target-2) or (w > target and w-l == 2)):
            raise DomainError(f"{game[0]}–{game[1]} is not a completed game to {target}, win by two.")
        wins[0 if game[0] > game[1] else 1] += 1
    if outcome == "played":
        if max(wins) != required:
            raise DomainError("Enter all games needed to decide the match.")
        return "a" if wins[0] > wins[1] else "b"
    if outcome in ("walkover", "void") and games:
        raise DomainError("Walkovers and void matches cannot contain invented completed games.")
    if outcome != "void" and winner not in ("a", "b"):
        raise DomainError("Select the winner of this administrative outcome.")
    if outcome != "played" and max(wins) >= required:
        raise DomainError("These completed games already decide the match; use a played result.")
    return winner if outcome != "void" else None


def rank_round_robin(entries, results):
    """entries: id,label,seed; results: a,b,winner,outcome,games."""
    table = {e["id"]: {**e, "wins": 0, "losses": 0, "played": 0, "points_for": 0,
                       "points_against": 0, "differential": 0, "tie_break": "Match wins"} for e in entries}
    for r in results:
        if r["a"] not in table or r["b"] not in table or not r.get("winner"):
            continue
        a, b = table[r["a"]], table[r["b"]]
        for row in (a, b):
            row["played"] += 1
            row["wins" if row["id"] == r["winner"] else "losses"] += 1
        if r["outcome"] == "played":
            pa = sum(g[0] for g in r["games"])
            pb = sum(g[1] for g in r["games"])
            a["points_for"] += pa; a["points_against"] += pb
            b["points_for"] += pb; b["points_against"] += pa
    groups = defaultdict(list)
    for row in table.values():
        row["differential"] = row["points_for"]-row["points_against"]
        groups[row["wins"]].append(row)
    ranked = []
    for wins in sorted(groups, reverse=True):
        group = groups[wins]
        ids = {row["id"] for row in group}
        mutual = [r for r in results if r["a"] in ids and r["b"] in ids and r["outcome"] == "played"]
        head = len(mutual) == len(ids)*(len(ids)-1)//2
        for row in group:
            row["head_to_head"] = sum(r["winner"] == row["id"] for r in mutual) if head else 0
        group.sort(key=lambda r: (-r["head_to_head"], -r["differential"], -r["points_for"], r["seed"]))
        if len(group) > 1:
            for row in group:
                peers = [r for r in group if r is not row]
                criterion = "Published seed"
                for field, label in [("head_to_head", "Head-to-head wins"), ("differential", "Point differential"), ("points_for", "Points scored")]:
                    tied = [r for r in peers if r[field] == row[field]]
                    if not tied:
                        criterion = label
                        break
                    peers = tied
                row["tie_break"] = criterion
        ranked.extend(group)
    for position, row in enumerate(ranked, 1):
        row["rank"] = position
    return ranked

