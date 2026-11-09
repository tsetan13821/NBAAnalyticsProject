"""Public NBA.com CDN image URLs. The frontend shows a fallback if an image is missing."""


def headshot_url(player_id: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"


def logo_url(nba_team_id: int) -> str:
    return f"https://cdn.nba.com/logos/nba/{nba_team_id}/global/L/logo.svg"
