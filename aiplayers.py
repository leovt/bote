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
        answer = []
        for ch in question.choices:
            ans = list(range(len(ch['blockers'])))
            random.shuffle(ans)
            answer.append(ans)
        return answer

    assert False, question
