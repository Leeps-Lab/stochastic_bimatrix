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
    timeout_seconds = 100

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

        return {
            'total_plus_base': self.player.payoff + Constants.base_points
        }


def get_output_table(events):
    header = [
        'tick',
        'player1',
        'player2',
    ]
    rows = []
    minT = min(e.timestamp for e in events)
    maxT = max(e.timestamp for e in events)
    last_p1_mean = float('nan')
    last_p2_mean = float('nan')
    for tick in range((maxT - minT).seconds):
        currT = minT + timedelta(seconds=tick)
        tick_events = []
        while events[0].timestamp <= currT:
            e = events.pop(0)
            if e.channel == 'decisions' and e.value is not None:
                tick_events.append(e)
        p1_decisions = []
        p2_decisions = []
        for event in tick_events:
            player = Player.objects.get(
                participant=event.participant,
                group=e.group)
            if player.id_in_group == 1:
                p1_decisions.append(event.value)
            elif player.id_in_group == 2:
                p2_decisions.append(event.value)
            else:
                raise ValueError('Invalid player id in group {}'.format(player.id_in_group))
        p1_mean, p2_mean = last_p1_mean, last_p2_mean
        if p1_decisions:
            p1_mean = sum(p1_decisions) / len(p1_decisions)
        if p2_decisions:
            p2_mean = sum(p2_decisions) / len(p2_decisions)
        rows.append([
            tick,
            p1_mean,
            p2_mean
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
