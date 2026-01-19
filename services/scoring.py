"""Scoring service - Calculate pick'em standings."""
from datetime import datetime


class ScoringService:
    """Service for calculating pick'em standings."""

    def __init__(self, db_module):
        self.db = db_module

    def calculate_standings(self, tournament_id: int):
        """Calculate and save pick'em standings for a tournament.

        Scoring rules:
        - Each user picks 4 golfers (one per tier)
        - Score = golfer's score against par (e.g., -8, +2)
        - Only best 2 scores count (lowest/most under par)
        - Missed cut = excluded from best 2
        - Lowest total wins
        """
        # Get all picks for tournament
        picks = [p for p in self.db.picks() if p.tournament_id == tournament_id]

        # Get results - keyed by golfer_id
        results = {r.golfer_id: r for r in self.db.tournament_results()
                   if r.tournament_id == tournament_id}

        standings = []
        for pick in picks:
            # Get entry_number (default to 1 for legacy picks)
            entry_number = getattr(pick, 'entry_number', 1) or 1

            # Get score against par for each tier
            scores = []
            tier_scores = {}

            for tier in [1, 2, 3, 4]:
                golfer_id = getattr(pick, f'tier{tier}_golfer_id')
                if golfer_id and golfer_id in results:
                    result = results[golfer_id]
                    # Only count if not missed cut/WD/DQ
                    if result.status == 'active' or result.status == 'finished':
                        score = result.score_to_par
                        tier_scores[tier] = score
                        if score is not None:
                            scores.append(score)
                    else:
                        # Missed cut, WD, DQ - mark as None
                        tier_scores[tier] = None
                else:
                    tier_scores[tier] = None

            # Calculate best 2 (lowest scores)
            # Need at least 2 valid scores, otherwise entry is DQ
            if len(scores) >= 2:
                best_two = sorted(scores)[:2]
                total = sum(best_two)
            else:
                # Less than 2 valid picks = DQ (disqualified)
                total = None

            standings.append({
                'user_id': pick.user_id,
                'tournament_id': tournament_id,
                'entry_number': entry_number,
                'tier1_score': tier_scores.get(1),
                'tier2_score': tier_scores.get(2),
                'tier3_score': tier_scores.get(3),
                'tier4_score': tier_scores.get(4),
                'best_two_total': total,
            })

        # Sort by total (lowest is best, like golf). DQ entries (None) go to bottom.
        standings.sort(key=lambda x: (x['best_two_total'] is None, x['best_two_total'] or 0))

        for i, s in enumerate(standings):
            s['rank'] = i + 1

            # Upsert to database - keyed by (tournament_id, user_id, entry_number)
            # Note: We're storing scores in the "position" columns for now
            existing = [ps for ps in self.db.pickem_standings()
                        if ps.tournament_id == tournament_id
                        and ps.user_id == s['user_id']
                        and (getattr(ps, 'entry_number', 1) or 1) == s['entry_number']]

            if existing:
                self.db.pickem_standings.update(
                    id=existing[0].id,
                    entry_number=s['entry_number'],
                    tier1_position=s['tier1_score'],
                    tier2_position=s['tier2_score'],
                    tier3_position=s['tier3_score'],
                    tier4_position=s['tier4_score'],
                    best_two_total=s['best_two_total'],
                    rank=s['rank'],
                    updated_at=datetime.now().isoformat()
                )
            else:
                self.db.pickem_standings.insert(
                    tournament_id=tournament_id,
                    user_id=s['user_id'],
                    entry_number=s['entry_number'],
                    tier1_position=s['tier1_score'],
                    tier2_position=s['tier2_score'],
                    tier3_position=s['tier3_score'],
                    tier4_position=s['tier4_score'],
                    best_two_total=s['best_two_total'],
                    rank=s['rank'],
                    updated_at=datetime.now().isoformat()
                )

        return standings
