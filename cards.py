from dataclasses import dataclass, field
import functools
import yaml
import energy
from abilities import ActivatableAbility, TriggeredAbility, parse_cost, parse_effect, parse_trigger

def instance_loader(loader):
    cache = {}
    @functools.wraps(loader)
    def cached_loader(instance_id):
        if instance_id in cache:
            return cache[instance_id]
        instance = loader(instance_id)
        cache[instance_id] = instance
        return instance
    cached_loader._cache = cache
    return cached_loader

@dataclass(eq=False, frozen=True)
class RuleCard:
    card_id: int
    types: set
    subtypes: set
    abilities: list = field(default_factory=list)
    cost: energy.Energy = energy.ZERO
    token: bool = False
    toughness: int = 0
    strength: int = 0

    @property
    def name(self):
        ''' return the english name (for debug purpose only) '''
        return _cards[self.card_id]['names']['en']

    @staticmethod
    @instance_loader
    def get_by_id(card_id):
        spec = _cards[card_id]
        abilities = []
        for ab_spec in spec.get('abilities', []):
            if 'cost' in ab_spec:
                abilities.append(
                    ActivatableAbility(parse_cost(ab_spec['cost']),
                                       parse_effect(ab_spec['effect']),
                                       ab_spec.get('energy_ability', False)))
            if 'trigger' in ab_spec:
                abilities.append(TriggeredAbility(
                    parse_trigger(ab_spec['trigger']),
                    parse_effect(ab_spec['effect'])))

            else:
                abilities.append(ab_spec)

        return RuleCard(
            card_id = spec['card_id'],
            types = {spec['type']},
            subtypes = spec.get('subtypes', {}),
            cost = energy.Energy.parse(spec.get('cost', '')),
            toughness = spec.get('toughness', 0),
            strength = spec.get('strength', 0),
            token = spec.get('token', False),
            abilities = abilities)

    def has_keyword_ability(self, keyword):
        return any(ability.get('keyword') == keyword for ability in self.abilities if isinstance(ability, dict))


@dataclass(eq=False, frozen=True)
class ArtCard:
    art_id: int
    rule_card: object

    @staticmethod
    @instance_loader
    def get_by_id(card_id):
        spec = _art_cards[card_id]
        return ArtCard(art_id=spec['art_id'],
                       rule_card=RuleCard.get_by_id(spec['card_id']))


@dataclass(eq=False)
class Card:
    art_card: object
    owner: object
    known_identity: str = None

    def __getattr__(self, attribute):
        return getattr(self.art_card.rule_card, attribute)

    def __str__(self):
        return self.art_card.rule_card.name

    def __repr__(self):
        return f'<Card name={self.name} owner={self.owner.name}>'

    def serialize_for(self, player):
        return {'art_id': self.art_card.art_id,
                'card_id': self.known_identity,
                'name': self.name,
                'owner': self.owner.serialize_for(player),
                'url': f'/card/svg/{self.art_card.art_id}',
                }


def art_card_spec(art_id):
    card = _art_cards.get(art_id)
    if not card:
        return None
    return dict(card)


def card_spec(card_id):
    card = _cards.get(card_id)
    if not card:
        return None
    return dict(card)


def load_yaml():
    with open('cards.yaml', encoding='utf8') as stream:
        data = yaml.safe_load(stream)

    types = data['types']
    cards = {}
    art_cards = {}

    for card_id, card in data['cards'].items():
        assert id not in cards
        card['card_id'] = card_id
        cards[card_id] = card
        typespec = types[card['type']]
        for subtype in cards.get('subtypes', []):
            assert subtype in typespec['subtypes']

        for art_id, art in card.get('art', {}).items():
            assert art_id not in art_cards
            art['art_id'] = art_id
            art['card_id'] = card_id
            art_cards[art_id] = art

    return types, cards, art_cards

def all():
    return _art_cards.values()

_types, _cards, _art_cards = load_yaml()
del load_yaml
