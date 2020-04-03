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

    def serialize(self):
        return self.name

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

    def resolve(self, game):
        yield EnterTheBattlefieldEvent(self.card, self.controller, next(game.unique_ids))

    def __str__(self):
        return f'cast {self.card.name} @{self.controller.name}'

    def serialize_for(self, player):
        return {'controller': self.controller.name,
                'card': self.card.serialize_for(player)}

def cast_spell(game, player, card):
    yield PayEnergyEvent(player, card.cost)
    yield CastSpellEvent(player.name, card)


@dataclass
class Damage:
    value: int

@dataclass(eq=False)
class Permanent:
    card: object
    controller: object
    perm_id: str
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

    def serialize_for(self, player):
        return {'card': self.card.serialize_for(player),
                'controller': self.controller.serialize_for(player),
                'perm_id': self.perm_id,
               }

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
            'is_me': self is player,
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
        handler = getattr(self, f'handle_{event.__class__.__name__}')
        handler(event)
        self.log(event)

    def handle_QuestionEvent(self, event):
        self.question = event.question
        self.answer = None

    def handle_PayEnergyEvent(self, event):
        event.player.energy_pool.pay(event.energy)
        event.new_total = event.player.energy_pool.energy

    def handle_AddEnergyEvent(self, event):
        event.player.energy_pool.add(event.energy)
        event.new_total = event.player.energy_pool.energy

    def handle_DrawCardEvent(self, event):
        card_popped = event.player.library.pop()
        assert card_popped is event.card
        card_popped.known_identity = event.card_id
        event.player.hand.add(card_popped)

    def handle_DrawEmptyEvent(self, event):
        event.player.has_drawn_from_empty_library = True

    def handle_ShuffleLibraryEvent(self, event):
        player = self.get_player(event.player)
        for card in player.library:
            card.known_identity = None
        random.shuffle(player.library)

    def handle_StepEvent(self, event):
        assert event.active_player in self.players
        self.step = event.step
        self.active_player = event.active_player

    def handle_ClearPoolEvent(self, event):
        event.player.energy_pool.clear()

    def handle_PriorityEvent(self, event):
        self.priority_player = self.get_player(event.player)

    def handle_PassedEvent(self, event):
        player = self.get_player(event.player)
        player.has_passed = True

    def handle_EnterTheBattlefieldEvent(self, event):
        #controller = self.get_player(event.controller)
        permanent = Permanent(event.card, event.controller, event.perm_id)
        self.battlefield.add(permanent)

    def handle_ExitTheBattlefieldEvent(self, event):
        self.battlefield.remove(event.permanent)

    def handle_PutInGraveyardEvent(self, event):
        event.card.owner.graveyard.add(event.card)

    def handle_DiscardEvent(self, event):
        event.card.owner.hand.discard(event.card)
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
        event.player.life -= event.damage;
        event.new_total = event.player.life;

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
            else:
                print('validate failed')
        else:
            print('did not expect answer now')
        return False

    def run(self):
        # todo: move to __init__
        self.events = game_events(self)

    def next_decision(self):
        ''' return the next question which needs to be answered
            if necessary advance the game to the next question
            if the question is not answered it will be returned repeatedly.
            if the game has ended None is returned
        '''
        while self.question is None:
            event = next(self.events, None)
            if event is None:
                return
            if isinstance(event, QuestionEvent):
                self.question = event.question
                self.answer = None
                break
            self.handle(event)

        return self.question


def make_library(deck, player):
    return [Card(ArtCard.get_by_id(art_id), player)
            for art_id, count in deck.items()
            for _ in range(count)]


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
    yield StepEvent(STEP.PRECOMBAT_MAIN, p1)
    yield PriorityEvent(p1.name)

def end_of_step(game):
    for player in game.players:
        yield ClearPoolEvent(player)
    yield PriorityEvent(None)

    if game.step == STEP.END_OF_COMBAT:
        for permanent in game.battlefield:
            yield RemoveFromCombatEvent(permanent)

    if game.step == STEP.CLEANUP:
        yield StepEvent(STEP.UNTAP, game.active_player.next_in_turn)
    else:
        yield StepEvent(NEXT_STEP[game.step], game.active_player)

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
                        yield from tos.resolve(game)
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
        yield from discard_excess_cards(game)
        yield from end_of_step(game)
    elif game.step == STEP.DECLARE_ATTACKERS:
        candidates = {next(game.unique_ids): permanent for permanent in
            game.battlefield.creatures.controlled_by(game.active_player)}
        choices = {key: c.card for key, c in candidates.items()}
        question = DeclareAttackers(game, game.active_player, choices)
        yield QuestionEvent(question)
        attackers_chosen = game.answer
        if attackers_chosen:
            for i in attackers_chosen:
                yield AttackEvent(candidates[i], game.active_player.next_in_turn.name)
            yield from open_priority(game)
        else:
            yield StepEvent(STEP.END_OF_COMBAT, game.active_player)
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
            question = DeclareBlockers(game, player,
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
                question = OrderBlockers(game, game.active_player, choices)
                yield QuestionEvent(question)
                for key, block_order in game.answer.items():
                    blockers = ambigous[key][1]
                    blockers[:] = [choices[key]['blockers'][b] for b in block_order]

            for attacker, blockers in blocked_by.items():
                yield BlockEvent(attacker, blockers)
        yield from open_priority(game)
    elif game.step == STEP.FIRST_STRIKE_DAMAGE:
        # TODO: do not skip this step if any attacker or blocker has first strike.
        yield StepEvent(STEP.SECOND_STRIKE_DAMAGE, game.active_player)
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
                yield PlayerDamageEvent(attacker.attacking, remaining_strength)
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

def discard_excess_cards(game):
    player = game.active_player
    while len(player.hand)>7:
        choices = {next(game.unique_ids): card for card in player.hand}
        question = ChooseAction(game, player, {key: dict(
            action='discard', card_id=card.known_identity, text=f'discard {card.name}')
            for key, card in choices.items()})
        yield QuestionEvent(question)
        answer = game.answer
        if answer in choices:
            yield DiscardEvent(choices[answer])

def draw_card(game, player):
    if player.library:
        card = player.library[-1]
        card_id = next(game.unique_ids)
        yield DrawCardEvent(player, card, card_id)
    else:
        yield DrawEmptyEvent(player)

def can_play_source(player):
    return True

def play_source(game, player, card):
    yield PlaySourceEvent(player.name, card)
    yield EnterTheBattlefieldEvent(card, player, next(game.unique_ids))

def player_action(game, player):
    ACTION_PERFORMED = False
    PASSED = True
    choices = {}
    actions = {}

    def add_choice(effects, **description):
        key = next(game.unique_ids)
        choices[key] = description
        actions[key] = effects

    add_choice(None, action='pass', text='Pass Priority')

    if (player is game.active_player and
        game.step in (STEP.PRECOMBAT_MAIN, STEP.POSTCOMBAT_MAIN) and
        not game.stack):
        if can_play_source(player):
            for source in player.hand.sources:
                add_choice([(play_source, (game, player, source))],
                    action='play', card_id=source.known_identity, text=f'play {source.name}')

        for card in player.hand.creatures:
            if player.energy_pool.can_pay(card.cost):
                add_choice([(cast_spell, (game, player, card))],
                    action='play', card_id=card.known_identity, text=f'cast {card.name}')

    for permanent in game.battlefield.controlled_by(player):
        for ab_key, ability in enumerate(permanent.abilities):
            if isinstance(ability, ActivatableAbility):
                if all(cost.can_pay(permanent, permanent.card) for cost in ability.cost):
                    add_choice([(cost.pay, (permanent, permanent.card))
                        for cost in ability.cost] + [(ability.effect, (player,))],
                        action='activate', card_id=permanent.card.known_identity, ab_key=ab_key,
                        text=f'activate {permanent.card.name}:{ability}')
    question = ChooseAction(game, player, choices)
    yield QuestionEvent(question)
    answer = game.answer
    if actions[answer] is None:
        yield PassedEvent(player.name)
    else:
        for func, arguments in actions[answer]:
            yield from func(*arguments)
