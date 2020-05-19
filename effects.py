import itertools
import lark

with open('grammar.txt') as grammar_txt:
    _parser = lark.Lark(grammar_txt.read(), parser="lalr")

test_effect = '''
    all .creature has +3/-3 and not flying and
    controlled by you until end of turn; chosen
    .player[1] gets 5 damage'''

class ChosenSpecVisitor(lark.Visitor):
    def __init__(self):
        lark.Visitor.__init__(self)
        self._def = {}
        self._ids = (f'@{i}' for i in itertools.count(1))

    def chosen_spec(self, tree):
        print('---------------------------')
        print(tree)
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
        print('---------------------------')

    def chosen_ref(self, tree):
        label = str(tree.children[0])
        if label not in self._def:
            raise ValueError(f'undefined label [{label}] for chosen object')

def parse_effect(src):
    tree = _parser.parse(src)
    print(tree.pretty())
    t = ChosenSpecVisitor()
    t.visit(tree)
    print(t._def)
    print(tree.pretty())



if __name__ == '__main__':
    parse_effect(test_effect)
