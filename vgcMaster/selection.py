from vgc2.agent import SelectionPolicy, SelectionCommand
from vgc2.battle_engine.team import Team

class MasterSelectionPolicy(SelectionPolicy):
    """
    Phase 3: 공방 순효과 기반 선출 정책 (Smart Selection)
    상대 파티를 분석하여 가장 유리한 포켓몬을 선출합니다. 
    우선은 단순 선출을 구현하고 차후 데미지 계산식 연동으로 고도화합니다.
    """
    def decision(self, teams: tuple[Team, Team], max_size: int) -> SelectionCommand:
        my_team = teams[0]
        opp_team = teams[1]
        
        # Todo: "내가 줄 데미지 - 내가 받을 데미지" 계산 로직 추가
        # 현재는 BST(TeamBuilder에서 정렬된 상태)가 높은 순서대로 가장 강력한 픽을 가져감
        return list(range(max_size))
