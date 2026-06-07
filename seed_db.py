import argparse
import os

from app import app, db
from app.models import Deck, DeckCard, User
from test_decks import GREEN_TEST_DECK, RED_GREEN_TEST_DECK, RED_TEST_DECK


def upsert_user(username, email, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username)
        db.session.add(user)

    user.email = email
    if password:
        user.set_password(password)
    return user


def upsert_deck(owner, name, cards, public=True):
    deck = Deck.query.filter_by(owner_id=owner.id, name=name).first()
    if deck is None:
        deck = Deck(owner_id=owner.id, name=name)
        db.session.add(deck)
        db.session.flush()

    deck.public = public

    existing_cards = {
        deck_card.art_id: deck_card
        for deck_card in deck.cards
    }

    for art_id, count in cards.items():
        deck_card = existing_cards.pop(art_id, None)
        if deck_card is None:
            deck_card = DeckCard(deck_id=deck.id, art_id=art_id)
            db.session.add(deck_card)
        deck_card.count = count

    for deck_card in existing_cards.values():
        db.session.delete(deck_card)

    return deck


def delete_deck(deck):
    for deck_card in deck.cards:
        db.session.delete(deck_card)
    db.session.delete(deck)


def seed(
        username,
        email,
        password,
        archive_username,
        archive_email,
        red_deck_name,
        green_deck_name='Green Test Deck',
        red_green_deck_name='Red Green Test Deck'):
    os.makedirs('savegames', exist_ok=True)
    with app.app_context():
        user = upsert_user(username, email, password)
        archive_user = upsert_user(archive_username, archive_email, None)
        db.session.flush()
        decks = [
            upsert_deck(archive_user, red_deck_name, RED_TEST_DECK, public=True),
            upsert_deck(archive_user, green_deck_name, GREEN_TEST_DECK, public=True),
            upsert_deck(archive_user, red_green_deck_name, RED_GREEN_TEST_DECK, public=True),
        ]
        removed_user_decks = []
        if user.id != archive_user.id:
            for deck in Deck.query.filter(
                    Deck.owner_id == user.id,
                    Deck.name.in_([red_deck_name, green_deck_name, red_green_deck_name])):
                removed_user_decks.append(deck.name)
                delete_deck(deck)
        summary = {
            'username': user.username,
            'archive_username': archive_user.username,
            'removed_user_decks': removed_user_decks,
            'decks': [
                {
                    'name': deck.name,
                    'card_rows': deck.cards.count(),
                }
                for deck in decks
            ],
        }
        db.session.commit()
        return summary


def parse_args():
    parser = argparse.ArgumentParser(description='Seed local development data.')
    parser.add_argument('--username', default='Leo')
    parser.add_argument('--email', default='leo@example.test')
    parser.add_argument('--password', default='password')
    parser.add_argument('--archive-username', default='deck_archive')
    parser.add_argument('--archive-email', default='deck-archive@example.test')
    parser.add_argument('--red-deck-name', default='Red Test Deck')
    parser.add_argument('--green-deck-name', default='Green Test Deck')
    parser.add_argument('--red-green-deck-name', default='Red Green Test Deck')
    return parser.parse_args()


def main():
    args = parse_args()
    summary = seed(
        username=args.username,
        email=args.email,
        password=args.password,
        archive_username=args.archive_username,
        archive_email=args.archive_email,
        red_deck_name=args.red_deck_name,
        green_deck_name=args.green_deck_name,
        red_green_deck_name=args.red_green_deck_name,
    )
    deck_summaries = ', '.join(
        f"{deck['name']!r} ({deck['card_rows']} card rows)"
        for deck in summary['decks']
    )
    print(
        f"Seeded user {summary['username']!r} and public decks for "
        f"{summary['archive_username']!r}: {deck_summaries}."
    )
    if summary['removed_user_decks']:
        removed_decks = ', '.join(repr(name) for name in summary['removed_user_decks'])
        print(f"Removed old personal seed decks from {summary['username']!r}: {removed_decks}.")


if __name__ == '__main__':
    main()
