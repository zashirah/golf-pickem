-- Season standings view for aggregating season-long statistics
-- Run this manually in Supabase SQL editor

DROP VIEW IF EXISTS season_standings_view;

CREATE VIEW season_standings_view AS
SELECT
    EXTRACT(YEAR FROM t.start_date::date)::text as season_year,
    u.id as user_id,
    u.display_name,

    -- Core stats
    COUNT(DISTINCT ps.tournament_id) as tournaments_played,
    COUNT(ps.id) as total_entries,
    SUM(CASE WHEN ps.best_two_total IS NOT NULL THEN ps.best_two_total ELSE 0 END) as total_score,
    AVG(CASE WHEN ps.best_two_total IS NOT NULL THEN ps.best_two_total ELSE NULL END) as average_score,

    -- Finish counts
    SUM(CASE WHEN ps.rank = 1 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN ps.rank <= 3 THEN 1 ELSE 0 END) as top3_finishes,
    SUM(CASE WHEN ps.rank <= 5 THEN 1 ELSE 0 END) as top5_finishes,
    SUM(CASE WHEN ps.rank <= 10 THEN 1 ELSE 0 END) as top10_finishes,

    -- Performance metrics
    AVG(CAST(ps.rank AS DECIMAL)) as average_position,
    MIN(ps.rank) as best_finish,

    -- Winnings (sum of purses for tournaments won)
    SUM(
        CASE WHEN ps.rank = 1 AND t.entry_price IS NOT NULL
        THEN t.entry_price * (SELECT COUNT(*) FROM pick WHERE tournament_id = t.id)
        ELSE 0 END
    ) as total_winnings

FROM "user" u
JOIN pickem_standing ps ON u.id = ps.user_id
JOIN tournament t ON ps.tournament_id = t.id
WHERE t.status = 'completed'
  AND ps.best_two_total IS NOT NULL
GROUP BY EXTRACT(YEAR FROM t.start_date::date), u.id, u.display_name
ORDER BY AVG(CASE WHEN ps.best_two_total IS NOT NULL THEN ps.best_two_total ELSE NULL END) ASC;
