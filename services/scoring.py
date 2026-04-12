"""Scoring service - Calculate pick'em standings."""
from datetime import datetime
from sqlalchemy import text


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

        Tiebreaker rules (in order):
        1. Best 2 of 4 scores (lowest wins)
        2. 3rd score (if available - lower wins)
        3. 4th score (if available - lower wins)
        4. Perfect tie = same rank (split pot)
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

            # Compute tiebreaker data: 3rd and 4th best scores
            all_scores_sorted = sorted(scores)
            third_best_score = all_scores_sorted[2] if len(all_scores_sorted) >= 3 else None
            has_third_made_cut = len(all_scores_sorted) >= 3
            fourth_best_score = all_scores_sorted[3] if len(all_scores_sorted) >= 4 else None
            has_fourth_made_cut = len(all_scores_sorted) >= 4

            standings.append({
                'user_id': pick.user_id,
                'tournament_id': tournament_id,
                'entry_number': entry_number,
                'tier1_score': tier_scores.get(1),
                'tier2_score': tier_scores.get(2),
                'tier3_score': tier_scores.get(3),
                'tier4_score': tier_scores.get(4),
                'best_two_total': total,
                'third_best_score': third_best_score,
                'has_third_made_cut': has_third_made_cut,
                'fourth_best_score': fourth_best_score,
                'has_fourth_made_cut': has_fourth_made_cut,
            })

        # Sort with tiebreaker rules
        def sort_key(entry):
            """
            Multi-level sort key for tiebreaker rules.

            Order:
            1. DQ entries (< 2 valid scores) → bottom
            2. Best 2 total (ascending - lower is better)
            3. Has 3rd made cut (descending - having score beats not having)
            4. 3rd score (ascending - lower is better, only compared if both have 3rd)
            5. Has 4th made cut (descending)
            6. 4th score (ascending - lower is better, only compared if both have 4th)
            """
            is_dq = entry['best_two_total'] is None
            total = entry['best_two_total'] if not is_dq else float('inf')

            # 3rd score tiebreaker: prioritize having a score, then compare values
            has_third = entry['has_third_made_cut'] or False
            third_score = entry['third_best_score'] if has_third else float('inf')

            # 4th score tiebreaker: prioritize having a score, then compare values
            has_fourth = entry['has_fourth_made_cut'] or False
            fourth_score = entry['fourth_best_score'] if has_fourth else float('inf')

            # Return tuple: DQ flag, best 2, inverse of has_third (for desc), 3rd score, inverse of has_fourth, 4th score
            return (is_dq, total, not has_third, third_score, not has_fourth, fourth_score)

        standings.sort(key=sort_key)

        # Assign ranks with same-rank logic for perfect ties
        current_rank = 1
        prev_key = None

        now = datetime.now().isoformat()
        for i, s in enumerate(standings):
            # Comparison key (same as sort key components, but without is_dq)
            current_key = (
                s['best_two_total'],
                s['has_third_made_cut'],
                s['third_best_score'],
                s['has_fourth_made_cut'],
                s['fourth_best_score']
            )

            # If different from previous entry, update rank to current position
            if prev_key is None or current_key != prev_key:
                current_rank = i + 1

            s['rank'] = current_rank
            prev_key = current_key

        # Delete all existing standings for this tournament and bulk insert fresh ones.
        # This avoids stale duplicate rows that cause the leaderboard to show wrong scores
        # when the upsert-by-first-record pattern skips over extra copies.
        with self.db.db.engine.connect() as conn:
            conn.execute(text("DELETE FROM pickem_standing WHERE tournament_id = :tid"),
                         {"tid": tournament_id})

            if standings:
                values_list = []
                params = {}
                for i, s in enumerate(standings):
                    values_list.append(
                        f"(:tid_{i}, :uid_{i}, :en_{i}, :t1_{i}, :t2_{i}, :t3_{i}, :t4_{i}, "
                        f":bt_{i}, :rank_{i}, :t3s_{i}, :h3_{i}, :t4s_{i}, :h4_{i}, :ua_{i})"
                    )
                    params.update({
                        f"tid_{i}": tournament_id,
                        f"uid_{i}": s['user_id'],
                        f"en_{i}": s['entry_number'],
                        f"t1_{i}": s['tier1_score'],
                        f"t2_{i}": s['tier2_score'],
                        f"t3_{i}": s['tier3_score'],
                        f"t4_{i}": s['tier4_score'],
                        f"bt_{i}": s['best_two_total'],
                        f"rank_{i}": s['rank'],
                        f"t3s_{i}": s['third_best_score'],
                        f"h3_{i}": s['has_third_made_cut'],
                        f"t4s_{i}": s['fourth_best_score'],
                        f"h4_{i}": s['has_fourth_made_cut'],
                        f"ua_{i}": now,
                    })
                conn.execute(text(
                    "INSERT INTO pickem_standing "
                    "(tournament_id, user_id, entry_number, tier1_position, tier2_position, "
                    "tier3_position, tier4_position, best_two_total, rank, third_best_score, "
                    "has_third_made_cut, fourth_best_score, has_fourth_made_cut, updated_at) "
                    f"VALUES {', '.join(values_list)}"
                ), params)
            conn.commit()

        return standings
