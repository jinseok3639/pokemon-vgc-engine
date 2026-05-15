import random
from vgc2.agent import BattlePolicy
from vgc2.battle_engine.game_state import State
from vgc2.battle_engine import BattleCommand
from vgc2.battle_engine.view import TeamView
from vgc2.battle_engine.modifiers import Stat

class MasterBattlePolicy(BattlePolicy):
    """
    Phase 4: 배틀 트리 탐색 및 자발적 교체 (The Brain)
    현재는 자발적 교체(Voluntary Switch) 휴리스틱과 단순 공격 로직을 먼저 구축합니다.
    이후 MCTS 등 고급 전수 탐색 알고리즘을 덧붙일 수 있습니다.
    """
    def decision(self, state: State, opp_view: TeamView | None = None) -> list[BattleCommand]:
        commands = []
        my_team = state.sides[0].team
        
        for i, pkm in enumerate(my_team.active):
            if pkm is None or pkm.fainted():
                commands.append(BattleCommand()) # 할 수 있는 행동 없음
                continue
                
            # [자발적 교체 판단 로직]
            # HP가 최대 체력의 30% 이하로 떨어지면 생존을 위해 후위와 교체 시도
            max_hp = pkm.constants.stats[Stat.MAX_HP]
            if (pkm.hp / max_hp) < 0.3:
                switch_idx = -1
                for j, reserve in enumerate(my_team.reserve):
                    if reserve.hp > 0:
                        switch_idx = j
                        break
                
                if switch_idx != -1:
                    # 교체 커맨드 생성: (-1, 대기열 인덱스)
                    commands.append((-1, switch_idx))
                    continue
            
            # [공격 판단 로직]
            # 사용 가능한 기술 중 데미지가 가장 셀 것으로 기대되는 기술을 단순 선택 (현재는 랜덤)
            valid_moves = []
            for m_idx, move in enumerate(pkm.battling_moves):
                if not move.disabled and move.pp > 0:
                    valid_moves.append(m_idx)
            
            if valid_moves:
                # Todo: 여기서 MCTS나 예상 데미지 기반의 스마트 타겟팅 도입
                chosen_move = valid_moves[0] 
                # 공격 커맨드 생성: (기술 인덱스, 타겟 인덱스). 타겟은 임의로 0번
                commands.append((chosen_move, 0))
            else:
                # 발버둥 또는 디폴트
                commands.append((0, 0))
                
        return commands
