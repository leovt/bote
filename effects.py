import itertools
import lark

from event import AddEnergyEvent
import energy

with open('grammar.txt') as grammar_txt:
    _parser = lark.Lark(grammar_txt.read(), parser="lalr")

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
        else:
            label = next(self._ids)
            tree.children.append(lark.Tree('chosen_label', [label]))
        self._def[label] = tree.children[0]
        tree.data = 'chosen_ref'
        tree.children = [label]

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
        t = ChosenSpecVisitor()
        t.visit(tree)
        return cls(t._def, tree)

    def unparse(self):
        return Unparser(self.choices).transform(self.tree)


class Executor(lark.Transformer):
    def __init__(self, context):
        lark.Transformer.__init__(self)
        self._context = context

    def __default__(self, data, children, meta):
        print(f'{self.__class__.__name__}.{data} not implemented')
        return lark.Transformer.__default__(self, data, children, meta)

    def add_energy_effect(self, args):
        energy, player = args
        return [AddEnergyEvent(player, energy)]

    def energy(self, args):
        return args[0]

    def effect_controller(self, args):
        return self._context.controller

    def effects(self, args):
        return [event for effect in args for event in effect]

    def start(self, args):
        return args[0]

class Effect:
    def __init__(self, template, choices, controller, permanent):
        self.template = template
        self.controller = controller
        self.permanent = permanent
        self.choices = choices
        assert set(self.choices) == set(self.template.choices)

    def execute(self):
        return Executor(self).transform(self.template.tree)


if __name__ == '__main__':
    e = EffectTemplate.parse(test_effect)
    up = e.unparse()
    f = EffectTemplate.parse(up)
    assert f.unparse() == up
