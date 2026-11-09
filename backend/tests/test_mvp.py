EMBIID = 203954


def test_overview(get_json):
    overview = get_json("/mvp")
    assert overview["total"] == len(overview["seasons"]) == 26
    assert overview["correct"] == sum(s["correct"] for s in overview["seasons"])
    assert overview["correct"] <= overview["top3"] <= overview["total"]
    assert sum(e["seasons"] for e in overview["eras"]) == overview["total"]
    assert sum(e["correct"] for e in overview["eras"]) == overview["correct"]

    # Matches the headline number in /meta.
    assert get_json("/meta")["mvp_model"]["correct"] == overview["correct"]

    for season in overview["seasons"]:
        assert season["correct"] == (season["predicted"]["id"] == season["actual"]["id"])
        assert season["correct"] == (season["actual_rank"] == 1)


def test_race(get_json):
    race = get_json("/mvp/2022-23", limit=50)
    candidates = race["candidates"]
    assert len(candidates) >= 5
    assert [c["rank"] for c in candidates] == list(range(1, len(candidates) + 1))
    assert len(get_json("/mvp/2022-23", limit=3)["candidates"]) == 3
    assert [c["model_score"] for c in candidates] == sorted((c["model_score"] for c in candidates), reverse=True)

    winners = [c for c in candidates if c["is_mvp"]]
    assert [w["player"]["id"] for w in winners] == [EMBIID]
    assert winners[0]["rank"] == race["actual_rank"]
    assert race["correct"] == (race["actual_rank"] == 1)


def test_race_score_shares_sum_to_one(get_json):
    candidates = get_json("/mvp/2015-16", limit=50)["candidates"]
    assert abs(sum(c["score_share"] for c in candidates) - 1) < 1e-4  # shares are stored rounded


def test_race_errors(get_json):
    get_json("/mvp/1990-91", status=404)
    get_json("/mvp/2022", status=422)
    get_json("/mvp/2022-23", status=422, limit=0)
    get_json("/mvp/2022-23", status=422, limit=51)
