import pytest
from state import GameState

@pytest.fixture
def game():
    g = GameState()
    # 30個のダミーキーワードをプールに追加
    keywords = [f"kw_{i}" for i in range(30)]
    g.load_keywords(keywords)
    g.start_game()
    return g

def test_add_participant_success(game):
    """正常系: 参加者追加とカード生成"""
    p = game.add_participant(12345, ["kw_1", "kw_2", "kw_3", "kw_4"])
    assert p.user_id == 12345
    assert len(p.card_keywords) == 5
    assert len(p.card_keywords[0]) == 5
    assert p.card_keywords[2][2] == "FREE"

def test_add_participant_invalid_keyword(game):
    """セキュリティ/異常系: プールに存在しないキーワードの拒否"""
    with pytest.raises(ValueError, match="無効なキーワードが含まれています"):
        game.add_participant(12345, ["invalid_kw"])

def test_add_participant_duplicate_keyword(game):
    """セキュリティ/異常系: 重複したキーワードの拒否"""
    with pytest.raises(ValueError, match="キーワードが重複しています"):
        game.add_participant(12345, ["kw_1", "kw_1"])

def test_add_participant_too_many_keywords(game):
    """セキュリティ/異常系: キーワード上限数超えの拒否"""
    too_many = [f"kw_{i}" for i in range(25)]
    with pytest.raises(ValueError, match="選択できるキーワード数が上限を超えています"):
        game.add_participant(12345, too_many)

def test_add_participant_already_exists(game):
    """異常系: すでに参加済みのユーザー"""
    game.add_participant(12345)
    with pytest.raises(ValueError, match="既にビンゴカードを発行済みです"):
        game.add_participant(12345)

def test_draw_keyword(game):
    """正常系: キーワードの抽選"""
    kw = game.draw_keyword()
    assert kw in game.keywords_pool
    assert kw in game.drawn_keywords
    
    # 全部引いた後のエラーテスト
    for _ in range(29): # 残り29個
        game.draw_keyword()
        
    with pytest.raises(ValueError, match="すべてのキーワードが引かれました"):
        game.draw_keyword()

def test_reach_and_bingo(game):
    """正常系: リーチとビンゴの判定"""
    p = game.add_participant(123)
    
    # 意図的に1行目(インデックス0)の5つの単語を引くシミュレーション
    target_row = p.card_keywords[0]
    
    # 3つ当てる
    for i in range(3):
        p.mark_keyword(target_row[i])
        new_reach, new_bingo = p.check_reach_bingo()
        assert not new_reach
        assert not new_bingo

    # 4つ当てる（リーチ）
    p.mark_keyword(target_row[3])
    new_reach, new_bingo = p.check_reach_bingo()
    assert new_reach
    assert not new_bingo
    
    # 再度チェックしても新規リーチにならないこと
    new_reach, new_bingo = p.check_reach_bingo()
    assert not new_reach

    # 5つ当てる（ビンゴ）
    p.mark_keyword(target_row[4])
    new_reach, new_bingo = p.check_reach_bingo()
    assert not new_reach  # ビンゴ成立時はリーチはFalseになる仕様
    assert new_bingo

def test_evaluate_draw(game):
    """正常系: 全体の抽選評価"""
    p1 = game.add_participant(1)
    p2 = game.add_participant(2)
    
    # 共通して持っている単語を探す
    # ただしランダムなので、確実にヒットさせるために直接カードを操作
    shared_word = p1.card_keywords[0][0]
    p2.card_keywords[0][0] = shared_word
    
    matched, reached, bingos = game.evaluate_draw(shared_word)
    assert p1 in matched
    assert p2 in matched
    assert len(reached) == 0
    assert len(bingos) == 0
