import sys
import os

# 현재 스크립트의 부모 디렉토리(pokemon-vgc-engine)를 python 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vgc2.agent.battle import RandomBattlePolicy
from vgc2.battle_engine import BattleEngine, State, StateView, TeamView
from vgc2.battle_engine.game_state import get_battle_teams
from vgc2.competition.match import run_battle, label_teams
from vgc2.net.stream import GodotClient
from vgc2.util.generator import gen_team

# 내가 만든 마스터 AI 배틀 정책 가져오기
from battle import MasterBattlePolicy

def test_my_ai_battle():
    n_active = 2
    team_size = 4
    n_moves = 4
    
    # 튜토리얼과 동일하게 2개의 랜덤 팀 생성
    team = gen_team(team_size, n_moves), gen_team(team_size, n_moves)
    label_teams(team)
    
    team_view = TeamView(team[0]), TeamView(team[1])
    state = State(get_battle_teams(team, n_active))
    state_view = StateView(state, 0, team_view), StateView(state, 1, team_view)
    
    engine = BattleEngine(state, debug=True)
    
    # Team 0: VGC Master AI (우리가 만든 배틀 정책)
    # Team 1: 기본 Random AI (비교 대상)
    agents = MasterBattlePolicy(), RandomBattlePolicy()
    
    print("~ Team 0 (VGC Master AI) ~")
    print(team[0])
    print("~ Team 1 (Random AI) ~")
    print(team[1])
    
    print("\n--- 배틀 시작 ---")
    winner = run_battle(engine, agents, team_view, state_view, GodotClient())
    
    print(f"\n[결과] {'VGC Master AI' if winner == 0 else 'Random AI'} 승리!")

if __name__ == '__main__':
    test_my_ai_battle()
