from dataclasses import dataclass, field

import energy


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
        return f'{self.name} @{self.owner}'
