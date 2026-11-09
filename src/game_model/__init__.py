"""The game predictor: who wins a game, and by how much, from team strength, form, schedule and who is playing.

Modules, in pipeline order:
    seasons          season-label helpers and the configured season ranges
    fetch_games      team and player game logs from the NBA stats API (data/raw/games/)
    injury_reports   the official NBA injury reports, downloaded and parsed (data/raw/injuries/)
"""
