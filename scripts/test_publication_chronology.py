"""Offline regressions for original-date ordering; no publication or network."""
from datetime import date
import unittest

import copy
from itertools import permutations

from homepage_demotion import chronological_cards, apply_upper_distribution, demote_side_cards


class ChronologicalCardsTests(unittest.TestCase):
    def rank(self, candidates, dates, limit=4):
        before = list(candidates)
        result = chronological_cards(candidates, dates.__getitem__, limit)
        self.assertEqual(candidates, before, 'Ranking must not mutate source order or dates')
        return result

    def test_newer_previous_lead_naturally_ranks_first(self):
        dates = {'lead': date(2026, 10, 24), 'side': date(2026, 10, 23)}
        self.assertEqual(self.rank(['side', 'lead'], dates), ['lead', 'side'])

    def test_older_previous_lead_is_not_pinned(self):
        dates = {'lead': date(2026, 10, 22), 'shrike': date(2026, 10, 23), 'older': date(2026, 10, 21)}
        self.assertEqual(self.rank(['lead', 'shrike', 'older'], dates), ['shrike', 'lead', 'older'])
        self.assertEqual(dates['lead'], date(2026, 10, 22))

    def test_equal_dates_preserve_explicit_candidate_priority(self):
        dates = dict.fromkeys(['lead', 'side-a', 'side-b'], date(2026, 10, 22))
        self.assertEqual(self.rank(['side-b', 'lead', 'side-a'], dates), ['side-b', 'lead', 'side-a'])

    def test_older_previous_lead_can_leave_four_card_capacity(self):
        dates = {'lead': date(2026, 10, 18), **{f'side-{n}': date(2026, 10, n) for n in range(20, 24)}}
        self.assertEqual(self.rank(['lead', 'side-20', 'side-21', 'side-22', 'side-23'], dates),
                         ['side-23', 'side-22', 'side-21', 'side-20'])

    def test_duplicates_never_consume_capacity(self):
        dates = {'a': date(2026, 10, 24), 'b': date(2026, 10, 23), 'c': date(2026, 10, 22)}
        self.assertEqual(self.rank(['b', 'a', 'a', 'c', 'b'], dates, 3), ['a', 'b', 'c'])

    def test_dates_not_input_order_control_distinct_day_ranking(self):
        dates = {'new-side': date(2026, 10, 24), 'previous-lead': date(2026, 10, 22), 'existing-side': date(2026, 10, 23)}
        self.assertEqual(self.rank(['previous-lead', 'existing-side', 'new-side'], dates),
                         self.rank(['new-side', 'existing-side', 'previous-lead'], dates))

    def test_next_publication_does_not_retain_a_historical_first_slot(self):
        dates = {'lead': date(2026, 10, 24), 'old-side': date(2026, 10, 23), 'new-side': date(2026, 10, 25)}
        first = self.rank(['lead', 'old-side'], dates)
        self.assertEqual(first, ['lead', 'old-side'])
        self.assertEqual(self.rank(first + ['new-side'], dates), ['new-side', 'lead', 'old-side'])

    def test_missing_publication_date_fails_instead_of_guessing(self):
        with self.assertRaises(KeyError):
            chronological_cards(['unknown'], {}.__getitem__, 4)


class UpperDistributionTests(unittest.TestCase):
    def fixture(self, lead_day=22):
        sides = ['side-23', 'side-21', 'side-20', 'side-19']
        latest = [f'latest-{n}' for n in range(18, 10, -1)]
        config = {'ia_slots': {'main': 'old-lead', 'important': sides[:], 'latest': latest[:]},
                  'featured': ['old-lead'] + sides, 'latest': latest[:], 'omit_from_latest': []}
        dates = {'old-lead': date(2026, 10, lead_day), 'new-lead': date(2026, 10, 24)}
        dates.update({slug: date(2026, 10, int(slug.rsplit('-', 1)[1])) for slug in sides + latest})
        return config, dates

    def apply(self, config, dates, placements):
        original_dates = copy.deepcopy(dates)
        returned = apply_upper_distribution(config, placements, date_of=dates.__getitem__)
        self.assertEqual(dates, original_dates, 'Original publication dates must never be rewritten')
        self.assertEqual(config['featured'], [config['ia_slots']['main']] + config['ia_slots']['important'])
        self.assertEqual(config['latest'], config['ia_slots']['latest'])
        self.assertEqual(len(config['ia_slots']['important']), len(set(config['ia_slots']['important'])))
        self.assertEqual(len(config['latest']), len(set(config['latest'])))
        self.assertFalse(set(config['featured']) & set(config['latest']))
        self.assertLessEqual(len(config['ia_slots']['important']), 4)
        self.assertLessEqual(len(config['latest']), 8)
        for group in (config['ia_slots']['important'], config['latest']):
            self.assertEqual([dates[x] for x in group], sorted((dates[x] for x in group), reverse=True))
        return returned

    def test_current_gulf_older_than_shrike_shape_is_accepted(self):
        config, dates = self.fixture()
        self.apply(config, dates, [('new-lead', 'lead')])
        self.assertEqual(config['ia_slots']['important'], ['side-23', 'old-lead', 'side-21', 'side-20'])
        self.assertIn('side-19', config['latest'])

    def test_newer_previous_lead_moves_first_without_a_pin(self):
        config, dates = self.fixture(lead_day=24)
        dates['new-lead'] = date(2026, 10, 25)
        self.apply(config, dates, [('new-lead', 'lead')])
        self.assertEqual(config['ia_slots']['important'][0], 'old-lead')
        dates['new-side'] = date(2026, 10, 26)
        self.apply(config, dates, [('new-side', 'side')])
        self.assertEqual(config['ia_slots']['important'][:2], ['new-side', 'old-lead'])

    def test_previous_lead_evicted_by_four_newer_sides_enters_updates(self):
        config, dates = self.fixture(lead_day=18)
        self.apply(config, dates, [('new-lead', 'lead')])
        self.assertNotIn('old-lead', config['ia_slots']['important'])
        self.assertIn('old-lead', config['latest'])
        self.assertEqual(len(config['latest']), 8)

    def test_evicted_previous_lead_with_optout_does_not_enter_updates(self):
        config, dates = self.fixture(lead_day=18)
        config['omit_from_latest'] = ['old-lead']
        self.apply(config, dates, [('new-lead', 'lead')])
        self.assertNotIn('old-lead', config['featured'] + config['latest'])
        self.assertEqual(config['omit_from_latest'], ['old-lead'])

    def test_shrike_optout_survives_side_eviction(self):
        config, dates = self.fixture()
        config['omit_from_latest'] = ['side-23']  # A feature with the Shrike's no-Updates rotation.
        placements = [('new-lead', 'lead')]
        for n in range(4):
            slug = f'new-side-{n}'
            dates[slug] = date(2026, 10, 24 + n)
            placements.append((slug, 'side'))
        self.apply(config, dates, placements)
        self.assertNotIn('side-23', config['featured'] + config['latest'])
        self.assertIn('old-lead', config['latest'])

    def test_all_updates_pools_respect_existing_optouts(self):
        config, dates = self.fixture()
        config['omit_from_latest'] = ['latest-18', 'side-19']
        self.apply(config, dates, [('new-lead', 'lead')])
        self.assertFalse(set(config['omit_from_latest']) & set(config['latest']))

    def test_same_batch_lead_side_latest_permutations_are_identical(self):
        base, dates = self.fixture()
        dates.update({'new-side-a': date(2026, 10, 25), 'new-side-b': date(2026, 10, 25),
                      'new-latest': date(2026, 10, 24)})
        placements = [('new-lead', 'lead'), ('new-side-b', 'side'),
                      ('new-side-a', 'side'), ('new-latest', 'latest')]
        outputs = []
        for batch in permutations(placements):
            config = copy.deepcopy(base)
            self.apply(config, dates, list(batch))
            outputs.append(config)
        self.assertTrue(all(config == outputs[0] for config in outputs))
        self.assertEqual(outputs[0]['ia_slots']['important'][:2], ['new-side-a', 'new-side-b'])

    def test_ties_keep_explicit_new_pool_then_existing_source_order(self):
        config, dates = self.fixture(lead_day=23)
        for slug in config['ia_slots']['important']:
            dates[slug] = date(2026, 10, 23)
        dates['new-side-b'] = dates['new-side-a'] = date(2026, 10, 23)
        self.apply(config, dates, [('new-side-b', 'side'), ('new-lead', 'lead'), ('new-side-a', 'side')])
        self.assertEqual(config['ia_slots']['important'], ['new-side-a', 'new-side-b', 'old-lead', 'side-23'])

    def test_requests_outside_chronological_capacity_fail_not_retain_by_force(self):
        for placement in ('side', 'latest'):
            config, dates = self.fixture()
            dates['too-old'] = date(2026, 1, 1)
            with self.assertRaises((ValueError, AssertionError)):
                apply_upper_distribution(config, [('too-old', placement)], date_of=dates.__getitem__)

    def test_side_only_request_does_not_demote_current_lead(self):
        config, dates = self.fixture(lead_day=18)
        dates['new-side'] = date(2026, 10, 24)
        self.apply(config, dates, [('new-side', 'side')])
        self.assertEqual(config['ia_slots']['main'], 'old-lead')
        self.assertNotIn('old-lead', config['latest'])

    def test_invalid_batch_fails_before_mutating_configuration(self):
        for placements in ([('one', 'lead'), ('two', 'lead')],
                           [('same', 'side'), ('same', 'latest')],
                           [('one', 'unknown')]):
            config, dates = self.fixture()
            original = copy.deepcopy(config)
            with self.assertRaises((ValueError, AssertionError)):
                apply_upper_distribution(config, placements, date_of=dates.__getitem__)
            self.assertEqual(config, original)

    def test_requested_updates_optout_is_not_silently_overridden(self):
        config, dates = self.fixture()
        dates['excluded'] = date(2026, 10, 24)
        config['omit_from_latest'] = ['excluded']
        with self.assertRaises((ValueError, AssertionError)):
            apply_upper_distribution(config, [('excluded', 'latest')], date_of=dates.__getitem__)
        self.assertNotIn('excluded', config['latest'])

    def test_legacy_demotion_uses_same_optouts_and_original_dates(self):
        config, dates = self.fixture()
        config['featured'] = ['old-lead', 'side-21', 'side-20', 'side-19']
        config['omit_from_latest'] = ['side-23', 'latest-18']
        demote_side_cards(config, ['side-23'], date_of=dates.__getitem__)
        self.assertNotIn('side-23', config['latest'])
        self.assertNotIn('latest-18', config['latest'])
        self.assertEqual(config['ia_slots']['latest'], config['latest'])


if __name__ == '__main__':
    unittest.main()
