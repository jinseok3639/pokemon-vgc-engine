import sys
import os

# 현재 스크립트의 부모 디렉토리(pokemon-vgc-engine)를 python 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 각 참가자 폴더도 sys.path에 추가 (내부 파일끼리 import할 때 ModuleNotFoundError 방지)
submissions_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'edition', 'vgc2025', 'submissions'))
for folder in ["BotzillaSubmission", "LazeComp", "PeachSubmission", "StocKarpadorSubmission", "caaaden_competitor", "evoTrainer", "iceMonteSubmission"]:
    sys.path.append(os.path.join(submissions_dir, folder))

from vgc2.agent.battle import RandomBattlePolicy
from vgc2.battle_engine import BattleEngine, State, StateView, TeamView
from vgc2.battle_engine.game_state import get_battle_teams
from vgc2.competition.match import run_battle, label_teams
from vgc2.net.stream import GodotClient
from vgc2.util.generator import gen_team

# 내가 만든 진석 AI 배틀 정책 가져오기
from battle import JinseokBattlePolicy

# --- 과거 참가자 제출물 (단순 import 가능한 경우만) ---
# 폴더명에 공백이나 특수문자가 있어 파이썬 모듈 로드가 복잡한 경우는 제외했습니다.
try:
    from edition.vgc2025.submissions.BotzillaSubmission.botzillaBattlePolicy import QTableBattlePolicy as BotzillaSubmission
except Exception as e:
    print(f"Botzilla 로드 에러: {e}")
    BotzillaSubmission = None

try:
    from edition.vgc2025.submissions.LazeComp.LazeBattlePolicy import LazeBattlePolicy as LazeComp
except Exception as e:
    LazeComp = None

try:
    from edition.vgc2025.submissions.PeachSubmission.PeachBattlePolicy import PeachBattlePolicy as PeachSubmission
except Exception as e:
    PeachSubmission = None

try:
    from edition.vgc2025.submissions.StocKarpadorSubmission.StocKarpadorBattlePolicy import MonteCarloBattlePolicy as StocKarpadorSubmission
except Exception as e:
    StocKarpadorSubmission = None

try:
    from edition.vgc2025.submissions.caaaden_competitor.caaaden_competitor import CaaadenBattlePolicy as caaaden_competitor
except Exception as e:
    caaaden_competitor = None

try:
    from edition.vgc2025.submissions.evoTrainer.EvoBattlePolicy import EvoBattlePolicy as evoTrainer
except Exception as e:
    print(f"evoTrainer 로드 에러: {e}")
    evoTrainer = None

try:
    from edition.vgc2025.submissions.iceMonteSubmission.iceMonteBattlePolicy import IceMonteBattlePolicy as iceMonteSubmission
except Exception:
    iceMonteSubmission = None

# 제출자명(디렉토리이름)을 key로, Policy 클래스를 value로 매핑
BENCHMARK_POLICIES = {
    "BotzillaSubmission": BotzillaSubmission,
    "LazeComp": LazeComp,
    "PeachSubmission": PeachSubmission,
    "StocKarpadorSubmission": StocKarpadorSubmission,
    "caaaden_competitor": caaaden_competitor,
    "evoTrainer": evoTrainer,
    "iceMonteSubmission": iceMonteSubmission,
    "Random": RandomBattlePolicy  # 기본 비교용
}

def test_my_ai_battle():
    n_active = 2
    team_size = 4
    n_moves = 4
    n_matches_per_opponent = 3 # 상대당 랜덤 팀으로 3세트 (공수교대 포함 총 6판)
    
    print("\n" + "="*50)
    print("🏆 VGC jinseok AI 공정한 벤치마크 테스트 시작 🏆")
    print("조건: 매 세트마다 랜덤 팀 새로 생성 + 불공평 방지 공수 교대 진행")
    print("="*50)
    
    results = {}
    
    for opponent_name, OpponentPolicyClass in BENCHMARK_POLICIES.items():
        if OpponentPolicyClass is None:
            results[opponent_name] = "로드 실패 (건너뜀)"
            continue
            
        print(f"\n⚔️  [{opponent_name}] 와(과)의 배틀 (총 {n_matches_per_opponent * 2}판) 진행 중...")
        master_wins = 0
        opp_wins = 0
        
        for i in range(n_matches_per_opponent):
            # 매 세트마다 완전히 새로운 랜덤 팀 생성
            team = gen_team(team_size, n_moves), gen_team(team_size, n_moves)
            label_teams(team)
            team_view = TeamView(team[0]), TeamView(team[1])
            
            # [Match 1] Master AI: Team 0 vs Opponent: Team 1
            state1 = State(get_battle_teams(team, n_active))
            state_view1 = StateView(state1, 0, team_view), StateView(state1, 1, team_view)
            engine1 = BattleEngine(state1, debug=False)
            agents1 = JinseokBattlePolicy(), OpponentPolicyClass()
            try:
                winner1 = run_battle(engine1, agents1, team_view, state_view1, GodotClient())
                if winner1 == 0: master_wins += 1
                else: opp_wins += 1
            except:
                pass

            # [Match 2] 공수 교대 - Master AI: Team 1 vs Opponent: Team 0
            state2 = State(get_battle_teams((team[1], team[0]), n_active))
            swapped_team_view = TeamView(team[1]), TeamView(team[0])
            state_view2 = StateView(state2, 0, swapped_team_view), StateView(state2, 1, swapped_team_view)
            engine2 = BattleEngine(state2, debug=False)
            agents2 = JinseokBattlePolicy(), OpponentPolicyClass() # jinseok AI가 0번(team[1] 조종)
            try:
                winner2 = run_battle(engine2, agents2, swapped_team_view, state_view2, GodotClient())
                if winner2 == 0: master_wins += 1
                else: opp_wins += 1
            except:
                pass
                
        print(f"   ➤ 결과: jinseok AI {master_wins}승 / {opponent_name} {opp_wins}패")
        
        if master_wins > opp_wins:
            results[opponent_name] = f"jinseok AI 압승 ({master_wins}:{opp_wins})"
        elif master_wins == opp_wins:
            results[opponent_name] = f"무승부 ({master_wins}:{opp_wins})"
        else:
            results[opponent_name] = f"jinseok AI 패배 ({master_wins}:{opp_wins})"
            
    # 최종 결과 요약 출력
    print("\n" + "="*50)
    print("📊 벤치마크 테스트 최종 결과 요약")
    print("="*50)
    for opponent, res in results.items():
        print(f"vs {opponent:<25} | {res}")
    print("="*50)

if __name__ == '__main__':
    test_my_ai_battle()
