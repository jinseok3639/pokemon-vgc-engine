from vgc2.agent import BattlePolicy, SelectionPolicy, TeamBuildPolicy
from vgc2.competition import Competitor

from .battle import MasterBattlePolicy
from .selection import MasterSelectionPolicy
from .team_builder import MasterTeamBuildPolicy

class ExampleCompetitor(Competitor):

    def __init__(self, name: str = "VGC_Master_AI"):
        self.__name = name
        self.__battle_policy = MasterBattlePolicy()
        self.__selection_policy = MasterSelectionPolicy()
        self.__team_build_policy = MasterTeamBuildPolicy()

    @property
    def battlepolicy(self) -> BattlePolicy | None:
        return self.__battle_policy

    @property
    def selectionpolicy(self) -> SelectionPolicy | None:
        return self.__selection_policy

    @property
    def teambuildpolicy(self) -> TeamBuildPolicy | None:
        return self.__team_build_policy

    @property
    def name(self) -> str:
        return self.__name
