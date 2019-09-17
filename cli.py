def ask(text, parse, prompt):
    while True:
        print(text)
        for _retry in range(3):
            try:
                return parse(input(prompt))
            except ValueError:
                pass


def choices_text(question, choices):
    number_width = len(str(len(choices))) # width of number
    return '\n'.join(
        [question] +
        [f'{i:{number_width}d}: {choice}'
         for i, choice in enumerate(choices, 1)])


def ask_question(question):

    text = choices_text(question.__class__.__name__, list(question.choices.values()))

    def parse(ans):
        return list(question.choices.keys())[int(ans)-1]

    if question.__class__.__name__ == 'DeclareAttackers':
        if not question.choices:
            return []
        def parse(ans):
            keys = list(question.choices.keys())
            return [keys[int(a)-1] for a in ans.split(',') if a]
    elif question.__class__.__name__ == 'DeclareBlockers':
        letters = 'abcdefghijklmnopqrstuvwxyz'
        text = ('For each potential blocker choose which attacker to block '
                'in the form 2:a, 3:c\n')
        text += '\n'.join(
            f'{b}: {ch["candidate"]} can block\n'
            + '\n'.join(f'    {letters[a]}: {attacker}'
                        for a, attacker in enumerate(ch['attackers'].values()))
            for b, ch in enumerate(question.choices.values(), 1)
        )
        def parse(ans):
            ret = {}
            for chunk in ans.split(','):
                chunk=chunk.strip()
                if not chunk:
                    continue
                b, a = chunk.split(':')
                b = list(question.choices.keys())[int(b.strip()) - 1]
                a = letters.index(a.strip())
                a = list(question.choices[b]['attackers'].keys())[a]
                if b in ret:
                    raise ValueError
                ret[b] = a
            return ret

    def parse_and_validate(ans):
        ans = parse(ans)
        if question.validate(question.player, ans):
            return ans
        print(repr(ans), 'is not valid.')
        raise ValueError

    return ask(text, parse_and_validate, f'{question.__class__.__name__}>')
