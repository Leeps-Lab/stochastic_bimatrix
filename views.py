# -*- coding: utf-8 -*-
from __future__ import division
from ._builtin import Page, WaitPage
from .models import Constants, Player, Subsession, parse_config

from datetime import timedelta
from operator import concat
from functools import reduce

def vars_for_all_templates(self):
    payoff_grid = parse_config(self.session.config['config_file'])[self.round_number-1]['payoff_grid']
    transition_probabilities = parse_config(self.session.config['config_file'])[self.round_number-1]['transition_probabilities']

    return locals()


class Introduction(Page):

    def is_displayed(self):
        return self.round_number == 1


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()


class Decision(Page):

    def vars_for_template(self):
        return {}

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()


class Results(Page):
    timeout_seconds = 30

    def vars_for_template(self):
        self.player.set_payoff()
        return {}

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()

def get_config_columns(group):
    payoffs = group.subsession.payoff_grid()
    payoffs = reduce(concat, payoffs)
    config = parse_config(group.session.config['config_file'])
    role_shuffle = config[group.round_number - 1]['shuffle_role']
    return payoffs + [role_shuffle]

def get_output_table_header():
    return [
        'session_code',
        'subsession_id',
        'id_in_subsession',
        'tick',
        'p1_strategy',
        'p2_strategy',
        'p1_code',
        'p2_code',
        'p_switch',
        'current_matrix',
        'A_payoff1Aa',
        'A_payoff1Ab',
        'A_payoff1Ba',
        'A_payoff1Bb',
        'A_payoff2Aa',
        'A_payoff2Ab',
        'A_payoff2Ba',
        'A_payoff2Bb',
        'B_payoff1Aa',
        'B_payoff1Ab',
        'B_payoff1Ba',
        'B_payoff1Bb',
        'B_payoff2Aa',
        'B_payoff2Ab',
        'B_payoff2Ba',
        'B_payoff2Bb',
        'role_shuffle',
    ]

def get_output_table(events):
    if not events:
        return []
    rows = []
    minT = min(e.timestamp for e in events)
    maxT = max(e.timestamp for e in events)
    current_matrix = 0
    p1, p2 = events[0].group.get_players()
    p1_code = p1.participant.code
    p2_code = p2.participant.code
    group = events[0].group
    config_columns = get_config_columns(group)
    ticks_per_second = 2
    p1_decision = float('nan')
    p2_decision = float('nan')
    for tick in range((maxT - minT).seconds * ticks_per_second):
        currT = minT + timedelta(seconds=(tick / ticks_per_second))
        cur_decision_event = None
        while events[0].timestamp <= currT:
            e = events.pop(0)
            if e.channel == 'group_decisions':
                cur_decision_event = e
            elif e.channel == 'current_matrix':
                current_matrix = e.value
        if cur_decision_event:
            p1_decision = cur_decision_event.value[p1_code]
            p2_decision = cur_decision_event.value[p2_code]
        rows.append([
            group.session.code,
            group.subsession_id,
            group.id_in_subsession,
            tick,
            p1_decision,
            p2_decision,
            p1_code,
            p2_code,
            group.pswitch(p1_decision,p2_decision),
            current_matrix,
        ] + config_columns)
    return rows
"""
    for tick in range((maxT - minT).seconds):
        currT = minT + timedelta(seconds=tick)
        group_decisions_events = []
        while events[0].timestamp <= currT:
            e = events.pop(0)
            if e.channel == 'group_decisions':
                group_decisions_events.append(e)
            elif e.channel == 'current_matrix':
                current_matrix = e.value
        p1_decisions = []
        p2_decisions = []
        for event in group_decisions_events:
            p1_decisions.append(event.value[p1_code])
            p2_decisions.append(event.value[p2_code])
        p1_mean, p2_mean = last_p1_mean, last_p2_mean
        if p1_decisions:
            p1_mean = sum(p1_decisions) / len(p1_decisions)
        if p2_decisions:
            p2_mean = sum(p2_decisions) / len(p2_decisions)
        rows.append([
            group.session.code,
            group.subsession_id,
            group.id_in_subsession,
            tick,
            p1_mean,
            p2_mean,
            p1_code,
            p2_code,
            group.pswitch(p1_mean, p2_mean),
            current_matrix,
        ])
        last_p1_mean = p1_mean
        last_p2_mean = p2_mean """


page_sequence = [
    Introduction,
    DecisionWaitPage,
    Decision,
    Results
]
