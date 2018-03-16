from collections import namedtuple
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


from otree.api import Bot, Submission
from . import views


class PlayerBot(Bot):

    def play_round(self):
        if (self.player.round_number > self.group.num_rounds()):
            return

        if self.player.round_number == 1:
            yield views.Introduction
        '''
        driver = webdriver.Remote(
            command_executor='http://chromedriver:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME)
        driver.get('http://localhost:8000/InitializeParticipant/{}/'.format(self.participant.code))
        wait = WebDriverWait(driver, 30)
        wait.until(EC.url_contains('Decision'))
        driver.close()
        '''
        yield Submission(views.Decision, {}, check_html=False)
        test_get_payoff()
        yield views.Results


    def validate_play(self):
        assert self.payoff > 0


def test_get_payoff():

    from otree_redwood.models import Event
    from otree.models.participant import Participant
    from otree.models.session import Session
    import random
    from django.utils import timezone
    from . import models

    sess = Session.objects.create(code=str(random.randint(0, 500000)))
    p1 = Participant.objects.create(session=sess, code='test_p1_'+str(random.randint(0, 500000)))
    p2 = Participant.objects.create(session=sess, code='test_p2_'+str(random.randint(0, 500000)))
    start = timezone.now()

    MockEvent = namedtuple('Event', ['channel', 'value', 'participant', 'timestamp'])
    events_over_time = []

    period_start = MockEvent('state', 'period_start', p1, start+timezone.timedelta(seconds=0))

    events_over_time.append(MockEvent('decisions', 0.5, p1, start+timezone.timedelta(seconds=0)))
    events_over_time.append(MockEvent('decisions', 0.5, p2, start+timezone.timedelta(seconds=0)))
 
    events_over_time.append(MockEvent('decisions', 0.8, p2, start+timezone.timedelta(seconds=5)))
    events_over_time.append(MockEvent('decisions', 0.9, p1, start+timezone.timedelta(seconds=10)))
    events_over_time.append(MockEvent('current_matrix', 1, None, start+timezone.timedelta(seconds=12)))
    events_over_time.append(MockEvent('decisions', 0.4, p1, start+timezone.timedelta(seconds=18)))
    events_over_time.append(MockEvent('decisions', 0.7, p1, start+timezone.timedelta(seconds=20)))

    period_end = MockEvent('state', 'period_end', p1, start+timezone.timedelta(seconds=30))

    payoff_grids = [
        [
            [ 100, 100 ], [   0, 800 ],
            [ 800,   0 ], [ 300, 300 ]
        ],
        [
            [ 800,   0 ], [   0, 200 ],
            [   0, 200 ], [ 200,   0 ]
        ]
    ]

    subsession = models.Subsession.objects.create(session=sess, round_number=1)
    player1 = models.Player.objects.create(session=sess, subsession=subsession, participant=p1, id_in_group=1)
    player2 = models.Player.objects.create(session=sess, subsession=subsession, participant=p2, id_in_group=2)
    group = models.Group.objects.create(session=sess, subsession=subsession)
    group.player_set = { player1, player2 }
    player1.group, player2.group = group, group

    payoff1 = player1.get_payoff(period_start, period_end, events_over_time, payoff_grids)
    payoff2 = player2.get_payoff(period_start, period_end, events_over_time, payoff_grids)

    assert 0 <= payoff1 and payoff1 <= 800
    assert 0 <= payoff2 and payoff2 <= 800
    assert abs(payoff1 - 412) < 1
    assert abs(payoff2 - 133) < 1