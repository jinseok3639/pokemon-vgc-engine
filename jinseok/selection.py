from vgc2.agent import SelectionPolicy, SelectionCommand
from vgc2.battle_engine.team import Team
from vgc2.battle_engine.modifiers import Stat
from vgc2.battle_engine.damage_calculator import type_effectiveness_modifier
from vgc2.battle_engine.constants import BattleRuleParam


class JinseokSelectionPolicy(SelectionPolicy):
    """
    타입 상성 + 종합 스탯 기반 선출 정책
    상대 팀의 타입을 분석하여 유리한 포켓몬을 우선 선출합니다.
    """

    def decision(self, teams: tuple[Team, Team], max_size: int) -> SelectionCommand:
        my_team = teams[0]
        opp_team = teams[1]
        params = BattleRuleParam()

        scores = []
        for i, my_pkm in enumerate(my_team.members):
            score = 0.0

            for opp_pkm in opp_team.members:
                # 내가 상대에게 주는 타입 상성 이점
                for my_type in my_pkm.species.types:
                    eff = type_effectiveness_modifier(params, my_type, opp_pkm.species.types)
                    if eff > 1:
                        score += 30 * eff
                    elif eff < 1:
                        score -= 10

                # 상대가 나에게 주는 타입 상성 위험도
                for opp_type in opp_pkm.species.types:
                    eff = type_effectiveness_modifier(params, opp_type, my_pkm.species.types)
                    if eff > 1:
                        score -= 20 * eff
                    elif eff < 1:
                        score += 10

            # BST 보너스 (높을수록 유리)
            bst = sum(my_pkm.stats)
            score += bst * 0.05

            # HP 기반 내구 보너스
            score += my_pkm.stats[Stat.MAX_HP] * 0.03

            # 스피드 보너스 (선공 유리)
            score += my_pkm.stats[Stat.SPEED] * 0.02

            scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [idx for _, idx in scores[:max_size]]
