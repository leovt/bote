import sqlite3

with sqlite3.connect('cards.sqlite') as con:
    with open('create_cards_db.sql') as f:
        con.cursor().executescript(f.read())
    con.commit()
