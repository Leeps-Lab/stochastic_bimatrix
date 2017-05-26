# -*- coding: utf-8 -*-
from __future__ import division
import random

from otree import widgets
from otree.db import models
from otree.constants import BaseConstants
from otree.common import Currency as c, currency_range
from otree.models import BaseSubsession, BaseGroup, BasePlayer

from otree_redwood.models import Event

doc = """
Two-by-two game with stochastic transitions between payoff matrices.
"""


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
                    [ 100, 100 ], [   0, 800 ],
                    [ 800,   0 ], [ 300, 300 ]
                ],
                [
                    [ 800,   0 ], [   0, 200 ],
                    [   0, 200 ], [ 200,   0 ]
                ]
            ],
            'transition_probabilities' :
                [
                    [ 1,   0   ], [ 0,   0   ],
                    [ 0,   0   ], [ 0,   1   ]
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
            'transition_probabilities' :
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

    def set_payoff(self):
        events_over_time = Event.objects.filter(
            session=self.session,
            subsession=self.subsession.name(),
            round=self.round_number,
            group=self.group.id_in_subsession
        )
        # filter further into only transition and decision events
        useful_events_over_time = []
        for event in events_over_time:
            if (event.channel == 'decisions' or event.channel == 'transitions') and event.value != None: # why is the not None check needed?
                useful_events_over_time.append(event)

        payoff = 0

        treatment = Constants.treatments[self.session.config['treatment']]
        payoff_grids = treatment['payoff_grid']

        my_state, other_state = .5, .5
        current_matrix = 0

        for i, change in enumerate(useful_events_over_time):
            if change.channel == 'transitions':
                current_matrix = change.value
            elif change.channel == 'decisions':
                if change.participant == self.participant:
                    my_state = change.value
                else:
                    other_state = change.value
            
            payoff_grid = [payoff[self.id_in_group - 1] for payoff in payoff_grids[current_matrix]]

            cur_payoff = (payoff_grid[0] * my_state * other_state +
                          payoff_grid[1] * my_state * (1 - other_state) +
                          payoff_grid[2] * (1 - my_state) * other_state +
                          payoff_grid[3] * (1 - my_state) * (1 - other_state)) / Constants.period_length

            print(change.channel, change.value)
            print('cur_payoff={}'.format(cur_payoff))

            if i < len(useful_events_over_time) - 1: # not last change
                next_change_time = useful_events_over_time[i + 1].timestamp
            else: # last change
                print(self.session.vars) # why is this sometimes not set?
                next_change_time = self.session.vars['end_time_{}'.format(self.group.id_in_subsession)]
            
            time_diff = (next_change_time - change.timestamp).total_seconds()

            print('time_diff={}'.format(time_diff))

            payoff += time_diff * cur_payoff

        print('payoff={}'.format(payoff))
        self.payoff = payoff
