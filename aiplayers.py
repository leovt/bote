import random

def random_answer(question):
    if question.__class__.__name__ == "ChooseAction":
        return random.choice(list(question.choices))

    if question.__class__.__name__ == "DeclareAttackers":
        if not question.choices:
            return []
        answer = list(question.choices.keys())
        random.shuffle(answer)
        return answer[:random.randrange(len(answer))]

    if question.__class__.__name__ == "DeclareBlockers":
        answer = {}
        for i, ch in question.choices.items():
            if random.random() > 0.7:
                answer[i] = random.choice(list(ch['attackers']))
        return answer

    if question.__class__.__name__ == "OrderBlockers":
        answer = {}
        for key, ch in question.choices.items():
            ans = list(ch['blockers'].keys())
            random.shuffle(ans)
            answer[key] = ans
        return answer

    assert False, question
