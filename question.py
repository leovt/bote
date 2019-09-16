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
            ret.choices = [str(choice) for choice in self.choices]
        return ret

class DeclareAttackers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, list) and
                all(isinstance(x, int) and 0 <= x < len(self.choices) for x in answer) and
                len(answer) == len(set(answer)))

    def serialize_for(self, _unused):
        return Namespace(
            question = 'DeclareAttackers',
            player = self.player.name,
            choices = [str(choice) for choice in self.choices]
        )

class DeclareBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, dict) and
                len(answer) <= len(self.choices) and
                all(isinstance(k, int) and 0 <= k < len(self.choices) and
                    isinstance(v, int) and 0 <= v < len(self.choices[k]['attackers'])
                for k,v in answer.items()))

    def serialize_for(self, _unused):
        return Namespace(
            question = 'DeclareBlockers',
            player = self.player.name,
            choices = [{'candidate': str(choice['candidate']),
                        'attackers': [str(x) for x in choice['attackers']]}
                       for choice in self.choices]
        )

class OrderBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, list) and
                len(answer) == len(self.choices) and
                all(isinstance(ans, list) and
                    all(isinstance(a, int) and 0 <= a < len(choice['blockers'])
                        for a in ans)
                    and len(set(ans)) == len(choice['blockers'])
                    for ans, choice in zip(answer, self.choices)) )

    def serialize_for(self, _unused):
        return Namespace(
            question = 'OrderBlockers',
            player = self.player.name,
            choices = [str(choice) for choice in self.choices]
        )
