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

def ask_choice(question, choices, multiple):
    text = choices_text(question, choices)

    def parse_single(answer):
        ans = int(answer)
        if 1 <= ans <= len(choices):
            return ans-1
        else:
            raise ValueError()

    def parse_multiple(ans):
        ans = ans.strip()
        if not ans:
            return set()
        ans = [int(a.strip())-1 for a in ans.split(',')]
        if all(0 <= a < len(choices) for a in ans) and len(set(ans)) == len(ans):
            return ans
        else:
            raise ValueError()

    if multiple:
        parse = parse_multiple
    else:
        parse = parse_single

    return ask(text, parse, '>')


def test():
    CHOICES = ['Apples', 'Pears', 'Tomatoes']
    ans = ask_choice('Please choose a fruit:', CHOICES, False)
    print(f'You chose {CHOICES[ans]}.')
    ans = ask_choice('Please choose some fruit', CHOICES, True)
    ans = {CHOICES[x] for x in ans}
    print(f'You chose {ans}.')

if __name__ == '__main__':
    test()
