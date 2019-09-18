from tools import Namespace

class Question:
    def __str__(self):
        return '%s(%s, [...])' % (self.__class__.__name__, self.player)

class ChooseAction(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                answer in self.choices)

    def serialize_for(self, player=None):
        ret = Namespace(
            question='ChooseAction',
            player=self.player.name,
        )
        if player is self.player:
            ret.choices = {key:str(choice) for key, choice in self.choices.items()}
        return ret

class DeclareAttackers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, list) and
                all(x in self.choices for x in answer) and
                len(answer) == len(set(answer)))

    def serialize_for(self, _unused):
        return Namespace(
            question = 'DeclareAttackers',
            player = self.player.name,
            choices = {key:str(choice) for key, choice in self.choices.items()}
        )

class DeclareBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, dict) and
                all(k in self.choices and
                    v in self.choices[k]['attackers']
                    for k,v in answer.items()))

    def serialize_for(self, _unused):
        return dict(
            question = 'DeclareBlockers',
            player = self.player.name,
            choices = {key: {'candidate': str(choice['candidate']),
                             'attackers': {k: str(v) for k, v in choice['attackers'].items()}}
                       for key, choice in self.choices.items()}
        )

class OrderBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, dict) and
                set(answer.keys()) == set(self.choices.keys()) and
                all(isinstance(ans, list) and
                    len(ans) == len(set(ans)) and
                    set(ans) == set(self.choices[key]['blockers'].keys())
                    for key, ans in answer.items())
                )

    def serialize_for(self, _unused):
        return Namespace(
            question = 'OrderBlockers',
            player = self.player.name,
            choices = {key: {'attacker': str(choice['attacker']),
                             'blockers': {k: str(v) for k, v in choice['blockers'].items()}}
                       for key, choice in self.choices.items()}
        )
