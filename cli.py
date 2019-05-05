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

def ask_choice(question, choices):
    text = choices_text(question, choices)

    def parse(answer):
        ans = int(answer)
        if 1 <= ans <= len(choices):
            return ans-1
        else:
            raise ValueError()

    return ask(text, parse, '>')

def ask_multiple(question, choices):
    text = choices_text(question, choices)

    def parse(ans):
        ans = ans.strip()
        if not ans:
            return set()
        ans = {int(a.strip())-1 for a in ans.split(',')}
        if all(0 <= a < len(choices) for a in ans):
            return ans
        else:
            raise ValueError()

    return ask(text, parse, 'Enter choices separated by comma >')


def test():
    CHOICES = ['Apples', 'Pears', 'Tomatoes']
    ans = ask_choice('Please choose a fruit:', CHOICES)
    print(f'You chose {CHOICES[ans]}.')
    ans = ask_multiple('Please choose some fruit', CHOICES)
    ans = {CHOICES[x] for x in ans}
    print(f'You chose {ans}.')

if __name__ == '__main__':
    test()
