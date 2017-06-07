from otree.api import Bot, Submission
from . import views


class PlayerBot(Bot):

    def play_round(self):
        yield views.Introduction
        yield Submission(views.Decision, {}, check_html=False)
        yield views.Results


    def validate_play(self):
        assert self.payoff > 0