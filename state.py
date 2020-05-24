from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
import energy
from library import make_library, Library
from abilities import ActivatableAbility, TriggeredAbility
from event import *
from question import ChooseAction, DeclareBlockers, DeclareAttackers, OrderBlockers
from tools import Namespace, unique_identifiers
from step import STEP, NEXT_STEP
from cards import Card, ArtCard
from effects import Effect


def is_simple(value):
    if isinstance(value, (int, str, bool, type(None))):
        return True
    if isinstance(value, (list, tuple)):
        return all(is_simple(x) for x in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and is_simple(v) for k,v in value.items())


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

    def of_types(self, *types):
        return self.filter(lambda x: any(t in x.types for t in types))

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

class ObjectDict(dict, ObjectView):
    def __iter__(self):
        return iter(self.values())



@dataclass(eq=False)
class Spell:
    stack_id: str
    controller: object
    card: object
    choices: dict

    def resolve(self, game):
        if 'creature' in self.card.types:
            yield EnterTheBattlefieldEvent(self.card.secret_id, self.controller.name, next(game.unique_ids))
        elif 'sorcery' in self.card.types or 'instant' in self.card.types:
            effect = Effect(self.card.effect, game, game.objects_from_ids(self.choices), self.controller, None)
            yield from effect.execute()
            yield PutInGraveyardEvent(self.card.secret_id)

    def __str__(self):
        return f'cast {self.card.name} @{self.controller.name}'

    def serialize_for(self, player):
        return {'stack_id': self.stack_id,
                'controller': self.controller.name,
                'card': self.card.serialize_for(player)}


@dataclass(eq=False)
class AbilityOnStack:
    stack_id: str
    ability: object
    choices: dict
    controller: object
    permanent: object

    def resolve(self, game):
        effect = Effect(self.ability.effect, game, self.choices, self.controller, self.permanent)
        yield from effect.execute()

    def __str__(self):
        return f'ability of {self.permanent.card.name}'

    def serialize_for(self, player):
        return {'stack_id': self.stack_id,
                'controller': self.permanent.controller.name,
                'card': self.permanent.card.serialize_for(player),
                'ability': self.ability.serialize_for(player),
        }


def cast_spell(game, player, card):
    choices = {}
    if card.effect:
        yield from make_choices(game, choices, card.effect, player, None)
    yield PayEnergyEvent(player.name, str(card.cost))
    yield CastSpellEvent(next(game.unique_ids), player.name, card.secret_id, choices)


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
    on_battlefield_at_begin_of_turn : bool = False

    @property
    def types(self):
        return self.card.types

    @property
    def subtypes(self):
        return self.card.subtypes

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
    sources_played_this_turn: int = 0

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
    battlefield: ObjectDict = field(default_factory=ObjectDict)
    active_player: Player = None
    priority_player: Player = None
    stack: list = field(default_factory=list)
    step = STEP.PRECOMBAT_MAIN
    event_log: list = field(default_factory=list)
    question = None
    answer = None
    unique_ids: iter = field(default_factory=unique_identifiers)
    triggers: list = field(default_factory=list)
    cards: dict = field(default_factory=dict)
    continuous_effects: dict = field(default_factory=OrderedDict)


    def log(self, event):
        self.event_log.append(event)

    def get_player(self, name):
        # todo: replace players by a map
        for player in self.players:
            if player.name == name:
                return player

    def handle(self, event):
        handler = getattr(self, f'handle_{event.__class__.__name__}')
        assert is_simple(event.__dict__), event.__dict__
        print(event)
        for key, value in dict(event.__dict__).items():
            if key=='perm_id' and value in self.battlefield:
                event.permanent = self.battlefield[value].serialize_for(self.players[0])
            if key=='attacker_id' and value in self.battlefield:
                event.attacker = self.battlefield[value].serialize_for(self.players[0])
            if key=='blocker_ids':
                event.blockers = [self.battlefield[x].serialize_for(self.players[0]) for x in value]
            if key=='stack_id' and self.stack and self.stack[-1].stack_id == value:
                event.tos = self.stack[-1].serialize_for(self.players[0])
        assert is_simple(event.__dict__), event.__dict__
        handler(event)
        assert is_simple(event.__dict__), event.__dict__
        self.log(event)

    def handle_QuestionEvent(self, event):
        self.question = event.question
        self.answer = None

    def handle_PayEnergyEvent(self, event):
        player = self.get_player(event.player)
        player.energy_pool.pay(energy.Energy.parse(event.energy))
        event.new_total = str(player.energy_pool.energy)

    def handle_AddEnergyEvent(self, event):
        player = self.get_player(event.player)
        player.energy_pool.add(energy.Energy.parse(event.energy))
        event.new_total = str(player.energy_pool.energy)

    def handle_DrawCardEvent(self, event):
        player = self.get_player(event.player)
        card_popped_sid = player.library.pop_given(event.card_secret_id)
        assert card_popped_sid == event.card_secret_id
        card_popped = self.cards[card_popped_sid]
        card_popped.known_identity = event.card_id
        player.hand.add(card_popped)

    def handle_DrawEmptyEvent(self, event):
        player = self.get_player(event.player)
        player.has_drawn_from_empty_library = True

    def handle_ShuffleLibraryEvent(self, event):
        player = self.get_player(event.player)
        for card_sid in player.library:
            self.cards[card_sid].known_identity = None
        player.library.shuffle()

    def handle_StepEvent(self, event):
        self.active_player = self.get_player(event.active_player)
        assert self.active_player
        self.step = STEP[event.step]
        self.triggers.append(('BEGIN_OF_STEP', self.step))
        if self.step == STEP.UNTAP:
            for player in self.players:
                player.sources_played_this_turn = 0
            for permanent in self.battlefield:
                permanent.on_battlefield_at_begin_of_turn = True

    def handle_ClearPoolEvent(self, event):
        player = self.get_player(event.player)
        player.energy_pool.clear()

    def handle_PriorityEvent(self, event):
        self.priority_player = self.get_player(event.player)

    def handle_PassedEvent(self, event):
        player = self.get_player(event.player)
        player.has_passed = True

    def handle_EnterTheBattlefieldEvent(self, event):
        permanent = Permanent(self.cards[event.card_secret_id], self.get_player(event.controller), event.perm_id)
        self.battlefield[permanent.perm_id] = permanent

    def handle_ExitTheBattlefieldEvent(self, event):
        del self.battlefield[event.perm_id]

    def handle_PutInGraveyardEvent(self, event):
        card = self.cards[event.card_secret_id]
        card.owner.graveyard.add(card)

    def handle_DiscardEvent(self, event):
        self.cards[event.card_secret_id].owner.hand.discard(self.cards[event.card_secret_id])
        self.cards[event.card_secret_id].owner.graveyard.add(self.cards[event.card_secret_id])

    def handle_PlaySourceEvent(self, event):
        player = self.get_player(event.player)
        player.hand.discard(self.cards[event.card_secret_id])
        player.sources_played_this_turn += 1

    def handle_CastSpellEvent(self, event):
        player = self.get_player(event.player)
        card = self.cards[event.card_secret_id]
        player.hand.discard(card)
        self.stack.append(Spell(event.stack_id, player, card, event.target))

    def handle_ActivateAbilityEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        ability = permanent.card.abilities[event.ability_index]
        controller = permanent.controller #TODO: move controller into the event
        choices = self.objects_from_ids(event.choices)
        self.stack.append(AbilityOnStack(event.stack_id, ability, choices, controller, permanent))

    def handle_CreateContinuousEffectEvent(self, event):
        self.continuous_effects[event.effect_id] = event

    def handle_EndContinuousEffectEvent(self, event):
        del self.continuous_effects[event.effect_id]

    def handle_ResolveEvent(self, event):
        tos_popped = self.stack.pop()
        assert tos_popped.stack_id == event.stack_id

    def handle_UntapEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.tapped = False

    def handle_TapEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.tapped = True

    def handle_ResetPassEvent(self, event):
        for player in self.players:
            player.has_passed = False

    def handle_AttackEvent(self, event):
        player = self.get_player(event.player)
        attacker = self.battlefield[event.attacker_id]
        attacker.attacking = player

    def handle_BlockEvent(self, event):
        attacker = self.battlefield[event.attacker_id]
        attacker.blockers = [self.battlefield[x] for x in event.blocker_ids]
        for b in attacker.blockers:
            b.blocking = attacker

    def handle_DamageEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.damage.append(Damage(event.damage))

    def handle_PlayerDamageEvent(self, event):
        player = self.get_player(event.player)
        player.life -= event.damage;
        event.new_total = player.life;

    def handle_RemoveFromCombatEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.attacking = False
        permanent.blocking = False
        permanent.blockers.clear()

    def handle_PlayerLosesEvent(self, event):
        pass

    def handle_ClearTriggerEvent(self, event):
        self.triggers.clear()

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

    def objects_from_ids(self, choices_ids):
        choices = {}
        for key, value in choices_ids.items():
            if value['type'] == 'player':
                choices[key] = self.get_player(value['player'])
            else:
                choices[key] = self.battlefield[value['perm_id']]
        return choices

    def run(self, skip_start=False):
        # todo: move to __init__
        self.events = game_events(self, skip_start)

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

    def serialize(self):
        return {
            'players': [{'name': p.name} for p in self.players],
            'cards': [{
                'secret_id': c.secret_id,
                'art_id': c.art_card.art_id,
                'owner': c.owner.name,
                } for c in self.cards.values()],
            'events': [event.serialize() for event in self.event_log]
        }

    @staticmethod
    def deserialize(data):
        players = []
        cards_per_player = {}
        player = None
        for p in data['players']:
            player = Player(p['name'], player)
            cards_per_player[p['name']] = []
            players.append(player)
        players[0].next_in_turn = player

        game = Game(players)

        for c in data['cards']:
            cards_per_player[c['owner']].append(c['secret_id'])
            card = Card(c['secret_id'], ArtCard.get_by_id(c['art_id']), game.get_player(c['owner']))
            game.cards[card.secret_id] = card

        for p in players:
            p.library = Library(cards_per_player[p.name])

        for e in data['events']:
            kwargs = dict(e)
            del kwargs['event_id']
            event = event_classes[e['event_id']](**kwargs)
            game.handle(event)

        game.run(skip_start=True)
        return game




def setup_duel(name1, deck1, name2, deck2):
    p1 = Player(name1, None)
    p2 = Player(name2, p1)
    game = Game([p1, p2])
    p1.library = make_library(deck1, p1, game)
    p2.library = make_library(deck2, p2, game)
    p1.next_in_turn = p2
    return game

def start_game(game):
    for player in game.players:
        yield ShuffleLibraryEvent(player.name)
        for _ in range(7):
            yield from draw_card(game, player)
    p1 = game.players[0]
    yield StepEvent(STEP.PRECOMBAT_MAIN.name, p1.name)
    yield PriorityEvent(p1.name)

def end_of_step(game):
    for player in game.players:
        yield ClearPoolEvent(player.name)
    yield PriorityEvent(None)

    if game.step == STEP.END_OF_COMBAT:
        for permanent in game.battlefield:
            yield RemoveFromCombatEvent(permanent.perm_id)

    if game.step == STEP.CLEANUP:
        yield StepEvent(STEP.UNTAP.name, game.active_player.next_in_turn.name)
    else:
        yield StepEvent(NEXT_STEP[game.step].name, game.active_player.name)

def game_events(game, skip_start):
    if not skip_start:
        yield from start_game(game)
    try:
        while True:
            if game.priority_player:
                while True:
                    yield from state_based_actions(game)
                    triggered_abilities = check_triggers(game)
                    yield ClearTriggerEvent()
                    if not triggered_abilities:
                        break
                    for (permanent, ab_idx, ability) in triggered_abilities:
                        yield ActivateAbilityEvent(next(game.unique_ids), permanent.perm_id, ab_idx, {})


                if game.priority_player.has_passed:
                    if game.stack:
                        tos = game.stack[-1]
                        yield ResolveEvent(tos.stack_id)
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
                yield UntapEvent(permanent.perm_id)
        yield from end_of_step(game)
    elif game.step == STEP.DRAW:
        yield from draw_card(game, game.active_player)
        yield from open_priority(game)
    elif game.step == STEP.CLEANUP:
        yield from discard_excess_cards(game)
        yield from clear_all_damage(game)
        yield from end_continuous_effects(game)
        yield from end_of_step(game)
    elif game.step == STEP.DECLARE_ATTACKERS:
        candidates = {next(game.unique_ids): permanent for permanent in
            game.battlefield.creatures.controlled_by(game.active_player)
            if permanent.on_battlefield_at_begin_of_turn or
            permanent.card.has_keyword_ability('haste')
            }
        choices = {key: c.card for key, c in candidates.items()}
        if choices:
            question = DeclareAttackers(game, game.active_player, choices)
            yield QuestionEvent(question)
            attackers_chosen = game.answer
        else:
            attackers_chosen = []
        if attackers_chosen:
            for i in attackers_chosen:
                if not candidates[i].card.has_keyword_ability('vigilance'):
                    yield TapEvent(candidates[i].perm_id)
                yield AttackEvent(candidates[i].perm_id, game.active_player.next_in_turn.name)
            yield from open_priority(game)
        else:
            yield StepEvent(STEP.END_OF_COMBAT.name, game.active_player.name)
    elif game.step == STEP.DECLARE_BLOCKERS:
        for player in game.players:
            attackers = {next(game.unique_ids): permanent for permanent in
                game.battlefield.attacking(player)}
            if not attackers:
                continue

            candidates = {}
            for cand in game.battlefield.creatures.controlled_by(player):
                blockable = {k:attacker for k,attacker in attackers.items()
                    if can_block(cand, attacker)}
                if blockable:
                    key = next(game.unique_ids)
                    candidates[key] = {
                        'candidate': cand,
                        'attackers': blockable
                    }
            if not candidates:
                continue

            question = DeclareBlockers(game, player, candidates)
            yield QuestionEvent(question)

            blocking = {}
            blocked_by = defaultdict(list)
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
                yield BlockEvent(attacker.perm_id, [b.perm_id for b in blockers])
        yield from open_priority(game)
    elif game.step == STEP.FIRST_STRIKE_DAMAGE:
        # TODO: do not skip this step if any attacker or blocker has first strike.
        yield StepEvent(STEP.SECOND_STRIKE_DAMAGE.name, game.active_player.name)
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
                yield DamageEvent(blocker.perm_id, damage)
                yield DamageEvent(attacker.perm_id, blocker.strength)
            if remaining_strength:
                yield PlayerDamageEvent(attacker.attacking.name, remaining_strength)
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
    yield ExitTheBattlefieldEvent(permanent.perm_id)
    yield PutInGraveyardEvent(permanent.card.secret_id)

def end_continuous_effects(game):
    ending_ids = [effect_id
                  for (effect_id, effect) in game.continuous_effects.items()
                  if effect.until_end_of_turn]
    for effect_id in ending_ids:
        yield EndContinuousEffectEvent(effect_id)

def clear_all_damage(game):
    yield from []
    #TODO: implement

def state_based_actions(game):
    for player in game.players:
        if player.life <= 0:
            yield PlayerLosesEvent(player.name)
            # TODO: losing should not end the game if it is a multiplayer game
            raise EndOfGameException
    for player in game.players:
        if player.has_drawn_from_empty_library:
            yield PlayerLosesEvent(player.name)
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
    has_triggered = []
    for trigger in game.triggers:
        for permanent in game.battlefield:
            for ab_idx, ability in enumerate(permanent.card.abilities):
                if isinstance(ability, TriggeredAbility):
                    if ability.trigger == trigger:
                        has_triggered.append((permanent, ab_idx, ability))
    return has_triggered


def open_priority(game):
    yield ResetPassEvent()
    yield PriorityEvent(game.active_player.name)


def discard_excess_cards(game):
    player = game.active_player
    while len(player.hand)>7:
        choices = {next(game.unique_ids): card for card in player.hand}
        question = ChooseAction(game, player, {key: dict(
            action='discard', card_id=card.known_identity, text=f'discard {card.name}')
            for key, card in choices.items()}, 'discard')
        yield QuestionEvent(question)
        answer = game.answer
        if answer in choices:
            yield DiscardEvent(choices[answer].secret_id)

def draw_card(game, player):
    if player.library:
        card = player.library.top()
        card_id = next(game.unique_ids)
        yield DrawCardEvent(player.name, card, card_id)
    else:
        yield DrawEmptyEvent(player.name)

def can_block(blocker, attacker):
    if blocker.tapped:
        return False
    # TODO: logic for flying, reach etc
    return True

def can_play_source(player):
    return player.sources_played_this_turn == 0

def play_source(game, player, card):
    yield PlaySourceEvent(player.name, card.secret_id)
    yield EnterTheBattlefieldEvent(card.secret_id, player.name, next(game.unique_ids))

def player_action(game, player):
    ACTION_PERFORMED = False
    PASSED = True
    choices = {}
    actions = {}

    def add_choice(effects, **description):
        key = next(game.unique_ids)
        choices[key] = description
        actions[key] = effects

    if game.stack:
        pass_text = 'Pass, resolve %s' % game.stack[-1]
    else:
        pass_text = 'Pass, continue with %s' % NEXT_STEP[game.step]

    add_choice(None, action='pass', text=pass_text)

    if (player is game.active_player and
        game.step in (STEP.PRECOMBAT_MAIN, STEP.POSTCOMBAT_MAIN) and
        not game.stack):
        if can_play_source(player):
            for source in player.hand.sources:
                add_choice([(play_source, (game, player, source), {})],
                    action='play', card_id=source.known_identity, text=f'play {source.name}')

        for card in player.hand.of_types('creature', 'sorcery'):
            if player.energy_pool.can_pay(card.cost):
                add_choice([(cast_spell, (game, player, card), {})],
                    action='play', card_id=card.known_identity, text=f'cast {card.name}')

    for permanent in game.battlefield.controlled_by(player):
        for ab_key, ability in enumerate(permanent.abilities):
            if isinstance(ability, ActivatableAbility):
                if all(cost.can_pay(permanent, permanent.card) for cost in ability.cost):
                    add_choice([(cost.pay, (permanent, permanent.card), {})
                        for cost in ability.cost] + [(activate_ability, (game, ability, ab_key, player, permanent), {})],
                        action='activate', card_id=permanent.card.known_identity, ab_key=ab_key,
                        text=f'activate {permanent.card.name}:{ability}')
    question = ChooseAction(game, player, choices, 'action')
    yield QuestionEvent(question)
    answer = game.answer
    if actions[answer] is None:
        yield PassedEvent(player.name)
    else:
        for func, arguments, kwarguments in actions[answer]:
            yield from func(*arguments, **kwarguments)

def activate_ability(game, ability, ab_idx, controller, permanent):
    choices = {}
    yield from make_choices(game, choices, ability.effect, controller, permanent)

    if ability.is_energy_ability:
        effect = Effect(ability.effect, game, game.objects_from_ids(choices), controller.name, permanent.perm_id)
        yield from effect.execute()
    else:
        yield ActivateAbilityEvent(next(game.unique_ids), permanent.perm_id, ab_idx, choices)

def make_choices(game, choices, effect, controller, permanent):
    for id, selector in effect.choices.items():
        question_choices = {}
        for candidate in select_objects(game, selector, controller, permanent):
            candidate.update({'action': 'target', 'text': 'target'})
            question_choices[next(game.unique_ids)] = candidate
        if not question_choices:
            print('No valid choice found')
            return #no valid choice
        question = ChooseAction(game, controller, question_choices, 'target')
        yield QuestionEvent(question)
        answer = game.answer
        assert answer in question_choices
        choices[id] = question_choices[answer]



def select_objects(game, selector, controller, permanent):
    include_types = set()
    exclude_types = set()
    include_colors = set()
    exclude_colors = set()
    include_subtypes = set()
    exclude_subtypes = set()

    other_permanent = False

    for sel in selector.children:
        include = True
        if sel.data == 'positive_selector':
            include = True
        elif sel.data == 'negative_selector':
            include = False
        else:
            assert False

        spec = sel.children[0]
        if spec.data == 'type_spec':
            selection = { x.children[0] for x in spec.children }
            if 'permanent' in selection:
                selection |= { 'creature', 'enchantment', 'source' }
                selection.discard('permanent')
            if include:
                include_types |= selection
            else:
                exclude_types |= selection
        elif spec.data == 'color_spec':
            selection = { x.children[0] for x in spec.children }
            if include:
                include_colors |= selection
            else:
                exclude_colors |= selection
        elif spec.data == 'subtype_spec':
            selection = { x.children[0] for x in spec.children }
            if include:
                include_subtypes |= selection
            else:
                exclude_subtypes |= selection
        elif spec.data == 'other_spec':
            if include:
                other_permanent = True
            else:
                assert False, 'bad spec !other'
        else:
            assert False

    # done interpreting spec, now select

    if 'player' in include_types:
        for player in game.players:
            yield {'player': player.name, 'type': 'player'}
    include_types.discard('player')

    for perm in game.battlefield:
        if perm.types & exclude_types:
            continue
        if include_types and not perm.types & include_types:
            continue
        if perm.subtypes & exclude_subtypes:
            continue
        if include_subtypes and not perm.subtypes & include_subtypes:
            continue
        #todo: colors
        if other_permanent and permanent == perm:
            continue

        yield {'card_id': perm.card.known_identity,
               'perm_id': perm.perm_id,
               'type': 'permanent'}
