from vgc2.agent import BattlePolicy, SelectionPolicy, TeamBuildPolicy
from vgc2.competition import Competitor

from .battle import JinseokBattlePolicy
from .selection import JinseokSelectionPolicy
from .team_builder import JinseokTeamBuildPolicy

class JinseokCompetitor(Competitor):

    def __init__(self, name: str = "jinseok"):
        self.__name = name
        self.__battle_policy = JinseokBattlePolicy()
        self.__selection_policy = JinseokSelectionPolicy()
        self.__team_build_policy = JinseokTeamBuildPolicy()

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
