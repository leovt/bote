import itertools
import lark

from keywords import KEYWORDS
RESERVED_LABELS = ['enchanted', 'x']

import energy

from event import (AddEnergyEvent,
                   PayEnergyEvent,
                   PlayerDamageEvent,
                   DamageEvent,
                   CreateContinuousEffectEvent,
                   EnterTheBattlefieldEvent,
                   CreateTriggerEvent,
                   UntapEvent,
                  )
from rules_actions import put_in_graveyard_events

def _parser():
    with open('grammar.txt') as grammar_txt:
        source = grammar_txt.read()
    source += f'\nkeyword: /{"|".join(KEYWORDS)}/\n'
    return lark.Lark(source, parser="lalr")
_parser = _parser()

test_effect = '''
    all .creature has +3/-3 and not flying and
    controlled by you until end of turn; chosen
    .player[1] gets 5 damage; add {3}{R}{R}{R} to [1] energy pool'''

class ChosenSpecVisitor(lark.Visitor):
    def __init__(self):
        lark.Visitor.__init__(self)
        self._def = {}
        self._ids = (f'@{i}' for i in itertools.count(1))

    def chosen_spec(self, tree):
        if len(tree.children) == 2 and tree.children[1] is not None:
            assert tree.children[1].data == 'chosen_label'
            label = str(tree.children[1].children[0])
            if label in self._def:
                raise ValueError(f'duplicate label [{label}] for chosen object')
            if label in RESERVED_LABELS:
                raise ValueError(f'label [{label}] is reserved')
        else:
            label = next(self._ids)
            tree.children.append(lark.Tree('chosen_label', [label]))
        self._def[label] = tree.children[0]
        tree.data = 'chosen_ref'
        tree.children = [label]

    def any(self, tree):
        if len(tree.children) == 2 and tree.children[1] is not None:
            assert tree.children[1].data == 'chosen_label'
            label = str(tree.children[1].children[0])
            if label in self._def:
                raise ValueError(f'duplicate label [{label}] for chosen object')
            if label in RESERVED_LABELS:
                raise ValueError(f'label [{label}] is reserved')
            self._def[label] = tree.children[0]
            tree.children = tree.children[:1]

    def enchanted(self, tree):
        if 'enchanted' in self._def:
            raise ValueError(f'duplicate specification of enchanted object')
        self._def['enchanted'] = tree.children[0]
        tree.data = 'chosen_ref'
        tree.children = ['enchanted']

    def chosen_ref(self, tree):
        label = str(tree.children[0])
        if label not in self._def:
            raise ValueError(f'undefined label [{label}] for chosen object')

class Unparser(lark.Transformer):
    def __init__(self, _def):
        lark.Transformer.__init__(self)
        self._def = dict(_def)

    def __default__(self, data, children, meta):
        assert False, f'{self.__class__.__name__}.{data} not implemented'

    def _modifier_text(self, modifier):
        if modifier[0] == 'delta_stat':
            return f'{modifier[1]:+d}/{modifier[2]:+d}'
        if modifier[0] == 'set_stat':
            return f'{modifier[1]}/{modifier[2]}'
        if modifier[0] == 'add_keyword':
            return modifier[1]
        if modifier[0] == 'remove_keyword':
            return f'not {modifier[1]}'
        if modifier[0] == 'change_controller':
            return f'controlled by {modifier[1]}'
        assert False, f'unknown modifier {modifier}'

    def _modifier_list_text(self, modifiers):
        return ' and '.join(
            self._modifier_text(modifier)
            for modifier in modifiers
        )

    def until_end_of_turn(self, args):
        return 'until end of turn'

    def color(self, args):
        return args[0]

    def color_spec(self, args):
        if len(args) == 1:
            return args[0]
        return f'color({",".join(args)})'

    def type(self, args):
        return args[0]

    def type_spec(self, args):
        if len(args) == 1:
            return args[0]
        return f'type({",".join(args)})'

    def subtype(self, args):
        return args[0]

    def subtype_spec(self, args):
        if len(args) == 1:
            return args[0]
        return f'subtype({",".join(args)})'

    def other_spec(self, args):
        return 'other'

    def positive_selector(self, args):
        return '.' + args[0]

    def negative_selector(self, args):
        return '!' + args[0]

    def keyword(self, args):
        return args[0]

    def modifier_list(self, args):
        return ' and '.join(args)

    def stat_mod(self, args):
        return args[0]+'/'+args[1]

    def increase_stat(self, args):
        return '+' + args[0]

    def decrease_stat(self, args):
        return '-' + args[0]

    def set_stat(self, args):
        return args[0]

    def add_keyword(self, args):
        return args[0]

    def remove_keyword(self, args):
        return 'not ' + args[0]

    def change_controller(self, args):
        return 'controlled by ' + args[0]

    def add_energy_effect(self, args):
        return f'add {args[0]} to {args[1]} energy pool'

    def this(self, args):
        return 'this'

    def triggered_effect(self, args):
        return f'when {args[0]}: {args[1]}'

    def tap_trigger(self, args):
        return f'{args[0]} gets tapped'

    def step_begin_trigger(self, args):
        return f'{args[0].lower()} step begins'

    def enters_battlefield_trigger(self, args):
        return 'this enters the battlefield'

    def turn_begin_trigger(self, args):
        return 'your turn begins'

    def effect_controller(self, args):
        return 'you'

    def any(self, args):
        return f'any {args[0]}'

    def cast_trigger(self, args):
        return f'{args[0]} cast {args[1]}'

    def chosen_ref(self, args):
        label = str(args[0])
        if label in self._def:
            ret = 'chosen ' + self.transform(self._def[label])
            del self._def[label]
        else:
            ret = ''
        if not label.startswith('@'):
            ret += f' [{label}]'
        return ret

    def chosen_spec(self, args):
        assert False, 'all chosen_spec must have been removed from the tree'

    def all(self, args):
        return f'all {args[0]}'

    def continuous_effect(self, args):
        suffix = ''
        if len(args) > 2 and args[2]:
            suffix = f' {args[2]}'
        return f'{args[0]} has {self._modifier_list_text(args[1])}{suffix}'

    def damage_effect(self, args):
        return f'{args[0]} gets {args[1]} damage'

    def create_token_effect(self, args):
        return f'create {args[0]} ({args[1]}) token'

    def effects(self, args):
        return '; '.join(args)

    def selector(self, args):
        return ''.join(args)

    def number(self, args):
        return args[0]

    signed_number = number

    def start(self, args):
        return args[0]

    def energy(self, args):
        return ''.join(args)


class EffectTemplate:
    def __init__(self, choices, tree):
        self.choices = choices
        self.tree = tree

    @classmethod
    def parse(cls, src):
        tree = _parser.parse(src)
        visitor = ChosenSpecVisitor()
        visitor.visit_topdown(tree)
        choices = visitor._def
        transformer = Sequencer()
        tree = transformer.transform(tree)
        return cls(choices, tree)

    def unparse(self):
        return Unparser(self.choices).transform(self.tree)

    def is_energy_only(self):
        effect_types = {
            'add_energy_effect',
            'continuous_effect',
            'create_token_effect',
            'damage_effect',
            'destruction_effect',
        }
        results = {
            subtree.data
            for subtree in self.tree.iter_subtrees()
            if subtree.data in effect_types
        }
        return results == {'add_energy_effect'}


class Sequencer(lark.Transformer):
    '''transform the parse tree into a sequence of execution-templates'''
    def number(self, args):
        return int(args[0], 10)

    signed_number = number

    def energy(self, args):
        return str(args[0])

    def set_stat(self, args):
        return ['set_stat', args[0], args[1]]

    def delta_stat(self, args):
        return ['delta_stat', args[0], args[1]]

    def modifier_list(self, args):
        return args

    def keyword(self, args):
        return str(args[0])

    def add_keyword(self, args):
        return ['add_keyword', args[0]]

    def remove_keyword(self, args):
        return ['remove_keyword', args[0]]

    def change_controller(self, args):
        return ['change_controller', args[0]]

    def step(self, args):
        return args[0].upper()


class Executor(lark.Transformer):
    def __init__(self, context):
        lark.Transformer.__init__(self)
        self._context = context

    def __default__(self, data, children, meta):
        print(f'{self.__class__.__name__}.{data} not implemented')
        return lark.Transformer.__default__(self, data, children, meta)

    def add_energy_effect(self, args):
        energy, player = args
        return [AddEnergyEvent(player.player_id, energy)]

    def destruction_effect(self, args):
        return [
            event
            for permanent in self.iter_objects(args[0])
            for event in put_in_graveyard_events(self._context.game, permanent)
        ]

    def damage_effect(self, args):
        return [
            PlayerDamageEvent(obj.player_id, args[1])
            if hasattr(obj, 'name')
            else DamageEvent(obj.perm_id, args[1])
            for obj in self.iter_objects(args[0])
        ]

    def create_token_effect(self, args):
        count, art_id = args
        return [EnterTheBattlefieldEvent(None, art_id,
                    self._context.controller.player_id,
                    next(self._context.game.unique_ids), {})
                for _ in range(count)]



    def variable(self, args):
        return self._context.choices['x']

    def signed_variable(self, args):
        sign = {'+': 1, '-': -1}[args[0][0]]
        return sign * self._context['x']

    def this(self, args):
        return self._context.permanent

    def effect_controller(self, args):
        return self._context.controller

    def effects(self, args):
        return [event for effect in args for event in effect]

    def start(self, args):
        return args[0]

    def continuous_effect(self, args):
        effect_id = next(self._context.game.unique_ids)
        perm_id = self._context.permanent.perm_id if self._context.permanent else None
        until_end_of_turn = args[-1] == 'until_end_of_turn'
        if args[0] == 'prevent_battle_damage':
            return [CreateContinuousEffectEvent(effect_id, perm_id, [], [['prevent_battle_damage']], until_end_of_turn)]
        objects = [
            obj.perm_id
            for obj in self.iter_objects(args[0])
            if obj.perm_id in self._context.game.battlefield
        ]
        if not objects:
            return []
        modifiers = [self.resolve_modifier(modifier) for modifier in args[1]]
        return [CreateContinuousEffectEvent(effect_id, perm_id, objects, modifiers, until_end_of_turn)]

    def prevent_battle_damage(self, args):
        return 'prevent_battle_damage'

    def until_end_of_turn(self, args):
        return 'until_end_of_turn'

    def untap_effect(self, args):
        return [
            UntapEvent(permanent.perm_id)
            for permanent in self.iter_objects(args[0])
        ]

    def pay_or_destroy_effect(self, args):
        cost, destruction_events = args
        parsed_cost = energy.Energy.parse(cost)
        if self._context.controller.energy_pool.can_pay(parsed_cost):
            return [PayEnergyEvent(self._context.controller.player_id, cost)]
        return destruction_events

    def iter_objects(self, objects):
        if isinstance(objects, list):
            return objects
        return [objects]

    def resolve_modifier(self, modifier):
        if modifier[0] == 'change_controller':
            controller = modifier[1]
            if isinstance(controller, lark.Tree) and controller.data == 'effect_controller':
                return ['change_controller', self._context.controller.player_id]
        return modifier

    def triggered_effect(self, args):
        perm_id = None
        if self._context.permanent:
            perm_id = self._context.permanent.perm_id
        trigger_id = next(self._context.game.unique_ids)
        #TODO: Problem: triggered events should be kept in unexecuted form.
        return [CreateTriggerEvent(trigger_id, perm_id, args[0], [evt.serialize() for evt in args[1]])]

    def chosen_ref(self, args):
        return self._context.choices[args[0]]

    def controller_of(self, args):
        return args[0].controller

    def tap_trigger(self, args):
        return ['TAP', args[0].perm_id]

    def damage_trigger(self, args):
        return ('DAMAGE', args[0].perm_id)

    def blocked_by_trigger(self, args):
        return ('BLOCKED_BY', args[0].perm_id, args[1])

    def step_begin_trigger(self, args):
        return ('BEGIN_OF_STEP', args[0])

    def turn_begin_trigger(self, args):
        return ('BEGIN_OF_TURN', self._context.controller.player_id)

    def enters_battlefield_trigger(self, args):
        return ('ENTERS_THE_BATTLEFIELD', args[0].perm_id)

    def all(self, args):
        return [
            obj
            for obj in list(self._context.game.players.values()) + list(self._context.game.battlefield)
            if self.object_matches_selector(obj, args[0])
        ]

    def object_matches_selector(self, obj, selector):
        for operator, specification in selector:
            matches = self.object_matches_spec(obj, specification)
            if operator == 'INCLUDE' and not matches:
                return False
            if operator == 'EXCLUDE' and matches:
                return False
        return True

    def object_matches_spec(self, obj, specification):
        kind, values = specification
        if kind == 'TYPE':
            obj_types = {'player'} if hasattr(obj, 'player_id') else obj.types
            return bool(set(values) & obj_types)
        if kind == 'KEYWORD':
            return not hasattr(obj, 'player_id') and any(obj.has(keyword) for keyword in values)
        if kind == 'SUBTYPE':
            return not hasattr(obj, 'player_id') and bool(set(values) & obj.subtypes)
        if kind == 'COLOR':
            return False
        if kind == 'OTHER':
            return obj is not self._context.permanent
        return False

    def type(self, args):
        return str(args[0])

    def color(self, args):
        return str(args[0])

    def subtype(self, args):
        return str(args[0])

    def type_spec(self, args):
        return ('TYPE', tuple(args))

    def color_spec(self, args):
        return ('COLOR', tuple(args))

    def subtype_spec(self, args):
        return ('SUBTYPE', tuple(args))

    def keyword_spec(self, args):
        return ('KEYWORD', tuple(args))

    def other_spec(self, args):
        return ('OTHER', ())

    def positive_selector(self, args):
        return ('INCLUDE', args[0])

    def negative_selector(self, args):
        return ('EXCLUDE', args[0])

    def selector(self, args):
        return tuple(args)

    def any(self, args):
        accepted_types = []
        for operator, specification in args[0]:
            if operator != 'INCLUDE':
                raise ValueError('cast trigger any selectors only support included types')
            kind, values = specification
            if kind != 'TYPE':
                raise ValueError('cast trigger any selectors only support card types')
            accepted_types.extend(values)
        return ('ANY', tuple(accepted_types))

    def cast_trigger(self, args):
        caster, cast_filter = args
        assert cast_filter[0] == 'ANY', cast_filter
        return ('CAST', caster.player_id, cast_filter[1])

class Effect:
    def __init__(self, template, game, choices, controller, permanent):
        self.template = template
        self.game = game
        self.controller = controller
        self.permanent = permanent
        self.choices = choices
        assert set(self.choices) >= set(self.template.choices), (set(self.choices), set(self.template.choices))

    def execute(self):
        return Executor(self).transform(self.template.tree)


class ContinuousEffect:
    def __init__(self, game, parse_tree, controller, permanent):
        '''
            game: the Game object
            parse_tree: the parse tree of the continuous_effect rule in the grammar
            controller: the controller of the effect
            permanent: if the effect is a rule on a permanent (e.g. enchantment)
        '''
        self.game = game
        self.controller = controller
        self.permanent = permanent
        assert parse_tree.data == 'continuous_effect'

        try:
            print(parse_tree.pretty())
        except:
            print(parse_tree)

        if len(parse_tree.children) == 3:
            assert parse_tree.children[2].data == 'until_end_of_turn'
            self.until_end_of_turn = True
        else:
            self.until_end_of_turn = False


if __name__ == '__main__':
    e = EffectTemplate.parse(test_effect)
    up = e.unparse()
    f = EffectTemplate.parse(up)
    assert f.unparse() == up
