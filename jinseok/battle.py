from itertools import product
from random import sample
from typing import Optional

from vgc2.agent import BattlePolicy
from vgc2.battle_engine.game_state import State
from vgc2.battle_engine import BattleCommand, BattleRuleParam
from vgc2.battle_engine.view import TeamView
from vgc2.battle_engine.modifiers import Stat, Category, Type, Status
from vgc2.battle_engine.damage_calculator import calculate_damage, type_effectiveness_modifier
from vgc2.battle_engine.pokemon import BattlingPokemon
from vgc2.battle_engine.move import BattlingMove
from vgc2.util.forward import copy_state, forward
from vgc2.util.rng import ZERO_RNG


class JinseokBattlePolicy(BattlePolicy):
    """
    고급 배틀 정책: Greedy 데미지 계산 + Forward Simulation + 스마트 교체
    - 1단계: 모든 가능한 행동 조합에 대해 데미지 기반 빠른 점수 계산
    - 2단계: 상위 후보에 대해 1턴 시뮬레이션으로 최적 행동 선택
    """

    def __init__(self):
        self._greedy_policy = None

    def _get_greedy(self):
        """GreedyBattlePolicy 지연 로딩"""
        if self._greedy_policy is None:
            from vgc2.agent.battle import GreedyBattlePolicy
            self._greedy_policy = GreedyBattlePolicy()
            self._greedy_policy.set_params(self.params)
        return self._greedy_policy

    # ── 상태 평가 함수 ──────────────────────────────────────────

    @staticmethod
    def _status_value(pkm: BattlingPokemon) -> float:
        """상태이상의 불이익 점수"""
        return {
            Status.BURN: 3, Status.SLEEP: 5, Status.PARALYZED: 3,
            Status.POISON: 2, Status.TOXIC: 5, Status.FROZEN: 6,
        }.get(pkm.status, 0)

    def _evaluate_state(self, state: State) -> float:
        """게임 상태를 side 0 관점에서 평가"""
        my = state.sides[0].team
        opp = state.sides[1].team

        my_all = my.active + my.reserve
        opp_all = opp.active + opp.reserve

        my_alive = [p for p in my_all if not p.fainted()]
        opp_alive = [p for p in opp_all if not p.fainted()]

        if not opp_alive:
            return 10000
        if not my_alive:
            return -10000

        my_hp = sum(p.hp / p.constants.stats[Stat.MAX_HP] for p in my_alive)
        opp_hp = sum(p.hp / p.constants.stats[Stat.MAX_HP] for p in opp_alive)

        my_cnt, opp_cnt = len(my_alive), len(opp_alive)

        opp_status = sum(self._status_value(p) for p in opp_alive)
        my_status = sum(self._status_value(p) for p in my_alive)

        return (50 * my_hp - 70 * opp_hp
                + 400 * my_cnt - 500 * opp_cnt
                + 30 * opp_status - 30 * my_status)

    # ── 행동 생성 ────────────────────────────────────────────────

    @staticmethod
    def _actions_for_pkm(pkm, opp_active, reserve):
        """한 포켓몬의 가능한 행동 리스트 반환"""
        if pkm is None or pkm.fainted():
            return [(0, 0)]
        acts = []
        for m_idx, mv in enumerate(pkm.battling_moves):
            if not mv.disabled and mv.pp > 0:
                for t in range(len(opp_active)):
                    acts.append((m_idx, t))
        for r_idx, res in enumerate(reserve):
            if not res.fainted():
                acts.append((-1, r_idx))
        return acts or [(0, 0)]

    def _get_all_actions(self, my_team, opp_team):
        per_pkm = [self._actions_for_pkm(p, opp_team.active, my_team.reserve)
                    for p in my_team.active]
        if len(per_pkm) == 1:
            return [[a] for a in per_pkm[0]]
        return [list(c) for c in product(*per_pkm)]

    # ── 빠른 점수 (시뮬레이션 없이 데미지만 계산) ────────────────

    def _quick_score(self, state: State, actions: list) -> float:
        my_team = state.sides[0].team
        opp_team = state.sides[1].team
        score = 0.0
        opp_hp = [d.hp for d in opp_team.active]

        for i, (act, tgt) in enumerate(actions):
            if i >= len(my_team.active):
                break
            pkm = my_team.active[i]
            if pkm is None or pkm.fainted():
                continue

            # ── 교체 ──
            if act == -1:
                if tgt >= len(my_team.reserve) or my_team.reserve[tgt].fainted():
                    score -= 100
                    continue
                res = my_team.reserve[tgt]
                hp_ratio = pkm.hp / pkm.constants.stats[Stat.MAX_HP]
                # 현재 HP가 낮으면 교체 보너스
                if hp_ratio < 0.25:
                    score += 40
                # 상대 타입 상성 분석
                for opp in opp_team.active:
                    if opp.fainted():
                        continue
                    for rt in res.types:
                        eff = type_effectiveness_modifier(self.params, rt, opp.types)
                        if eff > 1:
                            score += 25 * eff
                    for ot in opp.types:
                        eff_on_me = type_effectiveness_modifier(self.params, ot, pkm.types)
                        if eff_on_me > 1:
                            score += 20  # 불리한 매치업 탈출 보너스
                score -= 10  # 교체 템포 페널티
                continue

            # ── 공격 ──
            if act >= len(pkm.battling_moves):
                continue
            move = pkm.battling_moves[act]
            mc = move.constants
            t = min(tgt, len(opp_team.active) - 1)
            defender = opp_team.active[t]
            if defender.fainted():
                continue

            try:
                dmg = calculate_damage(self.params, 0, mc, state, pkm, defender)
            except Exception:
                dmg = 0

            if dmg >= opp_hp[t]:
                score += 1000 + dmg  # KO 보너스
                opp_hp[t] = 0
            else:
                score += dmg
                opp_hp[t] = max(0, opp_hp[t] - dmg)

            # 상태이상 가산점
            if mc.status != Status.NONE and defender.status == Status.NONE:
                score += 50
            # 자기 버프 가산점
            if mc.self_boosts and any(b > 0 for b in mc.boosts):
                score += 30
            # 상대 디버프 가산점
            if not mc.self_boosts and any(b < 0 for b in mc.boosts):
                score += 25
            # 헤이즈/독압정 등 필드기 가산점
            if mc.hazard.value > 0:
                score += 40

        return score

    # ── 상대 이동 추론 보조 ──────────────────────────────────────

    @staticmethod
    def _deduce_moves(pokemon: BattlingPokemon, max_moves: int):
        n = len(pokemon.battling_moves)
        if n < max_moves:
            ids = {m.constants.id for m in pokemon.battling_moves}
            pool = [m for m in pokemon.constants.species.moves if m.id not in ids]
            need = max_moves - n
            if len(pool) >= need:
                pokemon.battling_moves += [BattlingMove(m) for m in sample(pool, need)]

    def _deduce_state(self, state, opp_view, max_moves=4):
        _s = copy_state(state)
        opp = _s.sides[1].team
        if opp_view:
            cur = len(opp.active + opp.reserve)
            tot = len(opp_view.members)
            if cur < tot:
                ids = {p.constants.species.id for p in opp.active + opp.reserve}
                pool = [p for p in opp_view.members if p.species.id not in ids]
                need = tot - cur
                if len(pool) >= need:
                    opp.reserve += [BattlingPokemon(p) for p in sample(pool, need)]
        for p in opp.active + opp.reserve:
            self._deduce_moves(p, max_moves)
        return _s

    # ── 메인 의사결정 ────────────────────────────────────────────

    def decision(self, state: State,
                 opp_view: Optional[TeamView] = None) -> list[BattleCommand]:
        my_team = state.sides[0].team
        opp_team = state.sides[1].team

        all_actions = self._get_all_actions(my_team, opp_team)
        if not all_actions:
            return [(0, 0)] * len(my_team.active)

        # Phase 1: 빠른 greedy 점수로 후보 축소
        scored = [(self._quick_score(state, a), a) for a in all_actions]
        scored.sort(key=lambda x: x[0], reverse=True)

        top_n = min(20, len(scored))
        candidates = scored[:top_n]

        # Phase 2: Forward Simulation으로 최적 행동 결정
        try:
            _state = self._deduce_state(state, opp_view)
            greedy = self._get_greedy()
            opp_act = greedy.decision(
                State((_state.sides[1], _state.sides[0])), None)

            best_action = candidates[0][1]
            best_score = float('-inf')

            n_my = len(my_team.active)
            n_opp = len(opp_team.active)
            acc = (tuple([ZERO_RNG] * n_my), tuple([ZERO_RNG] * n_opp))

            for _, action in candidates:
                try:
                    sim = copy_state(_state)
                    forward(sim, (action, opp_act), self.params, acc_rng=acc)
                    s = self._evaluate_state(sim)
                    if s > best_score:
                        best_score = s
                        best_action = action
                except Exception:
                    continue

            return best_action
        except Exception:
            return scored[0][1] if scored else [(0, 0)] * len(my_team.active)
