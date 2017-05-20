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

from math import sqrt
import random


class UndefinedTreatmentError(ValueError):
    pass

def treatment(self):
    if 'treatment' in self.session.config:
        return Constants.treatments[self.session.config['treatment']]
    else:
        raise UndefinedTreatmentError('no treatment attribute in settings.py')

def vars_for_all_templates(self):
    payoff_grid = treatment(self)['payoff_grid']

    return locals()

class Introduction(Page):
    timeout_seconds = 100


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'


class Decision(redwood_views.ContinuousDecisionPage):
    period_length = Constants.period_length
    current_matrix = 0
    initial_decision = .5

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
        q1, q2 = list(self.group_decisions.values()) # decisions
        p11, p12, p21, p22 = [pij[self.current_matrix] for pij in treatment(self)['transition_probabilities']] # transition probabilities
        Pmax = .2
        Pswitch = Pmax * ( q1*q2*p11 + q1*(1-q2)*p12 + (1-q1)*q2*p21 + (1-q1)*(1-q2)*p22 )

        if random.uniform(0, 1) < Pswitch:
            self.current_matrix = 1 - self.current_matrix
            print(str.format('matrix changed with q1={}, q2={}, P={}', q1, q2, Pswitch))
            # TODO: save matrix transitions to database

        consumers.send(self.group, 'current_matrix', self.current_matrix)
        consumers.send(self.group, 'hazard_rate', Pswitch/Pmax)


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
