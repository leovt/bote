# Game End Design Notes

## Problem

The current game uses `EndOfGameException` as hidden control flow after
`PlayerLosesEvent`. This is hard to serialize and replay correctly.

During replay, the event log contains `PlayerLosesEvent`, but not the fact that
the generator stopped because an exception was raised. If the replayed game is
run again, state-based actions can see the same losing player and emit a second
`PlayerLosesEvent`.

## Preferred Model

Game-ending state should be represented by events and durable state, not by an
exception.

Add player/game state such as:

```python
player.has_lost = False
game.ended = False
```

`handle_PlayerLosesEvent` should mark the player as lost:

```python
def handle_PlayerLosesEvent(self, event):
    self.players[event.player_id].has_lost = True
```

The game loop or `next_decision()` should stop once an explicit game-end event
has been handled.

## State-Based Action Sequence

State-based actions should operate in layers, with each pass emitting one kind
of consequence.

1. Detect fresh losing players.

   Build a snapshot of all players who currently lose and have not already lost.
   Emit `PlayerLosesEvent` for each of them, then return.

2. On the next state-based action pass, detect the game result.

   Count players who have not lost:

   - `0` survivors: emit a draw event.
   - `1` survivor: emit `PlayerWinsEvent` or `GameEndsEvent(winner_id=...)`.
   - More than one survivor: continue the game.

3. On later passes, clean up objects controlled by lost players.

   For multiplayer, remove permanents, stack objects, triggers, and other
   game objects controlled by players who have lost. These removals should also
   be represented as events.

## Simultaneous Losses

If multiple players lose simultaneously, state-based actions should emit all
corresponding `PlayerLosesEvent`s before any winner/draw decision is made.

This requires collecting losing players from the current state first:

```python
losing_players = [
    player for player in game.players.values()
    if not player.has_lost and (
        player.life <= 0 or player.has_drawn_from_empty_library
    )
]
```

Then emit all loss events from that snapshot.

## Multiplayer Cleanup

For multiplayer, a player losing should eventually remove their game objects.
It is better to model this as follow-up state-based actions rather than doing it
inside `handle_PlayerLosesEvent`, because handlers mutate state and do not emit
new events.

Prefer cleanup based on objects controlled by lost players:

```python
for permanent in game.battlefield:
    if permanent.controller.has_lost:
        yield ExitTheBattlefieldEvent(permanent.perm_id)
```

This avoids making controllers `None` and keeps cleanup explicit in the log.

## Magic Reference

In Magic, if both players in a two-player game lose simultaneously, the game is
a draw. In multiplayer, all simultaneous losing players lose at the same time;
if exactly one player remains, that player wins. If no players remain, the game
is a draw.

## Minimal Fix Direction

For the current two-player replay bug, a small durable-state fix is enough:

- Add `has_lost` to `Player`.
- Add `ended` to `Game`, or add an explicit game-end event.
- `handle_PlayerLosesEvent` marks the player as lost.
- State-based actions only emit loss events for players that have not already
  lost.
- Emit and handle a game-end/win/draw event, then stop `next_decision()` or the
  game event loop once the game is ended.

