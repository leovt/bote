import itertools
import lark

from keywords import KEYWORDS
RESERVED_LABELS = ['enchanted', 'x']

from event import (AddEnergyEvent,
                   ExitTheBattlefieldEvent,
                   PutInGraveyardEvent,
                   PlayerDamageEvent,
                   DamageEvent,
                   CreateContinuousEffectEvent,
                   EnterTheBattlefieldEvent,
                   CreateTriggerEvent,
                  )

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
        if len(tree.children) == 2:
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

    def effect_controller(self, args):
        return 'you'

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
        return f'{args[0]} has {args[1]} {args[2]}'

    def damage_effect(self, args):
        return f'{args[0]} gets {args[1]} damage'

    def effects(self, args):
        return '; '.join(args)

    def selector(self, args):
        return args[0]

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
        visitor.visit(tree)
        choices = visitor._def
        transformer = Sequencer()
        tree = transformer.transform(tree)
        return cls(choices, tree)

    def unparse(self):
        return Unparser(self.choices).transform(self.tree)


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
        # TODO: Problem: does not perform all the checks as Game.put_in_graveyard
        permanent = args[0]
        return [ExitTheBattlefieldEvent(permanent.perm_id),
                PutInGraveyardEvent(permanent.card.secret_id)]

    def damage_effect(self, args):
        print(args)
        if hasattr(args[0], 'name'):
            return [PlayerDamageEvent(args[0].player_id, args[1])]
        else:
            return [DamageEvent(args[0].perm_id, args[1])]

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
        perm_id = None
        if self._context.permanent:
            perm_id = self._context.permanent.perm_id
        objects = [args[0].perm_id]
        modifiers = args[1]
        until_end_of_turn = False
        if len(args)>2:
            assert args[2].data == 'until_end_of_turn'
            until_end_of_turn = True
        return [CreateContinuousEffectEvent(effect_id, perm_id, objects, modifiers, until_end_of_turn)]

    def triggered_effect(self, args):
        trigger_id = next(self._context.game.unique_ids)
        perm_id = None
        if self._context.permanent:
            perm_id = self._context.permanent.perm_id
        #TODO: Problem: triggered events should be kept in unexecuted form.
        return [CreateTriggerEvent(trigger_id, perm_id, args[0], [evt.serialize() for evt in args[1]])]

    def chosen_ref(self, args):
        return self._context.choices[args[0]]

    def controller_of(self, args):
        return args[0].controller

    def tap_trigger(self, args):
        return ['TAP', args[0].perm_id]

    def step_begin_trigger(self, args):
        return ('BEGIN_OF_STEP', args[0])

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
