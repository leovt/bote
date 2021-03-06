import weakref

from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
import energy
from keywords import KEYWORDS
from library import Library
from abilities import ActivatableAbility, TapCost
from bote_collections import IndexedOrderedCollection, TriggerCollection
from event import *
from question import ChooseAction, DeclareBlockers, DeclareAttackers, OrderBlockers
from tools import Namespace, unique_identifiers
from step import STEP, NEXT_STEP
from cards import Card, ArtCard, Token
from effects import Effect


def is_simple(value):
    if isinstance(value, (int, str, bool, type(None))):
        return True
    if isinstance(value, (list, tuple)):
        return all(is_simple(x) for x in value)
    if isinstance(value, dict):
        return all(isinstance(k, (str, int)) and is_simple(v) for k,v in value.items())


class ObjectView:
    def filter(self, predicate):
        return ObjectIterator(x for x in self if predicate(x))

    @property
    def creatures(self):
        return self.filter(lambda x: 'creature' in x.types)

    @property
    def enchantments(self):
        return self.filter(lambda x: 'enchantment' in x.types)

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
        if {'creature', 'enchantment'} & self.card.types:
            perm_id = next(game.unique_ids)
            yield EnterTheBattlefieldEvent(self.card.secret_id,
                                           None,
                                           self.controller.player_id,
                                           perm_id,
                                           self.choices)
            permanent = game.battlefield[perm_id]
        elif {'sorcery', 'instant'} & self.card.types:
            yield PutInGraveyardEvent(self.card.secret_id)
            permanent = None
        else:
            assert False, f'unknown card types {self.card.types}.'

        if hasattr(self.card, 'effect') and self.card.effect:
            effect = Effect(self.card.effect,
                            game,
                            game.objects_from_ids(self.choices),
                            self.controller,
                            permanent)
            yield from effect.execute()

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


@dataclass(eq=False)
class TriggerOnStack:
    stack_id: str
    effect: list
    permanent: object

    def resolve(self, game):
        for event_spec in self.effect:
            kwargs = dict(event_spec)
            del kwargs['event_id']
            event = event_classes[event_spec['event_id']](**kwargs)
            yield event

    def __str__(self):
        return f'triggered effect of {self.permanent.card.name}'

    def serialize_for(self, player):
        return {'stack_id': self.stack_id,
                'effect': self.effect,
                'card': self.permanent.card.serialize_for(player),
        }


def cast_spell(game, player, card):
    choices = {}
    cost = card.cost
    if cost.variable:
        yield from choose_x(game, choices, player.energy_pool.energy.total - cost.total, player)
        cost = cost.replace_variable(choices['x'])
    if card.effect:
        yield from make_choices(game, choices, card.effect, player, None)
    yield PayEnergyEvent(player.player_id, str(cost))
    yield CastSpellEvent(next(game.unique_ids), player.player_id, card.secret_id, choices)


@dataclass
class Damage:
    value: int

class Permanent:
    def __init__(self, perm_id:str, game:'Game', card:Card, controller:'Player', choices:dict):
        self.perm_id = perm_id
        self._game_ref = weakref.ref(game)
        self.card = card
        self.controller = controller
        self.choices = choices

        self.tapped: bool = False
        self.damage: list = []
        self.attacking: bool = False
        self.blocking: bool = False
        self.blockers: list = []
        self.on_battlefield_at_begin_of_turn: bool = False

    @property
    def game(self) -> 'Game':
        return self._game_ref()

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
        ret = self.card.toughness
        for effect in self.game.continuous_effects.values_by_object_id(self.perm_id):
            assert self.perm_id in effect.object_ids
            for modifier in effect.modifiers:
                if modifier[0] == 'delta_stat':
                    ret += modifier[2]
                elif modifier[0] == 'set_stat':
                    ret = modifier[2]
        return ret

    @property
    def strength(self):
        ret = self.card.strength
        for effect in self.game.continuous_effects.values_by_object_id(self.perm_id):
            assert self.perm_id in effect.object_ids
            for modifier in effect.modifiers:
                if modifier[0] == 'delta_stat':
                    ret += modifier[1]
                elif modifier[0] == 'set_stat':
                    ret = modifier[1]
        return ret

    def has(self, keyword):
        assert keyword in KEYWORDS, f'undefined keyword {keyword!r}.'
        ret = any(ability.get('keyword') == keyword for ability in self.card.abilities if isinstance(ability, dict))
        for effect in self.game.continuous_effects.values_by_object_id(self.perm_id):
            assert self.perm_id in effect.object_ids
            for modifier in effect.modifiers:
                if modifier[0] == 'add_keyword' and modifier[1] == keyword:
                    ret = True
                elif modifier[0] == 'remove_keyword' and modifier[1] == keyword:
                    ret = False
        return ret

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
    player_id: str
    name: str
    next_in_turn_id: str
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
            'player_id': self.player_id,
            'name': self.name,
            'is_me': self is player,
        }

class EndOfGameException(Exception):
    pass

class Game:
    def __init__(self):
        self.players = {}
        self.battlefield = ObjectDict()
        self.active_player = None
        self.priority_player = None
        self.stack = []
        self.step = STEP.PRECOMBAT_MAIN
        self.event_log = []
        self.question = None
        self.answer = None
        self.unique_ids = unique_identifiers()
        self.triggers = []
        self.cards = {}
        self.continuous_effects = IndexedOrderedCollection()
        self.triggered_effects = TriggerCollection()

    @staticmethod
    def deserialize(data):
        game = Game()
        for event_spec in data['events']:
            kwargs = dict(event_spec)
            del kwargs['event_id']
            event = event_classes[event_spec['event_id']](**kwargs)
            game.handle(event)
        game.run()
        return game


    @staticmethod
    def create_duel(name1, deck1, name2, deck2):
        game = Game()
        id1 = 0 #next(game.unique_ids)
        id2 = 1 #next(game.unique_ids)

        def create_card_list(deck):
            return [[next(game.unique_ids), art_id]
                    for art_id, count in deck.items()
                    for _ in range(count)]

        game.handle(CreatePlayerEvent(id1, name1, create_card_list(deck1), id2))
        game.handle(CreatePlayerEvent(id2, name2, create_card_list(deck2), id1))
        for player in game.players.values():
            game.handle(ShuffleLibraryEvent(player.player_id))
            for _ in range(7):
                for event in draw_card(game, player):
                    game.handle(event)
        game.handle(StepEvent(STEP.PRECOMBAT_MAIN.name, id1))
        game.handle(PriorityEvent(id1))
        game.run()
        return game


    def log(self, event):
        self.event_log.append(event)

    def get_player(self, name):
        # todo: replace players by a map
        for player in self.players.values():
            if player.name == name:
                return player

    def handle(self, event):
        handler = getattr(self, f'handle_{event.__class__.__name__}')
        assert is_simple(event.__dict__), event.__dict__
        for key, value in dict(event.__dict__).items():
            if key=='perm_id' and value in self.battlefield:
                event.permanent = self.battlefield[value].serialize_for(self.players[0])
            if key=='attacker_id' and value in self.battlefield:
                event.attacker = self.battlefield[value].serialize_for(self.players[0])
            if key=='blocker_ids':
                event.blockers = [self.battlefield[x].serialize_for(self.players[0]) for x in value]
            if key=='object_ids':
                event.objects = [self.battlefield[x].serialize_for(self.players[0]) for x in value]
            if key=='stack_id' and self.stack and self.stack[-1].stack_id == value:
                event.tos = self.stack[-1].serialize_for(self.players[0])
        assert is_simple(event.__dict__), event.__dict__
        handler(event)
        assert is_simple(event.__dict__), event.__dict__
        self.log(event)

    def handle_CreatePlayerEvent(self, event):
        player = Player(event.player_id, event.name, event.next_in_turn_id)
        for secret_id, art_id in event.cards:
            self.cards[secret_id] = Card(secret_id, ArtCard.get_by_id(art_id), player)
        player.library = Library([secret_id for secret_id, _ in event.cards])
        self.players[event.player_id] = player

    def handle_QuestionEvent(self, event):
        self.question = event.question
        self.answer = None

    def handle_PayEnergyEvent(self, event):
        player = self.players[event.player_id]
        player.energy_pool.pay(energy.Energy.parse(event.energy))
        event.new_total = str(player.energy_pool.energy)

    def handle_AddEnergyEvent(self, event):
        player = self.players[event.player_id]
        player.energy_pool.add(energy.Energy.parse(event.energy))
        event.new_total = str(player.energy_pool.energy)

    def handle_DrawCardEvent(self, event):
        player = self.players[event.player_id]
        card_popped_sid = player.library.pop_given(event.card_secret_id)
        assert card_popped_sid == event.card_secret_id
        card_popped = self.cards[card_popped_sid]
        card_popped.known_identity = event.card_id
        player.hand.add(card_popped)

    def handle_DrawEmptyEvent(self, event):
        player = self.players[event.player_id]
        player.has_drawn_from_empty_library = True

    def handle_ShuffleLibraryEvent(self, event):
        player = self.players[event.player_id]
        for card_sid in player.library:
            self.cards[card_sid].known_identity = None
        player.library.shuffle()

    def handle_StepEvent(self, event):
        self.active_player = self.players[event.active_player_id]
        assert self.active_player
        self.step = STEP[event.step]
        self.trigger(('BEGIN_OF_STEP', self.step.name))
        if self.step == STEP.UNTAP:
            for player in self.players.values():
                player.sources_played_this_turn = 0
            for permanent in self.battlefield:
                permanent.on_battlefield_at_begin_of_turn = True

    def handle_ClearPoolEvent(self, event):
        player = self.players[event.player_id]
        player.energy_pool.clear()

    def handle_PriorityEvent(self, event):
        if event.player_id is None:
            self.priority_player = None
        else:
            self.priority_player = self.players[event.player_id]

    def handle_PassedEvent(self, event):
        player = self.players[event.player_id]
        player.has_passed = True

    def handle_EnterTheBattlefieldEvent(self, event):
        if event.card_secret_id is not None:
            assert event.art_id is None
            card = self.cards[event.card_secret_id]
        else:
            card = Token(ArtCard.get_by_id(event.art_id), event.perm_id)
            assert card.token
        permanent = Permanent(event.perm_id, self, card, self.players[event.controller_id], self.objects_from_ids(event.choices))
        self.battlefield[permanent.perm_id] = permanent
        event.permanent = permanent.serialize_for(self.players[0])

    def handle_ExitTheBattlefieldEvent(self, event):
        del self.battlefield[event.perm_id]

    def handle_PutInGraveyardEvent(self, event):
        card = self.cards[event.card_secret_id]
        card.owner.graveyard.add(card)

    def handle_DiscardEvent(self, event):
        self.cards[event.card_secret_id].owner.hand.discard(self.cards[event.card_secret_id])
        self.cards[event.card_secret_id].owner.graveyard.add(self.cards[event.card_secret_id])

    def handle_PlaySourceEvent(self, event):
        player = self.players[event.player_id]
        player.hand.discard(self.cards[event.card_secret_id])
        player.sources_played_this_turn += 1

    def handle_CastSpellEvent(self, event):
        player = self.players[event.player_id]
        card = self.cards[event.card_secret_id]
        player.hand.discard(card)
        self.stack.append(Spell(event.stack_id, player, card, event.target))

    def handle_ActivateAbilityEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        ability = permanent.card.abilities[event.ability_index]
        controller = permanent.controller #TODO: move controller into the event
        choices = self.objects_from_ids(event.choices)
        self.stack.append(AbilityOnStack(event.stack_id, ability, choices, controller, permanent))

    def handle_StackEffectEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        self.stack.append(TriggerOnStack(event.stack_id, event.effect, permanent))

    def handle_CreateContinuousEffectEvent(self, event):
        self.continuous_effects[event.effect_id] = event

    def handle_CreateTriggerEvent(self, event):
        self.triggered_effects[event.trigger_id] = event

    def handle_EndContinuousEffectEvent(self, event):
        del self.continuous_effects[event.effect_id]

    def handle_EndTriggerEvent(self, event):
        del self.triggered_effects[event.trigger_id]

    def handle_ResolveEvent(self, event):
        tos_popped = self.stack.pop()
        assert tos_popped.stack_id == event.stack_id

    def handle_UntapEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.tapped = False

    def handle_TapEvent(self, event):
        permanent = self.battlefield[event.perm_id]
        permanent.tapped = True
        self.trigger(('TAP', event.perm_id))

    def handle_ResetPassEvent(self, event):
        for player in self.players.values():
            player.has_passed = False

    def handle_AttackEvent(self, event):
        player = self.players[event.player_id]
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
        player = self.players[event.player_id]
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

    def handle_ClearDamageEvent(self, event):
        for permanent in self.battlefield:
            permanent.damage.clear()

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
            if key == 'x':
                choices[key] = value
            elif value['type'] == 'player':
                choices[key] = self.players[value['player_id']]
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
            'players': [{'name': p.name} for p in self.players.values()],
            'events': [event.serialize() for event in self.event_log]
        }

    def trigger(self, trigger):
        self.triggers.append(trigger)
        print(self.triggers)




def start_game(game):
    assert False

def end_of_step(game):
    for player in game.players.values():
        yield ClearPoolEvent(player.player_id)
    yield PriorityEvent(None)

    if game.step == STEP.END_OF_COMBAT:
        for permanent in game.battlefield:
            yield RemoveFromCombatEvent(permanent.perm_id)

    if game.step == STEP.CLEANUP:
        yield StepEvent(STEP.UNTAP.name, game.active_player.next_in_turn_id)
    else:
        yield StepEvent(NEXT_STEP[game.step].name, game.active_player.player_id)

def game_events(game, skip_start):
    try:
        while True:
            if game.priority_player:
                while True:
                    yield from state_based_actions(game)
                    triggered_abilities = check_triggers(game)
                    yield ClearTriggerEvent()
                    if not triggered_abilities:
                        break
                    for tr_effect in triggered_abilities:
                        if isinstance(tr_effect, tuple):
                            (permanent, ab_idx, ability) = tr_effect
                            yield ActivateAbilityEvent(next(game.unique_ids), permanent.perm_id, ab_idx, {})
                        else:
                            yield StackEffectEvent(next(game.unique_ids), tr_effect.perm_id, tr_effect.effect, None)


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
                        yield PriorityEvent(game.priority_player.next_in_turn_id)
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
        yield ClearDamageEvent()
        yield from end_continuous_effects(game)
        yield from end_of_step(game)
    elif game.step == STEP.DECLARE_ATTACKERS:
        candidates = {next(game.unique_ids): permanent for permanent in
            game.battlefield.creatures.controlled_by(game.active_player)
            if TapCost().can_pay(permanent, None)
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
                if not candidates[i].has('stamina'):
                    yield TapEvent(candidates[i].perm_id)
                yield AttackEvent(candidates[i].perm_id, game.active_player.next_in_turn_id)
            yield from open_priority(game)
        else:
            yield StepEvent(STEP.END_OF_COMBAT.name, game.active_player.player_id)
    elif game.step == STEP.DECLARE_BLOCKERS:
        for player in game.players.values():
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
        yield StepEvent(STEP.SECOND_STRIKE_DAMAGE.name, game.active_player.player_id)
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
                yield PlayerDamageEvent(attacker.attacking.player_id, remaining_strength)
        yield from open_priority(game)
    else:
        yield from open_priority(game)

def lose_the_game(player):
    print(f'player {player.name} loses the game')
    assert False, 'not implemented'

def put_in_graveyard(game, permanent):
    yield ExitTheBattlefieldEvent(permanent.perm_id)
    for effect_id in list(game.continuous_effects.keys_by_perm_id(permanent.perm_id)):
        yield EndContinuousEffectEvent(effect_id)
    for trigger_id in list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)):
        yield EndTriggerEvent(trigger_id)
    if hasattr(permanent.card, 'secret_id'):
        yield PutInGraveyardEvent(permanent.card.secret_id)
    else:
        assert permanent.card.token

def end_continuous_effects(game):
    for effect_id in list(game.continuous_effects.keys_until_end_of_turn()):
        yield EndContinuousEffectEvent(effect_id)

def state_based_actions(game):
    for player in game.players.values():
        if player.life <= 0:
            yield PlayerLosesEvent(player.player_id)
            # TODO: losing should not end the game if it is a multiplayer game
            raise EndOfGameException
    for player in game.players.values():
        if player.has_drawn_from_empty_library:
            yield PlayerLosesEvent(player.player_id)
            # TODO: losing should not end the game if it is a multiplayer game
            raise EndOfGameException
    for creature in {c for c in game.battlefield.creatures if c.toughness <= 0}:
        yield from put_in_graveyard(game, creature)
    for creature in {c for c in game.battlefield.creatures
                     if c.total_damage_received >= c.toughness}:
        yield from put_in_graveyard(game, creature)
    for enchantment in {e for e in game.battlefield.enchantments
                        if 'enchanted' in e.choices
                        and e.choices['enchanted'].perm_id not in game.battlefield}:
        yield from put_in_graveyard(game, enchantment)

def check_triggers(game):
    has_triggered = []
    for trigger in game.triggers:
        for tr_effect in game.triggered_effects.values():
            if tuple(tr_effect.trigger) == tuple(trigger):
                has_triggered.append(tr_effect)

    return has_triggered


def open_priority(game):
    yield ResetPassEvent()
    yield PriorityEvent(game.active_player.player_id)


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
        yield DrawCardEvent(player.player_id, card, card_id)
    else:
        yield DrawEmptyEvent(player.player_id)

def can_block(blocker, attacker):
    if blocker.tapped:
        return False
    if (attacker.has('flying') and
            not blocker.has('intercept') and not blocker.has('flying')):
        return False
    return True

def can_play_source(player):
    return player.sources_played_this_turn == 0

def play_source(game, player, card):
    yield PlaySourceEvent(player.player_id, card.secret_id)
    yield EnterTheBattlefieldEvent(card.secret_id, None, player.player_id, next(game.unique_ids), {})

def player_action(game, player):
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

        for card in player.hand.of_types('creature', 'sorcery', 'enchantment'):
            if player.energy_pool.can_pay(card.cost.replace_variable(0)):
                add_choice([(cast_spell, (game, player, card), {})],
                    action='play', card_id=card.known_identity, text=f'cast {card.name}')

    for card in player.hand.of_types('instant'):
        if player.energy_pool.can_pay(card.cost.replace_variable(0)):
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
        yield PassedEvent(player.player_id)
    else:
        for func, arguments, kwarguments in actions[answer]:
            yield from func(*arguments, **kwarguments)

def activate_ability(game, ability, ab_idx, controller, permanent):
    choices = {}
    yield from make_choices(game, choices, ability.effect, controller, permanent)

    if ability.is_energy_ability:
        effect = Effect(ability.effect, game, game.objects_from_ids(choices), controller, permanent)
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

def choose_x(game, choices, max, controller):
    question_choices = {}
    for x in range(max+1):
        question_choices[next(game.unique_ids)] = {'action': 'choose_x', 'value':x}
    question = ChooseAction(game, controller, question_choices, 'choose_x')
    yield QuestionEvent(question)
    answer = game.answer
    assert answer in question_choices
    assert 'x' not in choices
    choices['x'] = question_choices[answer]['value']


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
        for player in game.players.values():
            yield {'player_id': player.player_id, 'type': 'player'}
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
