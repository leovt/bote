import argparse
import os

from app import app, db
from app.models import Deck, DeckCard, User
from dummy_deck import TEST_DECK


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


def seed(username, email, password, deck_name):
    os.makedirs('savegames', exist_ok=True)
    with app.app_context():
        user = upsert_user(username, email, password)
        db.session.flush()
        deck = upsert_deck(user, deck_name, TEST_DECK)
        summary = {
            'username': user.username,
            'deck_name': deck.name,
            'card_rows': deck.cards.count(),
        }
        db.session.commit()
        return summary


def parse_args():
    parser = argparse.ArgumentParser(description='Seed local development data.')
    parser.add_argument('--username', default='Leo')
    parser.add_argument('--email', default='leo@example.test')
    parser.add_argument('--password', default='password')
    parser.add_argument('--deck-name', default='Test Deck')
    return parser.parse_args()


def main():
    args = parse_args()
    summary = seed(
        username=args.username,
        email=args.email,
        password=args.password,
        deck_name=args.deck_name,
    )
    print(
        f"Seeded user {summary['username']!r} with deck "
        f"{summary['deck_name']!r} ({summary['card_rows']} card rows)."
    )


if __name__ == '__main__':
    main()
