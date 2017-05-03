# -*- coding: utf-8 -*-
from __future__ import division
from . import models
from ._builtin import Page, WaitPage
from otree.common import Currency as c, currency_range
from .models import Constants
import otree_redwood.abstract_views as redwood_views
from otree_redwood import consumers

from django.utils import timezone
from datetime import timedelta
import logging
import time


def vars_for_all_templates(self):
    payoff_grid = Constants.payoff_grid_array[1]
    if (self.player.id_in_group == 1):
        return {
            "my_A_A_payoff": payoff_grid[0][0],
            "my_A_B_payoff": payoff_grid[1][0],
            "my_B_A_payoff": payoff_grid[2][0],
            "my_B_B_payoff": payoff_grid[3][0],
            "other_A_A_payoff": payoff_grid[0][1],
            "other_A_B_payoff": payoff_grid[1][1],
            "other_B_A_payoff": payoff_grid[2][1],
            "other_B_B_payoff": payoff_grid[3][1],
            "total_q": 1
        }
    else:
        return {
            "my_A_A_payoff": payoff_grid[0][1],
            "my_A_B_payoff": payoff_grid[1][1],
            "my_B_A_payoff": payoff_grid[2][1],
            "my_B_B_payoff": payoff_grid[3][1],
            "other_A_A_payoff": payoff_grid[0][0],
            "other_A_B_payoff": payoff_grid[1][0],
            "other_B_A_payoff": payoff_grid[2][0],
            "other_B_B_payoff": payoff_grid[3][0],
            "total_q": 1
        }


class Introduction(Page):
    timeout_seconds = 100


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'


class Decision(redwood_views.ContinuousDecisionPage):
    period_length = Constants.period_length

    def when_all_players_ready(self):
        super().when_all_players_ready()
        # calculate start and end times for the period
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=Constants.period_length)

        self.session.vars['start_time_{}'.format(self.group.id_in_subsession)] = start_time
        self.session.vars['end_time_{}'.format(self.group.id_in_subsession)] = end_time
        self.emitter = redwood_views.DiscreteEventEmitter(0.1, self.period_length, self.group, self.tick)
        self.emitter.start()

    def tick(self, current_interval, intervals, group):
        consumers.send(self.group, 'tick', {
            'current_interval': current_interval,
            'intervals': intervals,
            'timestamp': time.time()
        })


class Results(Page):
    
    def vars_for_template(self):
        self.player.set_payoff()

        return {
            'decisions_over_time': self.player.decisions_over_time,
            'total_plus_base': self.player.payoff + Constants.base_points
        }


page_sequence = [
    Introduction,
    DecisionWaitPage,
    Decision,
    Results
]
