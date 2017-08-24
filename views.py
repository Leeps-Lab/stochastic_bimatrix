# -*- coding: utf-8 -*-
from __future__ import division
from ._builtin import Page, WaitPage
from .models import Constants, Player, treatment

from datetime import timedelta


def vars_for_all_templates(self):
    payoff_grid = treatment(self.session)['payoff_grid']
    transition_probabilities = treatment(self.session)['transition_probabilities']

    return locals()


class Introduction(Page):

    def is_displayed(self):
        return self.round_number == 1


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'


class Decision(Page):
    pass


class Results(Page):
    timeout_seconds = 30
    
    def vars_for_template(self):
        self.player.set_payoff()
        return {}


def get_output_table(events):
    header = [
        'session_code',
        'subsession_id',
        'id_in_subsession',
        'tick',
        'p1_mean_strategy',
        'p2_mean_strategy',
        'p1_code',
        'p2_code',
        'p_switch',
        'current_matrix',
    ]
    if not events:
        return [], []
    rows = []
    minT = min(e.timestamp for e in events)
    maxT = max(e.timestamp for e in events)
    last_p1_mean = float('nan')
    last_p2_mean = float('nan')
    current_matrix = 0
    p1, p2 = events[0].group.get_players()
    p1_code = p1.participant.code
    p2_code = p2.participant.code
    group = events[0].group
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
        last_p2_mean = p2_mean
    return header, rows


page_sequence = [
    Introduction,
    DecisionWaitPage,
    Decision,
    Results
]
