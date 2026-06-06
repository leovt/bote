import argparse
import contextlib
from collections import Counter
import io
import logging
import random
import sys
import traceback
import pdb

from aiplayers import random_answer
from cards import ArtCard, RuleCard
from dummy_deck import GREEN_TEST_DECK, RED_TEST_DECK, TEST_DECK
from event import (
    ActivateAbilityEvent,
    AddEnergyEvent,
    CastSpellEvent,
    CreateContinuousEffectEvent,
    CreateTriggerEvent,
    DamageEvent,
    EnterTheBattlefieldEvent,
    PlaySourceEvent,
    PlayerDamageEvent,
    PlayerLosesEvent,
    StackEffectEvent,
)
from state import Game


sys.setrecursionlimit(50)

DECKS = {
    'test': TEST_DECK,
    'red': RED_TEST_DECK,
    'green': GREEN_TEST_DECK,
}

EFFECT_EVENT_TYPES = (
    AddEnergyEvent,
    CreateContinuousEffectEvent,
    CreateTriggerEvent,
    DamageEvent,
    EnterTheBattlefieldEvent,
    PlayerDamageEvent,
    StackEffectEvent,
)


class GameRunError(Exception):
    def __init__(self, original_error, game, deserialized_game=None):
        super().__init__(str(original_error))
        self.original_error = original_error
        self.game = game
        self.deserialized_game = deserialized_game
        self.traceback = ''.join(
            traceback.format_exception(
                type(original_error),
                original_error,
                original_error.__traceback__,
            )
        )


class Coverage:
    def __init__(self, *decks):
        self.deck_card_ids = {
            ArtCard.get_by_id(art_id).rule_card.card_id
            for deck in decks
            for art_id in deck
        }
        self.games = 0
        self.complete_games = 0
        self.wins = Counter()
        self.event_counts = Counter()
        self.cards_played = Counter()
        self.cards_entered = Counter()
        self.card_effects_seen = Counter()
        self.ability_activations = Counter()
        self.keyword_cards_seen = Counter()
        self.tokens_created = Counter()
        self.effect_events = Counter()
        self.failures = []
        self.max_events = 0

    def record_game(self, game, complete=True):
        self.games += 1
        if complete:
            self.complete_games += 1
            self.record_winner(game)
        self.max_events = max(self.max_events, len(game.event_log))

        for event in game.event_log:
            self.event_counts[event.__class__.__name__] += 1

            if isinstance(event, (CastSpellEvent, PlaySourceEvent)):
                card = game.cards[event.card_secret_id]
                card_id = card.art_card.rule_card.card_id
                self.cards_played[card_id] += 1
                if card.effect:
                    self.card_effects_seen[card_id] += 1
                for ability in card.abilities:
                    if isinstance(ability, dict) and 'keyword' in ability:
                        self.keyword_cards_seen[(card_id, ability['keyword'])] += 1

            if isinstance(event, EnterTheBattlefieldEvent):
                if event.card_secret_id is not None:
                    card = game.cards[event.card_secret_id]
                    self.cards_entered[card.art_card.rule_card.card_id] += 1
                else:
                    token_card = ArtCard.get_by_id(event.art_id).rule_card
                    self.tokens_created[token_card.card_id] += 1

            if isinstance(event, ActivateAbilityEvent):
                permanent = getattr(event, 'permanent', None)
                if permanent:
                    card_id = ArtCard.get_by_id(permanent['card']['art_id']).rule_card.card_id
                else:
                    card_id = 'unknown'
                self.ability_activations[(card_id, event.ability_index)] += 1

            if isinstance(event, EFFECT_EVENT_TYPES):
                self.effect_events[event.__class__.__name__] += 1

    def record_winner(self, game):
        for event in reversed(game.event_log):
            if isinstance(event, PlayerLosesEvent):
                loser = game.players[event.player_id]
                winner = game.players[loser.next_in_turn_id]
                self.wins[winner.name] += 1
                return

    def record_failure(self, game_index, error):
        self.failures.append((game_index, error.__class__.__name__, str(error)))

    def print_report(self):
        print(f'Ran {self.games} games.')
        print(f'Completed games: {self.complete_games}')
        print(f'player1 wins: {self.wins["player1"]}')
        print(f'player2 wins: {self.wins["player2"]}')
        print(f'Max events in one game: {self.max_events}')
        if self.failures:
            print(f'Failures: {len(self.failures)}')
            for game_index, error_name, message in self.failures[:10]:
                print(f'  game {game_index}: {error_name}: {message}')
        else:
            print('Failures: 0')

        print()
        self._print_card_section('Cards played', self.cards_played)
        self._print_card_section('Cards entered battlefield', self.cards_entered)
        self._print_card_section('Cards with effects exercised', self.card_effects_seen)
        self._print_keyword_section()
        self._print_ability_section()
        self._print_card_section('Tokens created', self.tokens_created)
        self._print_counter_section('Effect/event categories exercised', self.effect_events)

        missing = sorted(self.deck_card_ids - set(self.cards_played))
        if missing:
            print()
            print('Deck cards never played:')
            for card_id in missing:
                print(f'  {self._card_label(card_id)}')

    def _print_card_section(self, title, counter):
        print()
        print(f'{title}:')
        if not counter:
            print('  none')
            return
        for card_id, count in sorted(counter.items(), key=lambda item: str(item[0])):
            print(f'  {self._card_label(card_id)}: {count}')

    def _print_ability_section(self):
        print()
        print('Activated abilities exercised:')
        if not self.ability_activations:
            print('  none')
            return
        for (card_id, ability_index), count in sorted(self.ability_activations.items(), key=lambda item: str(item[0])):
            print(f'  {self._card_label(card_id)} ability #{ability_index}: {count}')

    def _print_keyword_section(self):
        print()
        print('Keyword/static abilities seen on played cards:')
        if not self.keyword_cards_seen:
            print('  none')
            return
        for (card_id, keyword), count in sorted(self.keyword_cards_seen.items(), key=lambda item: str(item[0])):
            print(f'  {self._card_label(card_id)} {keyword}: {count}')

    def _print_counter_section(self, title, counter):
        print()
        print(f'{title}:')
        if not counter:
            print('  none')
            return
        for name, count in sorted(counter.items()):
            print(f'  {name}: {count}')

    def _card_label(self, card_id):
        if card_id == 'unknown':
            return 'unknown'
        card = RuleCard.get_by_id(card_id)
        return f'{card_id} {card.name}'


def answer_all_questions(game):
    while True:
        question = game.next_decision()
        if not question:
            break

        answer = random_answer(question)
        ret = game.set_answer(question.player, answer)
        assert ret, 'random answer is not valid'
        game.question = None


def run_one_game(deck1, deck2, fast=False):
    game = Game.create_duel('player1', deck1, 'player2', deck2)
    try:
        answer_all_questions(game)
    except Exception as error:
        raise GameRunError(error, game) from error

    if fast:
        return game, None

    game_data = game.serialize()
    for event in game.event_log:
        event.serialize_for(game.players[0], game)
        event.serialize_for(game.players[1], game)

    deserialized_game = Game.deserialize(game_data)
    try:
        answer_all_questions(deserialized_game)
    except Exception as error:
        raise GameRunError(error, game, deserialized_game) from error
    return game, deserialized_game


def parse_args():
    available_decks = ', '.join(sorted(DECKS))
    parser = argparse.ArgumentParser(description='Run random BOTE games and report rough card/effect coverage.')
    parser.add_argument('-n', '--games', type=int, default=1)
    parser.add_argument(
        '--deck',
        '--deck1',
        choices=sorted(DECKS),
        default='test',
        help=f"player1's deck. Available: {available_decks}. Default: %(default)s.",
    )
    parser.add_argument(
        '--opponent-deck',
        '--deck2',
        choices=sorted(DECKS),
        help=(
            "player2's deck. Available: "
            f"{available_decks}. Default: same as --deck."
        ),
    )
    parser.add_argument('--seed', type=int)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--traceback', action='store_true')
    parser.add_argument('--stop-on-failure', action='store_true')
    parser.add_argument('--fast', action='store_true', help='Skip serialization/deserialization round-trip.')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    if not args.verbose:
        logging.getLogger('state').setLevel(logging.ERROR)

    deck1 = DECKS[args.deck]
    deck2_name = args.opponent_deck or args.deck
    deck2 = DECKS[deck2_name]
    coverage = Coverage(deck1, deck2)

    for game_index in range(1, args.games + 1):
        try:
            if args.verbose:
                game, deserialized_game = run_one_game(deck1, deck2, fast=args.fast)
            else:
                with contextlib.redirect_stdout(io.StringIO()):
                    game, deserialized_game = run_one_game(deck1, deck2, fast=args.fast)
            coverage.record_game(game)
            if args.fast:
                print(f'Game {game_index}: {len(game.event_log)} events.')
            else:
                print(
                    f'Game {game_index}: '
                    f'{len(game.event_log)} events, '
                    f'{len(deserialized_game.event_log)} after deserialize.'
                )
        except GameRunError as error:
            coverage.record_failure(game_index, error.original_error)
            coverage.record_game(error.game, complete=False)
            print(
                f'Game {game_index}: failed after {len(error.game.event_log)} events '
                f'with {error.original_error.__class__.__name__}: {error.original_error}'
            )
            if args.traceback:
                print(error.traceback, end='')
            if args.stop_on_failure:
                raise error.original_error
        except Exception as error:
            coverage.record_failure(game_index, error)
            print(f'Game {game_index}: failed with {error.__class__.__name__}: {error}')
            if args.traceback:
                traceback.print_exception(type(error), error, error.__traceback__)
            if args.stop_on_failure:
                raise

    print()
    coverage.print_report()


if __name__ == '__main__':
    try:
        import state
        state.print = lambda *a, **b: None
        main()
    except Exception:
        traceback.print_exc()
        pdb.post_mortem()
