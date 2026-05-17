from vgc2.agent import TeamBuildPolicy, TeamBuildCommand
from vgc2.balance.meta import Meta, Roster
from vgc2.battle_engine.modifiers import Stats, Nature, Stat, Category, Type
from vgc2.battle_engine.damage_calculator import type_effectiveness_modifier
from vgc2.battle_engine.constants import BattleRuleParam


class JinseokTeamBuildPolicy(TeamBuildPolicy):
    """
    고급 팀 빌더: BST + 타입 커버리지 + STAB 기술 우선 선택 + 최적 EV/성격 분배
    """

    def decision(self, roster: Roster, meta: Meta | None,
                 max_team_size: int, max_pkm_moves: int, n_active: int) -> TeamBuildCommand:
        params = BattleRuleParam()

        # 1단계: 후보 포켓몬 점수 매기기 (BST + 타입 다양성)
        candidates = []
        for pkm in roster.pkm_list:
            bst = sum(pkm.base_stats)
            # 고위력 STAB 기술 보유 여부 체크
            best_stab_power = 0
            for mv in pkm.moves:
                if mv.category != Category.OTHER and mv.pkm_type in pkm.types:
                    best_stab_power = max(best_stab_power, mv.base_power)
            stab_bonus = best_stab_power * 0.3
            candidates.append((bst + stab_bonus, pkm))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # 타입 커버리지를 고려한 팀 구성
        team = []
        selected_types = set()

        for _, pkm in candidates:
            if len(team) >= max_team_size:
                break

            # 타입 다양성 보너스: 이미 있는 타입과 겹치지 않으면 우선
            type_overlap = sum(1 for t in pkm.types if t in selected_types)

            # 첫 4마리는 BST 순, 그 이후는 타입 다양성 고려
            if len(team) < 3 or type_overlap == 0:
                team.append(pkm)
                for t in pkm.types:
                    selected_types.add(t)

        # 팀이 부족하면 남은 후보에서 채움
        if len(team) < max_team_size:
            for _, pkm in candidates:
                if pkm not in team:
                    team.append(pkm)
                if len(team) >= max_team_size:
                    break

        # 2단계: 각 포켓몬 빌드 최적화
        result = []
        for pkm in team:
            atk = pkm.base_stats[Stat.ATTACK]
            spa = pkm.base_stats[Stat.SPECIAL_ATTACK]
            spd = pkm.base_stats[Stat.SPEED]
            hp_base = pkm.base_stats[Stat.MAX_HP]

            evs = [0] * 6
            ivs = [31] * 6

            is_physical = atk >= spa

            # ── EV 분배 ──
            if spd >= 100:
                # 빠른 포켓몬: 공격 + 스피드 풀투자
                if is_physical:
                    evs[Stat.ATTACK] = 252
                else:
                    evs[Stat.SPECIAL_ATTACK] = 252
                evs[Stat.SPEED] = 252
                evs[Stat.MAX_HP] = 4
            elif hp_base >= 90:
                # 내구형: HP + 공격 풀투자
                evs[Stat.MAX_HP] = 252
                if is_physical:
                    evs[Stat.ATTACK] = 252
                else:
                    evs[Stat.SPECIAL_ATTACK] = 252
                evs[Stat.SPEED] = 4
            else:
                # 기본: HP + 공격 + 스피드 약간
                evs[Stat.MAX_HP] = 252
                if is_physical:
                    evs[Stat.ATTACK] = 252
                else:
                    evs[Stat.SPECIAL_ATTACK] = 252
                evs[Stat.SPEED] = 4

            # ── 성격 ──
            if spd >= 100:
                nature = Nature.JOLLY if is_physical else Nature.TIMID  # +Spd
            else:
                nature = Nature.ADAMANT if is_physical else Nature.MODEST  # +Atk/SpA

            # ── 기술 선택 ──
            preferred_cat = Category.PHYSICAL if is_physical else Category.SPECIAL
            my_types = set(pkm.types)

            scored_moves = []
            for idx, mv in enumerate(pkm.moves):
                ms = 0.0

                if mv.category == preferred_cat and mv.base_power > 0:
                    ms += mv.base_power * 2
                    # STAB 보너스
                    if mv.pkm_type in my_types:
                        ms += mv.base_power * 1.5
                    # 명중률 보정
                    ms *= mv.accuracy
                elif mv.category != Category.OTHER and mv.base_power > 0:
                    ms += mv.base_power
                    if mv.pkm_type in my_types:
                        ms += mv.base_power * 0.8

                # 상태이상 기술 가산점
                if mv.status.value > 0:
                    ms += 60
                # 버프 기술 가산점
                if mv.self_boosts and any(b > 0 for b in mv.boosts):
                    ms += 50
                # 리커버 가산점
                if mv.heal > 0:
                    ms += 45
                # 프로텍트 가산점
                if mv.protect:
                    ms += 40
                # 필드/날씨 가산점
                if mv.weather_start.value > 0 or mv.field_start.value > 0:
                    ms += 35
                # 헤이즈드 가산점
                if mv.hazard.value > 0:
                    ms += 55
                # 우선도 기술 보너스
                if mv.priority > 0 and mv.base_power > 0:
                    ms += 40
                # 테일윈드/리플렉트/빛의장막
                if mv.toggle_tailwind:
                    ms += 50
                if mv.toggle_reflect or mv.toggle_lightscreen:
                    ms += 40

                scored_moves.append((ms, idx))

            scored_moves.sort(key=lambda x: x[0], reverse=True)

            # 상위 기술 선택, 최소 1개는 공격기가 되도록 보장
            moves = [idx for _, idx in scored_moves[:max_pkm_moves]]

            # 공격기가 하나도 없으면 가장 높은 위력 공격기로 교체
            has_attack = any(
                pkm.moves[m].base_power > 0 and pkm.moves[m].category != Category.OTHER
                for m in moves if m < len(pkm.moves)
            )
            if not has_attack:
                for _, idx in scored_moves:
                    if idx < len(pkm.moves) and pkm.moves[idx].base_power > 0:
                        moves[-1] = idx
                        break

            if len(moves) < max_pkm_moves:
                for i in range(len(pkm.moves)):
                    if i not in moves:
                        moves.append(i)
                    if len(moves) >= max_pkm_moves:
                        break

            result.append((pkm.id, tuple(evs), tuple(ivs), nature, moves))

        return result
