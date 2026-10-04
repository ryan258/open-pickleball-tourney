from collections import Counter
from unittest import TestCase
from tourney.engine import round_robin, elimination_graph, validate_games, DomainError, rank_round_robin

class EngineTests(TestCase):
    def test_round_robin_pairs_2_to_16(self):
        for n in range(2, 17):
            rounds = round_robin(range(n))
            pairs = [tuple(sorted(pair)) for rnd in rounds for pair in rnd]
            self.assertEqual(len(pairs), n*(n-1)//2)
            self.assertEqual(len(set(pairs)), len(pairs))
            for rnd in rounds:
                people = [p for pair in rnd for p in pair]
                self.assertEqual(len(set(people)), len(people))

    def test_elimination_and_double_elimination_losses_2_to_16(self):
        for n in range(2, 17):
            for double in (False, True):
                for choose_b in (False, True):
                    graph = elimination_graph(list(range(1,n+1)), double=double)
                    finished, losses, played = [], Counter(), 0
                    for node in graph:
                        sides = []
                        for key in ("a", "b"):
                            value = node[key]
                            if isinstance(value, tuple):
                                value = finished[value[0]][0 if value[1] == "winner" else 1]
                            sides.append(value)
                        a,b = sides
                        if node["stage"] == "reset" and not choose_b:
                            finished.append((None,None)); continue
                        if a and b:
                            self.assertNotEqual(a,b)
                            self.assertLess(losses[a], 2 if double else 1)
                            self.assertLess(losses[b], 2 if double else 1)
                            winner, loser = (b,a) if choose_b else (a,b)
                            losses[loser] += 1; played += 1
                            finished.append((winner,loser))
                        else:
                            finished.append((a or b,None))
                    self.assertEqual(played, 2*n-1 if double and choose_b else 2*n-2 if double else n-1)
                    self.assertEqual(sum(count < (2 if double else 1) for count in [losses[x] for x in range(1,n+1)]), 1)

    def test_scoring_completed_and_incomplete(self):
        self.assertEqual(validate_games([[11,9]]), "a")
        self.assertEqual(validate_games([[15,17]], 15), "b")
        self.assertEqual(validate_games([], outcome="retirement", winner="b", incomplete_game=[4,3]), "b")
        for games in ([[11,10]], [[12,9]], [[11,9],[11,7]], [[True,0]], [[-1,11]]):
            with self.assertRaises(DomainError): validate_games(games)
        with self.assertRaises(DomainError): validate_games([], outcome="retirement", winner="a", incomplete_game=[11,9])
        with self.assertRaises(DomainError): validate_games([[11,9]], incomplete_game=[1,2])

    def test_three_way_tie_is_stable_and_explained(self):
        entries = [{"id": str(i), "label": str(i), "seed": i} for i in range(1,4)]
        results = [{"a": a, "b": b, "winner": a, "outcome": "played", "games": [[11,9]]} for a,b in [("1","2"),("2","3"),("3","1")]]
        rows = rank_round_robin(entries,results)
        self.assertEqual([r["id"] for r in rows], ["1","2","3"])
        self.assertEqual({r["tie_break"] for r in rows}, {"Published seed"})
