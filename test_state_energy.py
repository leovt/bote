import unittest

from cards import ArtCard, Card
from energy import BLUE, GREEN, RED
from event import (
    ActivateAbilityEvent,
    AddEnergyEvent,
    BlockEvent,
    CastSpellEvent,
    ClearPoolEvent,
    DamageEvent,
    EnterTheBattlefieldEvent,
    ExitTheBattlefieldEvent,
    PlayerDamageEvent,
    PutInGraveyardEvent,
    QuestionEvent,
    StackEffectEvent,
    StepEvent,
    UntapEvent,
    event_classes,
)
from effects import Effect, EffectTemplate
from state import (
    Game,
    Player,
    Spell,
    activate_ability,
    check_triggers,
    event_specs_are_energy_only,
    game_events,
    play_source,
    turn_based_actions,
)
from state import end_of_step
from step import STEP


def minimal_game(step=STEP.PRECOMBAT_MAIN):
    game = Game()
    player_one = Player(0, 'One', 1)
    player_two = Player(1, 'Two', 0)
    game.players[player_one.player_id] = player_one
    game.players[player_two.player_id] = player_two
    game.active_player = player_one
    game.step = step
    return game, player_one, player_two


def handle_all(game, events):
    for event in events:
        game.handle(event)


def handle_pending_triggers(game):
    game.priority_player = game.active_player
    emitted = []
    for event in game_events(game, skip_start=True):
        if isinstance(event, QuestionEvent):
            break
        emitted.append(event)
        game.handle(event)
    return emitted


def put_card_on_battlefield(game, controller, art_id, perm_id):
    card = Card(f'{perm_id}-secret-id', ArtCard.get_by_id(art_id), controller)
    game.cards[card.secret_id] = card
    game.handle(EnterTheBattlefieldEvent(
        card.secret_id, None, controller.player_id, perm_id, {}))
    return game.battlefield[perm_id]


class TestEnergyOnlyTemplates(unittest.TestCase):
    def test_energy_only_recognizes_immediate_and_triggered_energy(self):
        energy_only_rules = [
            'add {G} to you energy pool',
            'add {G} to you energy pool; add {R} to you energy pool',
            'when your turn begins: add {G} to your energy pool',
        ]

        for rule_text in energy_only_rules:
            with self.subTest(rule_text=rule_text):
                self.assertTrue(EffectTemplate.parse(rule_text).is_energy_only())

    def test_energy_only_rejects_non_energy_and_mixed_results(self):
        non_energy_rules = [
            'chosen .creature has +1/+1 until end of turn',
            'when your turn begins: add {G} to your energy pool; create 1 (90201) token',
        ]

        for rule_text in non_energy_rules:
            with self.subTest(rule_text=rule_text):
                self.assertFalse(EffectTemplate.parse(rule_text).is_energy_only())


class TestEnergyOnlyEventSpecs(unittest.TestCase):
    def test_only_add_energy_specs_are_energy_only(self):
        self.assertTrue(event_specs_are_energy_only([
            AddEnergyEvent(0, '{R}').serialize(),
            AddEnergyEvent(0, '{G}').serialize(),
        ]))
        self.assertFalse(event_specs_are_energy_only([
            AddEnergyEvent(0, '{R}').serialize(),
            EnterTheBattlefieldEvent(None, 90201, 0, 'token-id', {}).serialize(),
        ]))
        self.assertFalse(event_specs_are_energy_only([]))


class TestEnergyDrainTiming(unittest.TestCase):
    def test_end_of_step_does_not_clear_energy(self):
        game, active_player, inactive_player = minimal_game()
        active_player.energy_pool.add(RED)
        inactive_player.energy_pool.add(BLUE)

        events = list(end_of_step(game))

        self.assertFalse(
            any(isinstance(event, ClearPoolEvent) for event in events))
        for event in events:
            game.handle(event)
        self.assertEqual(active_player.energy_pool.energy, RED)
        self.assertEqual(inactive_player.energy_pool.energy, BLUE)

    def test_untap_clears_active_player_energy_first(self):
        game, active_player, inactive_player = minimal_game(STEP.UNTAP)
        active_player.energy_pool.add(RED)
        inactive_player.energy_pool.add(BLUE)

        events = list(turn_based_actions(game))

        self.assertIsInstance(events[0], ClearPoolEvent)
        self.assertEqual(events[0].player_id, active_player.player_id)
        for event in events:
            game.handle(event)
        self.assertEqual(active_player.energy_pool.energy.total, 0)
        self.assertEqual(inactive_player.energy_pool.energy, BLUE)

    def test_next_player_untap_clears_only_that_player_energy(self):
        game, previous_player, active_player = minimal_game(STEP.UNTAP)
        game.active_player = active_player
        previous_player.energy_pool.add(GREEN)
        active_player.energy_pool.add(RED)

        events = list(turn_based_actions(game))

        self.assertEqual(events[0].player_id, active_player.player_id)
        for event in events:
            game.handle(event)
        self.assertEqual(previous_player.energy_pool.energy, GREEN)
        self.assertEqual(active_player.energy_pool.energy.total, 0)
        self.assertIsInstance(events[-1], StepEvent)
        self.assertEqual(events[-1].step, STEP.UPKEEP.name)

    def test_source_adds_energy_when_it_enters(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)

        events = []
        for event in play_source(game, active_player, source):
            events.append(event)
            game.handle(event)
        events.extend(handle_pending_triggers(game))

        self.assertEqual(active_player.energy_pool.energy, RED)
        self.assertFalse(any(isinstance(event, StackEffectEvent) for event in events))

    def test_source_adds_energy_after_turn_start_drain(self):
        game, active_player, _ = minimal_game(STEP.UNTAP)
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)

        handle_all(game, play_source(game, active_player, source))
        handle_pending_triggers(game)
        active_player.energy_pool.add(GREEN)

        game.handle(StepEvent(STEP.UNTAP.name, active_player.player_id))
        for event in turn_based_actions(game):
            game.handle(event)

        triggered_effects, stale_trigger_ids = check_triggers(game)
        self.assertEqual(stale_trigger_ids, [])
        triggered_effect = triggered_effects[0]
        self.assertEqual(triggered_effect.perm_id, next(iter(game.battlefield)).perm_id)
        for event_spec in triggered_effect.effect:
            kwargs = {
                key: value
                for key, value in event_spec.items()
                if key != 'event_id'
            }
            event = event_classes[event_spec['event_id']](**kwargs)
            game.handle(event)

        self.assertEqual(active_player.energy_pool.energy, RED)

    def test_turn_start_energy_trigger_does_not_use_stack(self):
        game, active_player, _ = minimal_game(STEP.UNTAP)
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)
        handle_all(game, play_source(game, active_player, source))
        handle_pending_triggers(game)
        active_player.energy_pool.clear()
        game.trigger(('BEGIN_OF_TURN', active_player.player_id))

        emitted = handle_pending_triggers(game)

        self.assertTrue(any(isinstance(event, AddEnergyEvent) for event in emitted))
        self.assertFalse(any(isinstance(event, StackEffectEvent) for event in emitted))
        self.assertEqual(active_player.energy_pool.energy, RED)

    def test_activated_energy_effect_does_not_use_stack(self):
        game, active_player, _ = minimal_game()
        elf = Card('elf-secret-id', ArtCard.get_by_id(20401), active_player)
        game.cards[elf.secret_id] = elf
        game.handle(EnterTheBattlefieldEvent(
            elf.secret_id, None, active_player.player_id, 'elf-permanent', {}))
        permanent = game.battlefield['elf-permanent']
        ability = permanent.abilities[0]

        events = list(activate_ability(game, ability, 0, active_player, permanent))

        self.assertTrue(any(isinstance(event, AddEnergyEvent) for event in events))
        self.assertFalse(any(isinstance(event, ActivateAbilityEvent) for event in events))
        handle_all(game, events)
        self.assertEqual(active_player.energy_pool.energy, GREEN)

    def test_non_energy_enters_trigger_uses_stack(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        game.handle(EnterTheBattlefieldEvent(
            source.secret_id, None, active_player.player_id, 'source-permanent', {}))
        permanent = game.battlefield['source-permanent']
        trigger = Effect(
            EffectTemplate.parse(
                'when this enters the battlefield: create 1 (90201) token'),
            game,
            {},
            active_player,
            permanent,
        )

        handle_all(game, trigger.execute())
        events = handle_pending_triggers(game)

        self.assertTrue(any(isinstance(event, StackEffectEvent) for event in events))

    def test_destroy_effect_cleans_up_source_trigger(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)
        handle_all(game, play_source(game, active_player, source))
        permanent = next(iter(game.battlefield))
        self.assertTrue(list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)))

        destroy = Effect(EffectTemplate.parse('destroy this'), game, {}, active_player, permanent)
        handle_all(game, destroy.execute())

        self.assertNotIn(permanent.perm_id, game.battlefield)
        self.assertFalse(list(game.triggered_effects.keys_by_perm_id(permanent.perm_id)))

    def test_stale_trigger_is_reported_for_cleanup(self):
        game, active_player, _ = minimal_game()
        source = Card('source-secret-id', ArtCard.get_by_id(10201), active_player)
        game.cards[source.secret_id] = source
        active_player.hand.add(source)
        handle_all(game, play_source(game, active_player, source))
        permanent = next(iter(game.battlefield))
        trigger_ids = list(game.triggered_effects.keys_by_perm_id(permanent.perm_id))
        del game.battlefield[permanent.perm_id]
        game.trigger(('BEGIN_OF_TURN', active_player.player_id))

        with self.assertLogs('state', level='WARNING') as captured:
            triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(triggered_effects, [])
        self.assertEqual(stale_trigger_ids, trigger_ids)
        self.assertIn('Removing stale trigger', captured.output[0])


class TestCastTriggers(unittest.TestCase):
    def install_pyroscientist(self, game, controller):
        card = Card('pyro-secret-id', ArtCard.get_by_id(11901), controller)
        game.cards[card.secret_id] = card
        game.handle(EnterTheBattlefieldEvent(
            card.secret_id, None, controller.player_id, 'pyro-permanent', {}))
        permanent = game.battlefield['pyro-permanent']
        for template in card.effect:
            handle_all(game, Effect(template, game, {}, controller, permanent).execute())
        return permanent

    def test_pyroscientist_registers_simple_cast_triggers(self):
        game, controller, _ = minimal_game()
        self.install_pyroscientist(game, controller)

        triggers = {
            event.trigger
            for event in game.triggered_effects.values()
        }
        self.assertEqual(triggers, {
            ('CAST', controller.player_id, ('instant',)),
            ('CAST', controller.player_id, ('sorcery',)),
        })

    def test_pyroscientist_triggers_only_for_matching_controller_cast(self):
        game, controller, opponent = minimal_game()
        self.install_pyroscientist(game, controller)
        instant = Card('instant-secret-id', ArtCard.get_by_id(11401), controller)
        game.cards[instant.secret_id] = instant
        controller.hand.add(instant)

        game.handle(CastSpellEvent(
            'instant-stack-id', controller.player_id, instant.secret_id, {}))
        triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(stale_trigger_ids, [])
        self.assertEqual(len(triggered_effects), 1)
        self.assertEqual(triggered_effects[0].effect[0]['art_id'], 90201)

        game.triggers.clear()
        opponent_instant = Card(
            'opponent-instant-secret-id', ArtCard.get_by_id(11401), opponent)
        game.cards[opponent_instant.secret_id] = opponent_instant
        opponent.hand.add(opponent_instant)
        game.handle(CastSpellEvent(
            'opponent-stack-id', opponent.player_id, opponent_instant.secret_id, {}))

        triggered_effects, _ = check_triggers(game)
        self.assertEqual(triggered_effects, [])

    def test_pyroscientist_trigger_effect_specs_are_not_energy_only(self):
        game, controller, _ = minimal_game()
        self.install_pyroscientist(game, controller)

        self.assertTrue(all(
            not event_specs_are_energy_only(event.effect)
            for event in game.triggered_effects.values()
        ))

    def test_cast_trigger_unparses_as_canonical_rule_text(self):
        effect = EffectTemplate.parse(
            'when you cast any .instant: create 1 (90201) token')

        self.assertEqual(
            effect.unparse(),
            'when you cast any .instant: create 1 (90201) token',
        )


class TestCombatTriggerRegistration(unittest.TestCase):
    def register_trigger(self, rule_text):
        game, controller, _ = minimal_game()
        permanent = put_card_on_battlefield(game, controller, 20901, 'trigger-permanent')
        template = EffectTemplate.parse(rule_text)
        handle_all(game, Effect(template, game, {}, controller, permanent).execute())
        return game, permanent, next(iter(game.triggered_effects.values()))

    def test_damage_trigger_registers_simple_tuple(self):
        _, permanent, trigger = self.register_trigger(
            'when this gets damage: this has +1/+1')

        self.assertEqual(trigger.trigger, ('DAMAGE', permanent.perm_id))

    def test_blocked_by_trigger_registers_simple_tuple_with_filter(self):
        _, permanent, trigger = self.register_trigger(
            'when this gets blocked by any .creature: this has +1/+1')

        self.assertEqual(
            trigger.trigger,
            ('BLOCKED_BY', permanent.perm_id, ('ANY', ('creature',))),
        )

    def test_damage_event_matches_damage_trigger(self):
        game, permanent, trigger = self.register_trigger(
            'when this gets damage: this has +1/+1')

        game.handle(DamageEvent(permanent.perm_id, 1))
        triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(stale_trigger_ids, [])
        self.assertEqual(triggered_effects, [trigger])

    def test_block_event_matches_blocked_by_trigger_filter(self):
        game, attacker, trigger = self.register_trigger(
            'when this gets blocked by any .creature: this has +1/+1')
        blocker = put_card_on_battlefield(game, game.players[1], 20901, 'blocker')

        game.handle(BlockEvent(attacker.perm_id, [blocker.perm_id]))
        triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(stale_trigger_ids, [])
        self.assertEqual(triggered_effects, [trigger])

    def test_block_event_ignores_blockers_that_do_not_match_filter(self):
        game, attacker, _ = self.register_trigger(
            'when this gets blocked by any .creature: this has +1/+1')
        blocker = put_card_on_battlefield(game, game.players[1], 20101, 'source-blocker')

        game.handle(BlockEvent(attacker.perm_id, [blocker.perm_id]))
        triggered_effects, stale_trigger_ids = check_triggers(game)

        self.assertEqual(stale_trigger_ids, [])
        self.assertEqual(triggered_effects, [])


class TestCombatCleanup(unittest.TestCase):
    def test_exiting_blocker_is_removed_from_attacker_blockers(self):
        game, attacker_player, blocker_player = minimal_game()
        attacker = put_card_on_battlefield(game, attacker_player, 20901, 'attacker')
        blocker = put_card_on_battlefield(game, blocker_player, 20901, 'blocker')

        game.handle(BlockEvent(attacker.perm_id, [blocker.perm_id]))
        game.handle(ExitTheBattlefieldEvent(blocker.perm_id))

        self.assertEqual(attacker.blockers, [])
        self.assertFalse(blocker.blocking)
        self.assertNotIn(blocker.perm_id, game.battlefield)

    def test_exiting_attacker_clears_its_combat_state(self):
        game, attacker_player, blocker_player = minimal_game()
        attacker = put_card_on_battlefield(game, attacker_player, 20901, 'attacker')
        blocker = put_card_on_battlefield(game, blocker_player, 20901, 'blocker')
        game.handle(BlockEvent(attacker.perm_id, [blocker.perm_id]))
        attacker.attacking = blocker_player

        game.handle(ExitTheBattlefieldEvent(attacker.perm_id))

        self.assertFalse(attacker.attacking)
        self.assertEqual(attacker.blockers, [])
        self.assertNotIn(attacker.perm_id, game.battlefield)


class TestContinuousEffectResolution(unittest.TestCase):
    def test_all_player_damage_resolves_to_player_damage_events(self):
        game, controller, _ = minimal_game()
        events = Effect(
            EffectTemplate.parse('all .player gets 1 damage'),
            game,
            {},
            controller,
            None,
        ).execute()

        self.assertEqual(
            [(event.player_id, event.damage) for event in events],
            [(0, 1), (1, 1)],
        )
        self.assertTrue(all(isinstance(event, PlayerDamageEvent) for event in events))

    def test_all_flying_creature_damage_filters_by_keyword(self):
        game, controller, _ = minimal_game()
        flying = put_card_on_battlefield(game, controller, 20701, 'flying-permanent')
        put_card_on_battlefield(game, controller, 20901, 'ground-permanent')

        events = Effect(
            EffectTemplate.parse('all .creature.flying gets 1 damage'),
            game,
            {},
            controller,
            None,
        ).execute()

        self.assertEqual(
            [(event.perm_id, event.damage) for event in events],
            [(flying.perm_id, 1)],
        )
        self.assertTrue(all(isinstance(event, DamageEvent) for event in events))

    def test_untap_effect_resolves_to_untap_events(self):
        game, controller, _ = minimal_game()
        source = put_card_on_battlefield(game, controller, 20101, 'source-permanent')

        events = Effect(
            EffectTemplate.parse('untap chosen .source'),
            game,
            {'@1': source},
            controller,
            None,
        ).execute()

        self.assertEqual([event.perm_id for event in events], [source.perm_id])
        self.assertTrue(all(isinstance(event, UntapEvent) for event in events))

    def test_unsupported_prevent_battle_damage_is_explicit_noop(self):
        game, controller, _ = minimal_game()

        events = Effect(
            EffectTemplate.parse('prevent all battle damage until end of turn'),
            game,
            {},
            controller,
            None,
        ).execute()

        self.assertEqual(events, [])

    def test_self_modifier_does_nothing_after_permanent_leaves(self):
        game, controller, _ = minimal_game()
        card = Card('creature-secret-id', ArtCard.get_by_id(10501), controller)
        game.cards[card.secret_id] = card
        game.handle(EnterTheBattlefieldEvent(
            card.secret_id, None, controller.player_id, 'creature-permanent', {}))
        permanent = game.battlefield['creature-permanent']
        modifier = Effect(
            EffectTemplate.parse('this has +1/+0 until end of turn'),
            game,
            {},
            controller,
            permanent,
        )

        del game.battlefield[permanent.perm_id]
        events = modifier.execute()

        self.assertEqual(events, [])
        self.assertEqual(list(game.continuous_effects.keys()), [])


class TestSpellResolution(unittest.TestCase):
    def test_targeted_spell_does_nothing_if_target_has_left(self):
        game, controller, _ = minimal_game()
        target_card = Card('target-secret-id', ArtCard.get_by_id(10501), controller)
        spell_card = Card('spell-secret-id', ArtCard.get_by_id(11401), controller)
        game.cards[target_card.secret_id] = target_card
        game.cards[spell_card.secret_id] = spell_card
        game.handle(EnterTheBattlefieldEvent(
            target_card.secret_id, None, controller.player_id, 'target-permanent', {}))
        spell = Spell(
            'spell-stack-id',
            controller,
            spell_card,
            {'@1': {'type': 'permanent', 'perm_id': 'target-permanent'}},
        )

        del game.battlefield['target-permanent']
        events = list(spell.resolve(game))

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], PutInGraveyardEvent)
        handle_all(game, events)
        self.assertIn(spell_card, controller.graveyard)


if __name__ == '__main__':
    unittest.main()
