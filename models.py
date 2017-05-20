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
            'transition_probabilities' : [
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
            'transition_probabilities' : [
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
        self.decisions_over_time = Event.objects.filter(
            channel='decisions',
            session=self.session,
            subsession=self.subsession.name(),
            round=self.round_number,
            group=self.group.id_in_subsession
        )

        payoff = 0

        # default state when no decisions have been made
        my_state = .5
        other_state = .5

        payoff_grid = Constants.payoff_grid[1]
        if (self.id_in_group == 1):
            A_A_payoff = payoff_grid[0][0]
            A_B_payoff = payoff_grid[1][0]
            B_A_payoff = payoff_grid[2][0]
            B_B_payoff = payoff_grid[3][0]
        else:
            A_A_payoff = payoff_grid[0][1]
            A_B_payoff = payoff_grid[1][1]
            B_A_payoff = payoff_grid[2][1]
            B_B_payoff = payoff_grid[3][1]

        cur_payoff = (A_A_payoff + A_B_payoff + B_A_payoff + B_B_payoff) * .25 / Constants.period_length
        if (len(self.decisions_over_time) > 0):
            next_change_time = self.decisions_over_time[0].timestamp
        else:
            next_change_time = self.session.vars['end_time_{}'.format(self.group.id_in_subsession)]
        payoff += (next_change_time - self.session.vars['start_time_{}'.format(self.group.id_in_subsession)]).total_seconds() * cur_payoff

        for i, change in enumerate(self.decisions_over_time):
            if change.participant == self.participant:
                my_state = change.value
            else:
                other_state = change.value

            cur_payoff = ((A_A_payoff * my_state * other_state) +
                          (A_B_payoff * my_state * (1 - other_state)) +
                          (B_A_payoff * (1 - my_state) * other_state) +
                          (B_B_payoff * (1 - my_state) * (1 - other_state))) / Constants.period_length

            if i == len(self.decisions_over_time) - 1:
                next_change_time = self.session.vars['end_time_{}'.format(self.group.id_in_subsession)]
            else:
                next_change_time = self.decisions_over_time[i + 1].timestamp

            payoff += (next_change_time - change.timestamp).total_seconds() * cur_payoff

        self.payoff = payoff

