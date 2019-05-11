class Event:
    def __init__(self, event_id, *args):
        self.event_id = event_id
        self.args = args

    def __str__(self):
        return f'{self.event_id} ({" ".join(map(str, self.args))})'
