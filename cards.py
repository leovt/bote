from dataclasses import dataclass, field
import sqlite3
import energy
from abilities import ActivatableAbility, parse_cost, parse_effect

@dataclass(eq=False, frozen=True)
class RuleCard:
    name: str
    types: set
    subtypes: set
    abilities: list = field(default_factory=list)
    cost: energy.Energy = energy.ZERO
    token: bool = False
    toughness: int = 0
    strength: int = 0



@dataclass(eq=False, frozen=True)
class ArtCard:
    rule_card: object
    language: object = None
    image: object = None
    artist: object = None


@dataclass(eq=False, frozen=True)
class Card:
    art_card: object
    owner: object

    def __getattr__(self, attribute):
        return getattr(self.art_card.rule_card, attribute)

    def __str__(self):
        return self.art_card.rule_card.name

    def __repr__(self):
        return f'<Card name={self.name} owner={self.owner.name}>'

def load_db():
    global rule_cards
    rule_cards = {}
    with sqlite3.connect('cards.sqlite') as con:
        cur = con.cursor()
        cur.execute('select * from RuleCard')
        cur_list = con.cursor()
        for (id, name, cost, token, strength, toughness) in cur:
            print(id, name)
            cur_list.execute('select name from CardTypes where card_id=?', (id,))
            types = [x[0] for x in cur_list]
            cur_list.execute('select name from CardSubtypes where card_id=?', (id,))
            subtypes = [x[0] for x in cur_list]
            cur_list.execute('select cost, effect, energy_ability from ActivatableAbility where card_id=?', (id,))
            abilities = [ActivatableAbility(parse_cost(c), parse_effect(e), bool(ea))
                         for (c, e, ea) in cur_list]
            rule_cards[id] = RuleCard(name, types, subtypes, abilities,
                                        energy.Energy.parse(cost) if cost else None,
                                        bool(token),
                                        toughness,
                                        strength)

load_db()
