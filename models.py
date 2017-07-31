# -*- coding: utf-8 -*-
from __future__ import division
import random

from django.contrib.contenttypes.models import ContentType
from otree import widgets
from otree.db import models
from otree.constants import BaseConstants
from otree.common import Currency as c, currency_range
from otree.models import BaseSubsession, BaseGroup, BasePlayer

from otree_redwood.models import Event

doc = """
Two-by-two game with stochastic transitions between payoff matrices.
"""


# from .test_payoff import fill_events
# do_test = False

# if


class Constants(BaseConstants):
    name_in_url = 'stochastic_bimatrix'
    players_per_group = 2
    num_rounds = 10

    base_points = 0

    period_length = 120

    treatments = {
        'A': {
            'payoff_grid': [
                [
                    [ 100, 800 ], [ 100, 200 ],
                    [   0, 200 ], [   0,   0 ]
                ],
                [
                    [ 800,   0 ], [   0, 200 ],
                    [   0, 200 ], [ 200,   0 ]
                ]
            ],
            'transition_probabilities':
                [
                    [   1,   0 ], [   .8,   0 ],
                    [   0,   0 ], [   .8,   1 ]
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
    }


class Subsession(BaseSubsession):
    
    def before_session_starts(self):
        self.group_randomly()


class Group(BaseGroup):
    pass


class Player(BasePlayer):

    def other_player(self):
        return self.get_others_in_group()[0]

    def set_payoff(self, initial_decision):
        events_over_time = Event.objects.filter(
            content_type=ContentType.objects.get_for_model(self.group),
            group_pk=self.group.pk)

        if not events_over_time:
            return 0

        useful_events_over_time = [
            event for event in events_over_time
            if event.channel == 'decisions' or event.channel == 'transitions'
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

        self.payoff = get_payoff(
            period_start, period_end,
            useful_events_over_time,
            self.id_in_group,
            self.participant.code,
            Constants.treatments[self.session.config['treatment']]['payoff_grid']
        )


def get_payoff(period_start, period_end, events_over_time, id_in_group, participant_code, payoff_grids):

    period_duration = period_end.timestamp - period_start.timestamp

    payoff = 0

    # defaults
    q1, q2 = 0.5, 0.5
    current_matrix = 0

    for i, change in enumerate(events_over_time):
        if change.channel == 'transitions':
            current_matrix = change.value
        elif change.channel == 'decisions':
            # decision was made by me and my id is 1, or decision was made by opponent and my id is 2
            if (change.participant.code == participant_code) is (id_in_group == 1):
                q1 = change.value
                print('q1={}'.format(change.value))
            else:
                q2 = change.value
                print('q2={}'.format(change.value))

        payoff_grid = [payoff[id_in_group - 1] for payoff in payoff_grids[current_matrix]]

        cur_payoff = (
            payoff_grid[0] * q1 * q2 +
            payoff_grid[1] * q1 * (1 - q2) +
            payoff_grid[2] * (1 - q1) * q2 +
            payoff_grid[3] * (1 - q1) * (1 - q2))

        if i + 1 < len(events_over_time):
            next_change_time = events_over_time[i + 1].timestamp
        else:
            next_change_time = period_end.timestamp

        time_diff = (next_change_time - change.timestamp).total_seconds()

        payoff += time_diff * cur_payoff

    return payoff / Constants.period_length
