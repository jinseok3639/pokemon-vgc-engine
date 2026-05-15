from vgc2.agent import TeamBuildPolicy, TeamBuildCommand
from vgc2.balance.meta import Meta, Roster
from vgc2.battle_engine.modifiers import Stats, Nature, Stat, Category

class MasterTeamBuildPolicy(TeamBuildPolicy):
    """
    Phase 2: 완벽한 팀 빌더 (The Perfect Builder)
    포켓몬의 종족값을 분석하여 물리/특수 스위퍼 역할을 배정하고 EV를 최적 분배합니다.
    """
    def decision(self, roster: Roster, meta: Meta | None, max_team_size: int, max_pkm_moves: int, n_active: int) -> TeamBuildCommand:
        team = []
        # 종족값 총합(BST) 기준으로 상위 포켓몬을 선별합니다.
        sorted_roster = sorted(roster.pkm_list, key=lambda p: sum(p.base_stats), reverse=True)
        
        for pkm in sorted_roster[:max_team_size]:
            atk = pkm.base_stats[Stat.ATTACK]
            spa = pkm.base_stats[Stat.SPECIAL_ATTACK]
            
            evs = [0] * 6
            ivs = [31] * 6
            
            # 내구를 위해 HP에 풀투자
            evs[Stat.MAX_HP] = 252 
            evs[Stat.SPEED] = 4
            
            if atk > spa:
                # 물리 어태커 세팅
                evs[Stat.ATTACK] = 252
                nature = Nature.ADAMANT # +Atk -SpA
                
                # 물리형 기술 또는 변화기 위주로 선택
                moves = []
                for i, move in enumerate(pkm.moves):
                    if move.category == Category.PHYSICAL or move.power == 0:
                        moves.append(i)
                moves = moves[:max_pkm_moves]
                
                # 부족하면 남은 기술로 채움
                if len(moves) < max_pkm_moves:
                    for i in range(len(pkm.moves)):
                        if i not in moves:
                            moves.append(i)
                        if len(moves) == max_pkm_moves:
                            break
            else:
                # 특수 어태커 세팅
                evs[Stat.SPECIAL_ATTACK] = 252
                nature = Nature.MODEST # +SpA -Atk
                
                # 특수형 기술 또는 변화기 위주로 선택
                moves = []
                for i, move in enumerate(pkm.moves):
                    if move.category == Category.SPECIAL or move.power == 0:
                        moves.append(i)
                moves = moves[:max_pkm_moves]
                
                if len(moves) < max_pkm_moves:
                    for i in range(len(pkm.moves)):
                        if i not in moves:
                            moves.append(i)
                        if len(moves) == max_pkm_moves:
                            break
            
            team.append((pkm.id, tuple(evs), tuple(ivs), nature, moves))
            
        return team
