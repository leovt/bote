from dataclasses import dataclass, field
from enum import Enum
import random
from collections import defaultdict
import energy
from cards import Card, ArtCard, RuleCard
from abilities import ActivatableAbility
from event import *
from question import ChooseAction, DeclareBlockers, DeclareAttackers, OrderBlockers
from tools import Namespace, unique_identifiers

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
        yield EnterTheBattlefieldEvent(self.card, self.controller.name)

    def __str__(self):
        return f'cast {self.card.name} @{self.controller.name}'

    def serialize(self):
        return {'controller': self.controller.name,
                'card': self.card.serialize()}

def cast_spell(game, player, card):
    yield PayEnergyEvent(player.name, card.cost)
    yield CastSpellEvent(player.name, card)


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

    def serialize_for(self, player):
        return {
            'name': self.name,
        }

class EndOfGameException(Exception):
    pass

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
    answer = None
    unique_ids: iter = field(default_factory=unique_identifiers)

    def log(self, event):
        print(event)
        self.event_log.append(event)

    def get_player(self, name):
        # todo: replace players by a map
        for player in self.players:
            if player.name == name:
                return player

    def handle(self, event):
        self.log(event)
        handler = getattr(self, f'handle_{event.__class__.__name__}')
        handler(event)

    def handle_QuestionEvent(self, event):
        self.question = event.question
        self.answer = None

    def handle_PayEnergyEvent(self, event):
        player = self.get_player(event.player)
        player.energy_pool.pay(event.energy)

    def handle_AddEnergyEvent(self, event):
        player = self.get_player(event.player)
        event.player.energy_pool.add(event.energy)

    def handle_DrawCardEvent(self, event):
        player = self.get_player(event.player)
        card_popped = player.library.pop()
        assert card_popped is event.card
        card_popped.known_identity = event.card_id
        player.hand.add(card_popped)

    def handle_DrawEmptyEvent(self, event):
        player = self.get_player(event.player)
        player.has_drawn_from_empty_library = True

    def handle_ShuffleLibraryEvent(self, event):
        player = self.get_player(event.player)
        for card in player.library:
            card.known_identity = None
        random.shuffle(player.library)

    def handle_ActivePlayerEvent(self, event):
        player = self.get_player(event.player)
        self.active_player = player

    def handle_StepEvent(self, event):
        self.step = event.step

    def handle_ClearPoolEvent(self, event):
        player = self.get_player(event.player)
        player.energy_pool.clear()

    def handle_PriorityEvent(self, event):
        self.priority_player = self.get_player(event.player)

    def handle_PassedEvent(self, event):
        player = self.get_player(event.player)
        player.has_passed = True

    def handle_EnterTheBattlefieldEvent(self, event):
        controller = self.get_player(event.controller)
        permanent = Permanent(event.card, controller)
        self.battlefield.add(permanent)

    def handle_ExitTheBattlefieldEvent(self, event):
        self.battlefield.remove(event.permanent)

    def handle_PutInGraveyardEvent(self, event):
        event.card.owner.graveyard.add(event.card)

    def handle_PlaySourceEvent(self, event):
        player = self.get_player(event.player)
        player.hand.discard(event.card)

    def handle_CastSpellEvent(self, event):
        player = self.get_player(event.player)
        assert player in self.players
        player.hand.discard(event.card)
        self.stack.append(Spell(player, event.card))

    def handle_ResolveEvent(self, event):
        tos_popped = self.stack.pop()
        assert tos_popped == event.tos

    def handle_UntapEvent(self, event):
        event.permanent.tapped = False

    def handle_TapEvent(self, event):
        event.permanent.tapped = True

    def handle_ResetPassEvent(self, event):
        for player in self.players:
            player.has_passed = False

    def handle_AttackEvent(self, event):
        player = self.get_player(event.player)
        event.attacker.attacking = player

    def handle_BlockEvent(self, event):
        event.attacker.blockers = event.blockers
        for b in event.blockers:
            b.blocking = event.attacker

    def handle_DamageEvent(self, event):
        event.permanent.damage.append(Damage(event.damage))

    def handle_PlayerDamageEvent(self, event):
        player = self.get_player(event.player)
        player.life -= event.damage

    def handle_RemoveFromCombatEvent(self, event):
        event.permanent.attacking = False
        event.permanent.blocking = False
        event.permanent.blockers.clear()

    def handle_PlayerLosesEvent(self, event):
        pass

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
            view['question'] = self.question.serialize_for(player)

        return view

    def set_answer(self, player, answer):
        if self.question is not None and self.answer is None:
            if self.question.validate(player, answer):
                self.answer = answer
                return True
        return False

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
        yield ShuffleLibraryEvent(player.name)
        for _ in range(7):
            yield from draw_card(game, player)
    p1 = game.players[0]
    yield ActivePlayerEvent(p1.name)
    yield StepEvent(STEP.PRECOMBAT_MAIN)
    yield PriorityEvent(p1.name)

def end_of_step(game):
    for player in game.players:
        yield ClearPoolEvent(player.name)
    yield PriorityEvent(None)
    if game.step == STEP.CLEANUP:
        yield ActivePlayerEvent(game.active_player.next_in_turn.name)
        yield StepEvent(STEP.UNTAP)
    else:
        yield StepEvent(NEXT_STEP[game.step])

def game_events(game):
    yield from start_game(game)
    try:
        while True:
            if game.priority_player:
                yield from state_based_actions(game)
                while check_triggers(game):
                    yield from state_based_actions(game)

                if game.priority_player.has_passed:
                    if game.stack:
                        tos = game.stack[-1]
                        yield ResolveEvent(tos)
                        yield from tos.resolve()
                        yield from open_priority(game)
                    else:
                        yield from end_of_step(game)
                else:
                    yield from player_action(game, game.priority_player)
                    if game.priority_player.has_passed:
                        yield PriorityEvent(game.priority_player.next_in_turn.name)
                    else:
                        yield from open_priority(game)
            else:
                yield from turn_based_actions(game)
    except EndOfGameException:
        return


def turn_based_actions(game):
    if game.step == STEP.UNTAP:
        for permanent in game.battlefield:
            if permanent.controller is game.active_player:
                yield UntapEvent(permanent)
        yield from end_of_step(game)
    elif game.step == STEP.DRAW:
        yield from draw_card(game, game.active_player)
        yield from open_priority(game)
    elif game.step == STEP.CLEANUP:
        yield from end_of_step(game)
    elif game.step == STEP.DECLARE_ATTACKERS:
        candidates = {next(game.unique_ids): permanent for permanent in
            game.battlefield.creatures.controlled_by(game.active_player)}
        choices = {key: c.card.name for key, c in candidates.items()}
        question = DeclareAttackers(game.active_player, choices)
        yield QuestionEvent(question)
        attackers_chosen = game.answer
        if attackers_chosen:
            for i in attackers_chosen:
                yield AttackEvent(candidates[i], game.active_player.next_in_turn.name)
            yield from open_priority(game)
        else:
            yield StepEvent(STEP.END_OF_COMBAT)
    elif game.step == STEP.DECLARE_BLOCKERS:
        for player in game.players:
            attackers = {next(game.unique_ids): permanent for permanent in
                game.battlefield.attacking(player)}
            if not attackers:
                continue
            candidates = {next(game.unique_ids): permanent for permanent in
                game.battlefield.creatures.controlled_by(player)}
            if not candidates:
                continue
            blocking = {}
            blocked_by = defaultdict(list)
            question = DeclareBlockers(player,
                {key: {'candidate': cand, 'attackers': attackers}
                 for key, cand in candidates.items()})
            yield QuestionEvent(question)

            for cand, attacker in game.answer.items():
                spec = question.choices[cand]
                blocker = spec['candidate']
                attacker = spec['attackers'][attacker]
                blocking[blocker] = attacker
                blocked_by[attacker].append(blocker)

            # if an attacker is blocked by multiple blockers its controller
            # selects the order of the blockers
            ambigous = {next(game.unique_ids): item
                        for item in blocked_by.items()
                        if len(item[1]) > 1}
            if ambigous:
                choices = {key: {'attacker': attacker,
                                 'blockers': {next(game.unique_ids): b for b in blockers}}
                           for key, (attacker, blockers) in ambigous.items()}
                question = OrderBlockers(game.active_player, choices)
                yield QuestionEvent(question)
                for key, block_order in game.answer.items():
                    blockers = ambigous[key][1]
                    blockers[:] = [choices[key]['blockers'][b] for b in block_order]

            for attacker, blockers in blocked_by.items():
                yield BlockEvent(attacker, blockers)
        yield from open_priority(game)
    elif game.step == STEP.FIRST_STRIKE_DAMAGE:
        # TODO: do not skip this step if any attacker or blocker has first strike.
        yield StepEvent(STEP.SECOND_STRIKE_DAMAGE)
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
                yield DamageEvent(blocker, damage)
                yield DamageEvent(attacker, blocker.strength)
            if remaining_strength:
                yield PlayerDamageEvent(attacker.attacking.name, remaining_strength)
        yield from open_priority(game)
    elif game.step == STEP.POSTCOMBAT_MAIN:
        for permanent in game.battlefield:
            yield RemoveFromCombatEvent(permanent)
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
    yield ExitTheBattlefieldEvent(permanent)
    yield PutInGraveyardEvent(permanent.card)

def state_based_actions(game):
    for player in game.players:
        if player.life <= 0:
            yield PlayerLosesEvent(player)
            # TODO: losing should not end the game if it is a multiplayer game
            raise EndOfGameException
    for player in game.players:
        if player.has_drawn_from_empty_library:
            yield PlayerLosesEvent(player)
            # TODO: losing should not end the game if it is a multiplayer game
            raise EndOfGameException
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
    yield ResetPassEvent()
    yield PriorityEvent(game.active_player.name)

def discard_excess_cards():
    pass

def draw_card(game, player):
    if player.library:
        card = player.library[-1]
        card_id = next(game.unique_ids)
        yield DrawCardEvent(player.name, card, card_id)
    else:
        yield DrawEmptyEvent(player.name)

def can_play_source(player):
    return True

def play_source(game, player, card):
    yield PlaySourceEvent(player.name, card)
    yield EnterTheBattlefieldEvent(card, player.name)

def player_action(game, player):
    ACTION_PERFORMED = False
    PASSED = True
    choices = {}
    actions = {}

    def add_choice(choice, action):
        key = next(game.unique_ids)
        choices[key] = choice
        actions[key] = action

    add_choice('Pass Priority', None)

    if (player is game.active_player and
        game.step in (STEP.PRECOMBAT_MAIN, STEP.POSTCOMBAT_MAIN) and
        not game.stack):
        if can_play_source(player):
            for source in player.hand.sources:
                add_choice(f'play {source.name}', [
                    (play_source, (game, player, source))
                ])

        for card in player.hand.creatures:
            if player.energy_pool.can_pay(card.cost):
                add_choice(f'cast {card.name}', [
                    (cast_spell, (game, player, card))
                ])

    for permanent in game.battlefield.controlled_by(player):
        for ability in permanent.abilities:
            if isinstance(ability, ActivatableAbility):
                if all(cost.can_pay(permanent, permanent.card) for cost in ability.cost):
                    add_choice(f'activate {permanent.card.name}:{ability}', [
                        (cost.pay, (permanent, permanent.card))
                            for cost in ability.cost] + [
                        (ability.effect, (player,))
                    ])
    question = ChooseAction(player, choices)
    yield QuestionEvent(question)
    answer = game.answer
    if actions[answer] is None:
        yield PassedEvent(player.name)
    else:
        for func, arguments in actions[answer]:
            yield from func(*arguments)
