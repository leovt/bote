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
                isinstance(answer, int) and
                0 <= answer < len(self.choices))

    def serialize_for(self, player=None):
        ret = Namespace(
            question='ChooseAction',
            player=self.player.name,
        )
        if player is self.player:
            ret.choices = [choice.serialize() for choice in self.choices]
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
            choices = [choice.serialize() for choice in self.choices]
        )

class DeclareBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, list) and
                len(answer) == self.choices and
                all(isinstance(ans, list) and
                    all(isinstance(a, int) and 0 <= a < len(choice) for a in ans) and
                    len(ans) == len(set(ans))
                    for ans, choice in zip(answer, self.choices)) )

    def serialize_for(self, _unused):
        return Namespace(
            question = 'DeclareBlockers',
            player = self.player.name,
            choices = [choice.serialize() for choice in self.choices]
        )

class OrderBlockers(Question):
    def __init__(self, player, choices):
        self.player = player
        self.choices = choices

    def validate(self, player, answer):
        return (player is self.player and
                isinstance(answer, list) and
                len(answer) == self.choices and
                all(isinstance(ans, list) and
                    all(0 <= a < len(choice) for a in ans)
                    for ans, choice in zip(answer, self.choices)) )

    def serialize_for(self, _unused):
        return Namespace(
            question = 'OrderBlockers',
            player = self.player.name,
            choices = [choice.serialize() for choice in self.choices]
        )
