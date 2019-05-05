from dataclasses import dataclass, field
from enum import Enum
import random
import cli
from enum import Enum
import energy
from cards import Card, ArtCard, RuleCard
from abilities import ActivatableAbility

class STEP(Enum):
    UNTAP = 11
    UPKEEP = 12
    DRAW = 13

    PRECOMBAT_MAIN = 21

    BEGIN_COMBAT = 31
    DECLARE_ATTACKERS = 32
    DECLARE_BLOCKERS = 33
    FIRST_STRIKE_DAMAGE = 34
    SECOND_STRIKE_DAMAGE = 35
    END_OF_COMBAT = 36

    POSTCOMBAT_MAIN = 41

    END = 51
    CLEANUP = 52

STEPS = [
        STEP.UNTAP, STEP.UPKEEP, STEP.DRAW,
        STEP.PRECOMBAT_MAIN,
        STEP.BEGIN_COMBAT, STEP.DECLARE_ATTACKERS, STEP.DECLARE_BLOCKERS, STEP.FIRST_STRIKE_DAMAGE, STEP.SECOND_STRIKE_DAMAGE, STEP.END_OF_COMBAT,
        STEP.POSTCOMBAT_MAIN,
        STEP.END, STEP.CLEANUP]


NEXT_STEP = {step:next_step for step, next_step in zip(STEPS, STEPS[1:])}



class ObjectView:
    def filter(self, predicate):
        return ObjectIterator(x for x in self if predicate(x))

    @property
    def creatures(self):
        return self.filter(lambda x: 'creature' in x.types)

    @property
    def auras(self):
        return self.filter(lambda x: 'aura' in x.types)

    @property
    def sources(self):
        return self.filter(lambda x: 'source' in x.types)

    def controlled_by(self, player):
        return self.filter(lambda x: x.controller is player)

class ObjectIterator(ObjectView):
    def __init__(self, iterable):
        self.iter = iter(iterable)

    def __iter__(self):
        return self.iter

class ObjectSet(set, ObjectView):
    pass



@dataclass(eq=False)
class Spell:
    controller: object
    card: object

    def resolve(self, game):
        permanent = Permanent(self.card, self.controller)
        game.battlefield.add(permanent)

    def __str__(self):
        return f'cast {self.card.name} @{self.controller.name}'


def cast_spell(game, player, card):
    player.hand.remove(card)
    player.energy_pool.pay(card.cost)
    game.stack.append(Spell(player, card))


@dataclass(eq=False)
class Permanent:
    card: object
    controller: object
    tapped: bool = False
    damage: list = field(default_factory=list)

    @property
    def types(self):
        return self.card.types

    @property
    def abilities(self):
        return self.card.abilities

    @property
    def toughness(self):
        return self.card.toughness

    @property
    def strength(self):
        return self.card.strength

    @property
    def total_damage_received(self):
        return sum(d.value for d in self.damage)

    def __str__(self):
        return f'{self.card.name} @{self.controller.name}{"{T}" if self.tapped else ""}'

@dataclass(eq=False)
class Player:
    name: str
    next_in_turn: object
    library: list = None
    hand: ObjectSet = field(default_factory=ObjectSet)
    graveyard: ObjectSet = field(default_factory=ObjectSet)
    life: int = 20
    energy_pool: ObjectSet = field(default_factory=energy.EnergyPool)
    has_passed: bool = False
    has_drawn_from_empty_library: bool = False

@dataclass
class Game:
    players: list
    battlefield: ObjectSet
    active_player: Player
    priority_player: Player
    stack: list
    step = STEP.PRECOMBAT_MAIN

def make_library(deck, player):
    return [Card(x, player) for x in deck]

def setup_duel(name1, deck1, name2, deck2):
    p1 = Player(name1, None)
    p2 = Player(name2, p1)
    p1.library = make_library(deck1, p1)
    p2.library = make_library(deck2, p2)
    p1.next_in_turn = p2
    game = Game([p1, p2], ObjectSet(), p1, p1, [])
    for player in game.players:
        shuffle_library(player)
        for _ in range(7):
            draw_card(player)

    return game

def run_game(game):
    while True:
        if game.priority_player:
            state_based_actions(game)
            while check_triggers(game):
                state_based_actions(game)

            if game.priority_player.has_passed:
                if game.stack:
                    tos = game.stack.pop()
                    tos.resolve(game)
                    open_priority(game)
                else:
                    game.priority_player = None
            else:
                passed = player_action(game, game.priority_player)
                if passed:
                    game.priority_player.has_passed = True
                    game.priority_player = game.priority_player.next_in_turn
                else:
                    #todo: elif handling other actions
                    open_priority(game)

        else:
            for player in game.players:
                player.energy_pool.clear()
            if game.step == STEP.CLEANUP:
                game.active_player = game.active_player.next_in_turn
                game.step = STEP.UNTAP
            else:
                game.step = NEXT_STEP[game.step]
            turn_based_actions(game)

def turn_based_actions(game):
    if game.step == STEP.UNTAP:
        for permanent in game.battlefield:
            if permanent.controller is game.active_player:
                permanent.tapped = False
    elif game.step == STEP.DRAW:
        draw_card(game.active_player)
        open_priority(game)
    elif game.step == STEP.CLEANUP:
        discard_excess_cards()
    else:
        open_priority(game)

def lose_the_game(player):
    print(f'player {player.name} loses the game')
    assert False, 'not implemented'

def destroy(game, object):
    if object.has_regenerated or object.regenerates():
        object.tapped = True
        object.damage.clear()
        object.has_regenerated = False
        object.attacking = False
        object.blocking = False
    else:
        put_in_graveyard(game, object)

def put_in_graveyard(game, object):
    if object.card:
        object.card.owner.graveyard.add(object.card)
        game.battlefield.discard(object)

def state_based_actions(game):
    for player in game.players:
        if player.life <= 0:
            lose_the_game(player)
    for player in game.players:
        if player.has_drawn_from_empty_library:
            lose_the_game(player)
    for creature in {c for c in game.battlefield.creatures if c.toughness <= 0}:
        put_in_graveyard(game, creature)
    for creature in {c for c in game.battlefield.creatures
                     if c.total_damage_received >= c.toughness}:
        destroy(game, creature)
    for aura in game.battlefield.auras:
        if aura.attachment not in game.battlefield:
            destroy(game, aura)


def check_triggers(game):
    pass

def open_priority(game):
    for p in game.players:
        p.has_passed = False
    game.priority_player = game.active_player

def discard_excess_cards():
    pass

def draw_card(player):
    if player.library:
        player.hand.add(player.library.pop())
    else:
        player.has_drawn_from_empty_library = True

def print_player_view(game, player):
    print('=' * 80)
    print(f'It is the {game.step} of {game.active_player.name}s turn.')
    print('Players:')
    np = player.next_in_turn
    while True:
        print(f'    {np.name}: {np.life} life; {len(np.hand)} cards in hand, {np.energy_pool.energy} in pool')
        if np is player:
            break
        np = np.next_in_turn
    print('-' * 80)
    if game.stack:
        print('Stack')
        for item in reversed(game.stack):
            print(f'    {item}')
        print('-' * 80)
    print('Battlefield')
    np = player.next_in_turn
    while True:
        print('    Controlled by', np.name)
        nothing = True
        for obj in game.battlefield.controlled_by(np):
            print('       ', obj)
            nothing = False
        if nothing:
            print('        nothing')
        if np is player:
            break
        np = np.next_in_turn
    print('-' * 80)
    print('Your hand:')
    for card in player.hand:
        print('   ', card.name)

def can_play_source(player):
    return True

def play_source(game, player, card):
    perm = Permanent(card, player)
    player.hand.discard(card)
    game.battlefield.add(perm)

def player_action(game, player):
    ACTION_PERFORMED = False
    PASSED = True
    print_player_view(game, player)
    choices = ['Pass Priority']
    actions = [None]

    if (player is game.active_player and
        game.step in (STEP.PRECOMBAT_MAIN, STEP.POSTCOMBAT_MAIN) and
        not game.stack):
        if can_play_source(player):
            for source in player.hand.sources:
                choices.append(f'play {source.name}')
                actions.append([(play_source, (game, player, source))])

        for card in player.hand.creatures:
            if player.energy_pool.can_pay(card.cost):
                choices.append(f'cast {card.name}')
                actions.append([(cast_spell, (game, player, card))])

    for permanent in game.battlefield.controlled_by(player):
        for ability in permanent.abilities:
            if isinstance(ability, ActivatableAbility):
                if all(cost.can_pay(permanent, permanent.card)
                    for cost in ability.cost):
                        choices.append(f'activate {permanent.card.name}:{ability}')
                        act = [(cost.pay, (permanent, permanent.card)) for cost in ability.cost]
                        act.append((ability.effect, (player,)))
                        actions.append(act)

    answer = cli.ask_choice(f'{player.name} has priority; select an action:', choices)
    if answer==0:
        return PASSED

    for func, arguments in actions[answer]:
        func(*arguments)
    return ACTION_PERFORMED

def shuffle_library(player):
    random.shuffle(player.library)
