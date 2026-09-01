from app.scoring.since import rank_score


def test_ranking_close_first_external_beats_lone_push():
    winner = rank_score(significance=12, is_close=True, first_external=True, kind="first_external")
    loser = rank_score(significance=1, is_close=False, kind="high_significance")
    assert winner > loser


def test_tech_first_seen_bonus():
    assert rank_score(significance=0, is_close=False, tech_first_seen=True) == 15
