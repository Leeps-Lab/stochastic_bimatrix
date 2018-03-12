# -*- coding: utf-8 -*-
from __future__ import division
import csv
import random

from django.contrib.contenttypes.models import ContentType
from otree import widgets
from otree.db import models
from otree.constants import BaseConstants
from otree.common import Currency as c, currency_range
from otree.models import BaseSubsession, BasePlayer
from otree_redwood.models import Event, DecisionGroup
from otree_redwood.utils import DiscreteEventEmitter

doc = """
Two-by-two game with stochastic transitions between payoff matrices.
"""

"""
class UndefinedTreatmentError(ValueError):
    pass


def treatment(session):
    if 'treatment' in session.config:
        return Constants.treatments[session.config['treatment']]
    else:
        raise UndefinedTreatmentError('no treatment attribute in settings.py')
"""

class Constants(BaseConstants):
    name_in_url = 'stochastic_bimatrix'
    players_per_group = 2
    num_rounds = 100

    base_points = 0

    # period_length = 120

def parse_config(config_file):
    with open('stochastic_bimatrix/configs/' + config_file) as f:
        rows = list(csv.DictReader(f))

    rounds = []
    for row in rows:
        rounds.append({
            'shuffle_role': True if row['shuffle_role'] == 'TRUE' else False,
            'period_length': int(row['period_length']),
            'payoff_grid': [
                [
                    [int(row['A_payoff1Aa']), int(row['A_payoff2Aa'])], [int(row['A_payoff1Ab']), int(row['A_payoff2Ab'])],
                    [int(row['A_payoff1Ba']), int(row['A_payoff2Ba'])], [int(row['A_payoff1Bb']), int(row['A_payoff2Bb'])]
                ],
                [
                    [int(row['B_payoff1Aa']), int(row['B_payoff2Aa'])], [int(row['B_payoff1Ab']), int(row['B_payoff2Ab'])],
                    [int(row['B_payoff1Ba']), int(row['B_payoff2Ba'])], [int(row['B_payoff1Bb']), int(row['B_payoff2Bb'])]
                ]
            ],
            'transition_probabilities':
                [
                    [int(row['transition1Aa']), int(row['transition2Aa'])], [int(row['transition1Ab']), int(row['transition2Ab'])],
                    [int(row['transition1Ba']), int(row['transition2Ba'])], [int(row['transition1Bb']), int(row['transition2Bb'])]
                ]
        })
    return rounds

"""
    treatments = {
        'A': {
            'payoff_grid': [
                [
                    [ 20, 0 ], [ 0, 20 ],
                    [   0, 20 ], [   20,   0 ]
                ],
                [
                    [ 200,   0 ], [   0, 200 ],
                    [   0, 200 ], [ 50,   150 ]
                ]
            ],
            'transition_probabilities':
                [
                    [   1,   0 ], [   0,   0 ],
                    [   0,   0 ], [   0,   1 ]
                ]
        },
        'B': {
            'payoff_grid': [
                [
                    [ 100, 100 ], [   0, 800 ],
                    [ 800,   0 ], [ 300, 300 ]
                ],
                [
                    [ 800,   0 ], [   0, 200 ],
                    [   0, 200 ], [ 200,   0 ]
                ]
            ],
            'transition_probabilities':
                [
                    [ 0.8, 0.2 ], [   0,   0 ],
                    [   0,   0 ], [ 0.2, 0.8 ]
                ]
        },
    }"""


class Subsession(BaseSubsession):

    def before_session_starts(self):
        config = parse_config(self.session.config['config_file'])
        if self.round_number > len(config):
            self.group_randomly()
        elif config[self.round_number-1]['shuffle_role']:
            self.group_randomly()
        else:
            self.group_randomly(fixed_id_in_group=True)

    def payoff_grid(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['payoff_grid']

    def transition_probabilities(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['transition_probabilities']


class Group(DecisionGroup):

    current_matrix = models.PositiveIntegerField()

    def period_length(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['period_length']

    def num_rounds(self):
        return len(parse_config(self.session.config['config_file']))

    def when_all_players_ready(self):
        super().when_all_players_ready()
        self.current_matrix = random.choice([0, 1])
        self.save()
        self.emitter = DiscreteEventEmitter(0.1, self.period_length(), self, self.tick)
        self.emitter.start()

    def pswitch(self, q1, q2):
        p11, p12, p21, p22 = [
            pij[self.current_matrix]
            for pij in self.subsession.transition_probabilities()
        ] # transition probabilities
        # probability of a switch in 2 seconds = 1/2
        # solved by P(switch in t) = (1-p)^10t = 1/2
        Pmax = .034064
        return (p11 * q1 * q2 +
                p12 * q1 * (1 - q2) +
                p21 * (1 - q1) * q2 +
                p22 * (1 - q1) * (1 - q2)) * Pmax

    def tick(self, current_interval, intervals):
        # TODO: Integrate into the otree-redwood DiscreteEventEmitter API, because otherwise
        # someone will forget this and get very confused when the tick functions use stale data.
        self.refresh_from_db()
        if len(self.group_decisions) != 2:
            return
        q1 = self.group_decisions[self.get_player_by_id(1).participant.code]
        q2 = self.group_decisions[self.get_player_by_id(2).participant.code]
        if random.uniform(0, 1) < self.pswitch(q1, q2):
            self.current_matrix = 1 - self.current_matrix
            self.save()
            self.send('current_matrix', self.current_matrix)


class Player(BasePlayer):

    def initial_decision(self):
        return 0.5

    def other_player(self):
        return self.get_others_in_group()[0]

    def set_payoff(self):
        events_over_time = Event.objects.filter(
            content_type=ContentType.objects.get_for_model(self.group),
            group_pk=self.group.pk)

        if not events_over_time:
            return 0

        useful_events_over_time = [
            event for event in events_over_time
            if event.channel == 'decisions' or event.channel == 'current_matrix'
        ]

        period_start = Event.objects.get(
                channel='state',
                content_type=ContentType.objects.get_for_model(self.group),
                group_pk=self.group.pk,
                value='period_start')
        period_end = Event.objects.get(
                channel='state',
                content_type=ContentType.objects.get_for_model(self.group),
                group_pk=self.group.pk,
                value='period_end')

        self.payoff = self.get_payoff(
            period_start, period_end,
            useful_events_over_time,
            self.subsession.payoff_grid()
        )

    def get_payoff(self, period_start, period_end, events_over_time, payoff_grids):

        period_duration = period_end.timestamp - period_start.timestamp

        payoff = 0

        # defaults
        q1, q2 = 0.5, 0.5
        current_matrix = 0
        if self.id_in_group == 1:
            row_player = self.participant
        else:
            row_player = self.get_others_in_group()[0].participant

        for i, change in enumerate(events_over_time):
            if change.channel == 'current_matrix':
                current_matrix = change.value
            elif change.channel == 'decisions':
                if change.participant == row_player: # row player sets q1
                    q1 = change.value
                else: # column player sets q2
                    q2 = change.value

            flow_payoff = (
                payoff_grids[current_matrix][0][self.id_in_group - 1] * q1 * q2 +
                payoff_grids[current_matrix][1][self.id_in_group - 1] * q1 * (1 - q2) +
                payoff_grids[current_matrix][2][self.id_in_group - 1] * (1 - q1) * q2 +
                payoff_grids[current_matrix][3][self.id_in_group - 1] * (1 - q1) * (1 - q2))

            if i + 1 < len(events_over_time):
                next_change_time = events_over_time[i + 1].timestamp
            else:
                next_change_time = period_end.timestamp

            payoff += (next_change_time - change.timestamp).total_seconds() * flow_payoff

        return payoff / period_duration.total_seconds()
