import random
from typing import List, Dict, Optional, Tuple

class Participant:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.card_keywords: List[List[str]] = []
        self.marked: List[List[bool]] = [[False] * 5 for _ in range(5)]
        
        self.has_reach = False
        self.has_bingo = False
        
        # 通知済みかどうかのフラグ
        self.notified_reach = False
        self.notified_bingo = False

    def generate_card(self, keywords_pool: List[str], user_selected: List[str] = None):
        """
        キーワードプールからランダムに選んで5x5のカードを生成する
        user_selected: ユーザーが明示的に選んだ4つのキーワード（あれば優先して配置）
        """
        user_selected = user_selected or []
        
        # 必要な単語数は 24（中央はFREEのため）
        needed = 24 - len(user_selected)
        
        pool_without_selected = [k for k in keywords_pool if k not in user_selected]
        if len(pool_without_selected) < needed:
            raise ValueError("キーワードの数が足りません。")
            
        random_selected = random.sample(pool_without_selected, needed)
        combined = user_selected + random_selected
        random.shuffle(combined)
        
        # 5x5に配置
        self.card_keywords = [[""] * 5 for _ in range(5)]
        idx = 0
        for r in range(5):
            for c in range(5):
                if r == 2 and c == 2:
                    self.card_keywords[r][c] = "FREE"
                    self.marked[r][c] = True
                else:
                    self.card_keywords[r][c] = combined[idx]
                    idx += 1

    def mark_keyword(self, keyword: str) -> bool:
        """キーワードがカードにあればマークし、Trueを返す。なければFalse"""
        matched = False
        for r in range(5):
            for c in range(5):
                if self.card_keywords[r][c] == keyword:
                    self.marked[r][c] = True
                    matched = True
        return matched

    def check_reach_bingo(self) -> Tuple[bool, bool]:
        """
        リーチおよびビンゴが新しく成立したか判定し、状態を更新する。
        :return: (newly_reached, newly_bingo)
        """
        lines = []
        # 横
        for row in self.marked:
            lines.append(sum(row))
        # 縦
        for col in range(5):
            lines.append(sum(self.marked[row][col] for row in range(5)))
        # 斜め
        lines.append(sum(self.marked[i][i] for i in range(5)))
        lines.append(sum(self.marked[i][4-i] for i in range(5)))

        new_reach = False
        new_bingo = False

        if not self.has_bingo and any(count == 5 for count in lines):
            self.has_bingo = True
            new_bingo = True
            # ビンゴになったらリーチ通知は不要になる
            self.has_reach = True 

        if not self.has_bingo and not self.has_reach and any(count == 4 for count in lines):
            self.has_reach = True
            new_reach = True

        return new_reach, new_bingo


class GameState:
    def __init__(self):
        self.is_active = False
        self.participants: Dict[int, Participant] = {}
        self.keywords_pool: List[str] = []
        self.drawn_keywords: set = set()
        
        # 進行に使うチャンネルID
        self.admin_channel_id: Optional[int] = None
        self.participant_channel_id: Optional[int] = None
        self.stage_channel_id: Optional[int] = None

    def start_game(self):
        """ゲームを開始し、状態をリセットする"""
        if not self.keywords_pool or len(self.keywords_pool) < 25:
            raise ValueError("キーワードが設定されていないか、25個未満です。")
        self.is_active = True
        self.participants.clear()
        self.drawn_keywords.clear()

    def end_game(self):
        """ゲームを終了し、状態をクリアする"""
        self.is_active = False
        self.participants.clear()
        self.drawn_keywords.clear()
        self.keywords_pool.clear()

    def add_participant(self, user_id: int, user_selected: List[str] = None) -> Participant:
        """参加者を追加し、ビンゴカードを生成する"""
        if not self.is_active:
            raise ValueError("ビンゴ大会は現在開催されていません。")
        if user_id in self.participants:
            raise ValueError("既にビンゴカードを発行済みです。")
        
        user_selected = user_selected or []
        if not isinstance(user_selected, list):
            raise ValueError("不正なデータフォーマットです。")
            
        # 入力検証（セキュリティ/整合性チェック）
        valid_pool = [k for k in self.keywords_pool if k.upper() != "FREE"]
        valid_selected = []
        for kw in user_selected:
            if not isinstance(kw, str) or kw not in valid_pool:
                raise ValueError(f"無効なキーワードが含まれています: {kw}")
            if kw in valid_selected:
                raise ValueError("キーワードが重複しています。")
            valid_selected.append(kw)
            
        # 最大数チェック (24個まで)
        if len(valid_selected) > 24:
            raise ValueError("選択できるキーワード数が上限を超えています。")
        
        participant = Participant(user_id)
        participant.generate_card(self.keywords_pool, valid_selected)
        self.participants[user_id] = participant
        return participant

    def draw_keyword(self) -> str:
        """まだ引かれていないキーワードをランダムに1つ引き、返す"""
        if not self.is_active:
            raise ValueError("ビンゴ大会は現在開催されていません。")
        
        available = [kw for kw in self.keywords_pool if kw not in self.drawn_keywords and kw != "FREE"]
        if not available:
            raise ValueError("すべてのキーワードが引かれました。")
        
        drawn = random.choice(available)
        self.drawn_keywords.add(drawn)
        return drawn
        
    def reset_draws(self):
        """これまで引いたキーワードと、全参加者のカードのマーク（FREE以外）を初期化する"""
        if not self.is_active:
            raise ValueError("ビンゴ大会は現在開催されていません。")
            
        self.drawn_keywords.clear()
        
        for p in self.participants.values():
            p.has_reach = False
            p.has_bingo = False
            p.notified_reach = False
            p.notified_bingo = False
            # 全てのマークをクリアし、FREEだけマークし直す
            for r in range(5):
                for c in range(5):
                    if r == 2 and c == 2:
                        p.marked[r][c] = True
                    else:
                        p.marked[r][c] = False

    def evaluate_draw(self, keyword: str) -> Tuple[List[Participant], List[Participant], List[Participant]]:
        """
        全参加者のカードをチェックする
        :return: (matched_participants, reached_participants, bingo_participants)
        """
        matched_participants = []
        reached_participants = []
        bingo_participants = []

        for p in self.participants.values():
            if p.mark_keyword(keyword):
                matched_participants.append(p)
                
                new_reach, new_bingo = p.check_reach_bingo()
                if new_bingo:
                    bingo_participants.append(p)
                elif new_reach:
                    reached_participants.append(p)
                    
        return matched_participants, reached_participants, bingo_participants

    def load_keywords(self, keywords: List[str]):
        """キーワードプールを更新する"""
        if self.is_active:
            raise ValueError("ゲーム進行中はキーワードリストを変更できません。")
        self.keywords_pool = [k.strip() for k in keywords if k.strip() and k.strip().upper() != "FREE"]


# グローバルなゲーム状態のインスタンス（本来はbotの属性などに持たせる方が安全だが、単一サーバー想定という仮定で簡略化）
game = GameState()
