from dataclasses import dataclass, field
from enum import Enum
import random
from collections import defaultdict
from enum import Enum
import energy
from cards import Card, ArtCard, RuleCard
from abilities import ActivatableAbility
from event import Event
from tools import Namespace

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

    def attacking(self, player):
        return self.filter(lambda x: x.attacking is player)

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

    def resolve(self):
        yield Event('enter_the_battlefield', self.card, self.controller)

    def __str__(self):
        return f'cast {self.card.name} @{self.controller.name}'


def cast_spell(game, player, card):
    yield Event('pay_energy', player, card.cost)
    yield Event('cast_spell', player, card)


@dataclass
class Damage:
    value: int

@dataclass(eq=False)
class Permanent:
    card: object
    controller: object
    tapped: bool = False
    damage: list = field(default_factory=list)
    attacking: bool = False
    blocking: bool = False
    blockers: list = field(default_factory=list)

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

    def __str__(self):
        return self.name


@dataclass
class Game:
    players: list
    battlefield: ObjectSet = field(default_factory=ObjectSet)
    active_player: Player = None
    priority_player: Player = None
    stack: list = field(default_factory=list)
    step = STEP.PRECOMBAT_MAIN
    event_log: list = field(default_factory=list)
    question = None

    def log(self, event):
        print(str(event)[:50])
        self.event_log.append(event)

    def handle(self, event):
        self.log(event)
        if event.event_id == 'ask_player_action':
            player, question, choices = event.args
            assert player in self.players
            self.question = (player, question, choices, False)
            self.answer = None
        elif event.event_id == 'ask_player_multiple':
            player, question, choices = event.args
            assert player in self.players
            self.question = (player, question, choices, True)
            self.answer = None
        elif event.event_id == 'pay_energy':
            player, energy = event.args
            assert player in self.players
            player.energy_pool.pay(energy)
        elif event.event_id == 'add_energy':
            player, energy = event.args
            assert player in self.players
            player.energy_pool.add(energy)
        elif event.event_id == 'draw_card':
            player, card = event.args
            assert player in self.players
            card_popped = player.library.pop()
            assert card_popped == card
            player.hand.add(card)
        elif event.event_id == 'draw_empty':
            player, = event.args
            assert player in self.players
            player.has_drawn_from_empty_library = True
        elif event.event_id == 'shuffle_library':
            player, = event.args
            assert player in self.players
            random.shuffle(player.library)
        elif event.event_id == 'active_player':
            player, = event.args
            assert player in self.players
            self.active_player = player
        elif event.event_id == 'step':
            step, = event.args
            assert isinstance(step, STEP)
            self.step = step
        elif event.event_id == 'clear_pool':
            player, = event.args
            assert player in self.players
            player.energy_pool.clear()
        elif event.event_id == 'priority':
            player, = event.args
            assert player in self.players or player is None
            self.priority_player = player
        elif event.event_id == 'passed':
            player, = event.args
            assert player in self.players
            player.has_passed = True
        elif event.event_id == 'enter_the_battlefield':
            card, controller = event.args
            assert controller in self.players
            permanent = Permanent(card, controller)
            self.battlefield.add(permanent)
        elif event.event_id == 'exit_the_battlefield':
            permanent, = event.args
            self.battlefield.remove(permanent)
        elif event.event_id == 'put_in_graveyard':
            card, = event.args
            card.owner.graveyard.add(card)
        elif event.event_id == 'play_source':
            player, card = event.args
            assert player in self.players
            player.hand.discard(card)
        elif event.event_id == 'cast_spell':
            player, card = event.args
            assert player in self.players
            player.hand.discard(card)
            self.stack.append(Spell(player, card))
        elif event.event_id == 'resolve_tos':
            tos, = event.args
            tos_popped = self.stack.pop()
            assert tos_popped == tos
        elif event.event_id == 'untap':
            permanent, = event.args
            assert permanent in self.battlefield
            permanent.tapped = False
        elif event.event_id == 'tap':
            permanent, = event.args
            assert permanent in self.battlefield
            permanent.tapped = True
        elif event.event_id == 'reset_pass':
            for player in self.players:
                player.has_passed = False
        elif event.event_id == 'attack':
            attacker, player = event.args
            assert player in self.players
            attacker.attacking = player
        elif event.event_id == 'block':
            attacker, blockers = event.args
            attacker.blockers = blockers
            for b in blockers:
                b.blocking = attacker
        elif event.event_id == 'damage':
            permanent, d = event.args
            permanent.damage.append(Damage(d))
        elif event.event_id == 'player_damage':
            player, d = event.args
            player.life -= d
        elif event.event_id == 'remove_from_combat':
            permanent, = event.args
            assert permanent in self.battlefield
            permanent.attacking = False
            permanent.blocking = False
            permanent.blockers.clear()
        else:
            assert False, f'unable to handle {event}'

    def __str__(self):
        return '<Game>'

    def player_view(self, player=None):
        view = Namespace({
            'players': {id(pl): Namespace({
                    'name': pl.name,
                    'life': pl.life,
                    'hand_size': len(pl.hand),
                    'energy_pool': str(pl.energy_pool.energy),
                    'next_player': id(pl.next_in_turn),
                    'graveyard': [Namespace(
                        id = id(card.art_card),
                        name = card.name)
                        for card in pl.graveyard]})
                for pl in self.players},
            'stack': [str(item) for item in self.stack],
            'battlefield': {id(perm): Namespace({
                    'name': perm.card.name,
                    'card': id(perm.card.art_card),
                    'controller': id(perm.controller)})
                for perm in self.battlefield},
            'active_player': id(self.active_player),
            'step': str(self.step)})
        if player:
            view['you'] = Namespace({
                'id': id(player),
                'hand': [Namespace(
                    id = id(card.art_card),
                    name = card.name)
                    for card in player.hand]
            })
        if self.question:
            (q_player, question, choices, multiple) = self.question
            view['question'] = Namespace({
                'player_id': id(player),
                'question': question,
            })
            if player is q_player or True: #TODO: remove or True
                view['question'].update({
                    'choices': choices,
                    'multiple': multiple,
                })

        return view

def make_library(deck, player):
    return [Card(x, player) for x in deck]

def setup_duel(name1, deck1, name2, deck2):
    p1 = Player(name1, None)
    p2 = Player(name2, p1)
    p1.library = make_library(deck1, p1)
    p2.library = make_library(deck2, p2)
    p1.next_in_turn = p2
    game = Game([p1, p2])
    return game

def start_game(game):
    for player in game.players:
        yield Event('shuffle_library', player)
        for _ in range(7):
            yield from draw_card(player)
    p1 = game.players[0]
    yield Event('active_player', p1)
    yield Event('step', STEP.PRECOMBAT_MAIN)
    yield Event('priority', p1)

def run_game(game, ask_choice):
    event_stream = game_events(game)
    for event in event_stream:
        game.handle(event)
        if game.question:
            game.answer = ask_choice(*game.question)
            game.question = None

def end_of_step(game):
    for player in game.players:
        yield Event('clear_pool', player)
    yield Event('priority', None)
    if game.step == STEP.CLEANUP:
        yield Event('active_player', game.active_player.next_in_turn)
        yield Event('step', STEP.UNTAP)
    else:
        yield Event('step', NEXT_STEP[game.step])

def game_events(game):
    yield from start_game(game)
    while True:
        if game.priority_player:
            yield from state_based_actions(game)
            while check_triggers(game):
                yield from state_based_actions(game)

            if game.priority_player.has_passed:
                if game.stack:
                    tos = game.stack[-1]
                    yield Event('resolve_tos', tos)
                    yield from tos.resolve()
                    yield from open_priority(game)
                else:
                    yield from end_of_step(game)
            else:
                yield from player_action(game, game.priority_player)
                if game.priority_player.has_passed:
                    yield Event('priority', game.priority_player.next_in_turn)
                else:
                    yield from open_priority(game)
        else:
            yield from turn_based_actions(game)

def turn_based_actions(game):
    if game.step == STEP.UNTAP:
        for permanent in game.battlefield:
            if permanent.controller is game.active_player:
                yield Event('untap', permanent)
        yield from end_of_step(game)
    elif game.step == STEP.DRAW:
        yield from draw_card(game.active_player)
        yield from open_priority(game)
    elif game.step == STEP.CLEANUP:
        yield from end_of_step(game)
    elif game.step == STEP.DECLARE_ATTACKERS:
        candidates = list(game.battlefield.creatures.controlled_by(game.active_player))
        choices = [c.card.name for c in candidates]
        yield Event('ask_player_multiple', game.active_player, 'choose attackers', choices)
        attackers_chosen = game.answer
        if attackers_chosen:
            for i in attackers_chosen:
                yield Event('attack', candidates[i], game.active_player.next_in_turn)
            yield from open_priority(game)
        else:
            yield Event('step', STEP.END_OF_COMBAT)
    elif game.step == STEP.DECLARE_BLOCKERS:
        for player in game.players:
            attackers = list(game.battlefield.attacking(player))
            if not attackers:
                continue
            candidates = list(game.battlefield.creatures.controlled_by(player))
            if not candidates:
                continue
            blocking = {}
            blocked_by = defaultdict(list)
            for attacker in attackers:
                choices = [f'block {attacker.card.name} with {c.card.name}' for c in candidates]
                yield Event('ask_player_multiple', player, f'choose blockers for {attacker.card.name}', choices)
                blockers = game.answer
                for b in blockers:
                    blocking[candidates[b]] = attacker
                    blocked_by[attacker].append(candidates[b])
                candidates = [c for c in candidates if c not in blocking]

            # if an attacker is blocked by multiple blockers its controller
            # selects the order of the blockers
            for attacker, blockers in blocked_by.items():
                if len(blockers) > 1:
                    blocker_order = []
                    while len(blocker_order) != len(blockers):
                        yield Event('ask_player_multiple', attacker.controller, 'choose damage order for multiple blockers', [b.card.name for b in blockers])
                        blocker_order = game.answer
                    blockers[:] = [blockers[b] for b in blocker_order]

            for attacker, blockers in blocked_by.items():
                yield Event('block', attacker, blockers)
        yield from open_priority(game)
    elif game.step == STEP.FIRST_STRIKE_DAMAGE:
        # TODO: do not skip this step if any attacker or blocker has first strike.
        yield Event('step', STEP.SECOND_STRIKE_DAMAGE)
    elif game.step == STEP.SECOND_STRIKE_DAMAGE:
        for attacker in game.battlefield.filter(lambda x:x.attacking):
            remaining_strength = attacker.strength
            for b, blocker in enumerate(attacker.blockers):
                if b == len(attacker.blockers)-1:
                    # TODO: trample
                    damage = remaining_strength
                else:
                    damage = min(remaining_strength, blocker.strength)
                remaining_strength -= damage
                yield Event('damage', blocker, damage)
                yield Event('damage', attacker, blocker.strength)
            if remaining_strength:
                yield Event('player_damage', attacker.attacking, remaining_strength)
        yield from open_priority(game)
    elif game.step == STEP.POSTCOMBAT_MAIN:
        for permanent in game.battlefield:
            yield Event('remove_from_combat', permanent)
        yield from open_priority(game)
    else:
        yield from open_priority(game)

def lose_the_game(player):
    print(f'player {player.name} loses the game')
    assert False, 'not implemented'

def destroy(permanent):
    if False: #permanent.has_regenerated or permanent.regenerates():
        yield Event('tap', permanent)
        yield Event('clear_damage', permanent)
        yield Event('has_regenerated', permanent)
        yield Event('remove_from_combat', permanent)
    else:
        yield from put_in_graveyard(permanent)

def put_in_graveyard(permanent):
    yield Event('exit_the_battlefield', permanent)
    yield Event('put_in_graveyard', permanent.card)

def state_based_actions(game):
    for player in game.players:
        if player.life <= 0:
            yield Event('lose', player)
    for player in game.players:
        if player.has_drawn_from_empty_library:
            yield Event('lose', player)
    for creature in {c for c in game.battlefield.creatures if c.toughness <= 0}:
        yield from put_in_graveyard(creature)
    for creature in {c for c in game.battlefield.creatures
                     if c.total_damage_received >= c.toughness}:
        yield from destroy(creature)
    for aura in game.battlefield.auras:
        if aura.attachment not in game.battlefield:
            yield from destroy(aura)


def check_triggers(game):
    pass

def open_priority(game):
    yield Event('reset_pass')
    yield Event('priority', game.active_player)

def discard_excess_cards():
    pass

def draw_card(player):
    if player.library:
        card = player.library[-1]
        yield Event('draw_card', player, card)
    else:
        yield Event('draw_empty', player)

def print_player_view(view):
    print('=' * 80)
    print(f'It is the {view.step} of {view.players[view.active_player].name}s turn.')
    print('Players:')
    for p in view.players.values():
        print(f'    {p.name}: {p.life} life; {p.hand_size} cards in hand, {p.energy_pool} in pool')
        if p.graveyard:
            print('        Graveyard:')
            for card in p.graveyard:
                print(f'            {card.name}')
    print('-' * 80)
    if view.stack:
        print('Stack')
        for item in reversed(view.stack):
            print(f'    {item}')
        print('-' * 80)
    print('Battlefield')
    for pid, p in view.players.items():
        print('    Controlled by', p.name)
        nothing = True
        for obj in view.battlefield.values():
            if obj.controller == pid:
                print('       ', obj.name)
                nothing = False
        if nothing:
            print('        nothing')
    print('-' * 80)
    print('Your hand:')
    for card in view.you.hand:
        print('   ', card.name)

def can_play_source(player):
    return True

def play_source(game, player, card):
    yield Event('play_source', player, card)
    yield Event('enter_the_battlefield', card, player)

def player_action(game, player):
    ACTION_PERFORMED = False
    PASSED = True
    print_player_view(game.player_view(player))
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
                if all(cost.can_pay(permanent, permanent.card) for cost in ability.cost):
                    choices.append(f'activate {permanent.card.name}:{ability}')
                    act = [(cost.pay, (permanent, permanent.card)) for cost in ability.cost]
                    act.append((ability.effect, (player,)))
                    actions.append(act)
    yield Event('ask_player_action', player, f'{player.name} has priority; select an action:', choices)
    answer = game.answer
    if answer==0:
        yield Event('passed', player)
    else:
        for func, arguments in actions[answer]:
            yield from func(*arguments)
