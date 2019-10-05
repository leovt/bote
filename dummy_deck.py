from cards import ArtCard

TEST_DECK = (
    [ArtCard.get_by_id(10201)] * 10 +
    [ArtCard.get_by_id(10202)] * 10 +
    [ArtCard.get_by_id(10101)] * 20 +
    [ArtCard.get_by_id(10301)] * 20
)
