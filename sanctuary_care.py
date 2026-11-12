"""Scene-local care performance: authored poses, single owners and cue transfers.

Only acknowledged story beats persist. Partial actions rebuild their beat's
starting arrangement, just like the scene's movement and rope performance.
"""
from collections import deque


class SanctuaryCare:
    def __init__(self, scene, art):
        self.scene = scene
        self.art = art
        self.reset(0)

    def reset(self, beat):
        self.action = None
        self.elapsed_ms = 0.
        self.queue = deque()
        self.fired = set()
        self.purpose = None
        self.setup_started = beat > 0
        self.kit_owner = 'world' if 0 < beat <= 4 else 'stowed'
        self.cloth_owner = 'worker' if beat > 0 else 'linen'
        self.runner_delivered = beat > 0
        self.runner_elapsed_ms = 0.
        self.runner_started = False
        self.runner_sounded = False

    @property
    def busy(self):
        return self.action is not None

    @property
    def remaining(self):
        if not self.busy:return 0.
        poses = self.art['poses']
        return (sum(f['duration_ms'] for f in poses[self.action]['frames'])
                - self.elapsed_ms
                + sum(sum(f['duration_ms'] for f in poses[name]['frames'])
                      for name in self.queue))/1000

    def start(self, purpose, names):
        if self.busy:raise ValueError('Care action already in progress')
        self.scene.actors['mira'].moving = False
        self.purpose = purpose
        self.queue = deque(names)
        if purpose == 'setup':
            self.setup_started = True
            self.kit_owner = 'mira'
        self._next()

    def _next(self):
        self.action = self.queue.popleft() if self.queue else None
        self.elapsed_ms = 0.
        self.fired = set()
        mira = self.scene.actors['mira']
        mira.pose = self.action or ('care_ready' if self.cloth_owner=='mira' else 'care_idle')
        mira.pose_ms = 0.
        if self.action == 'treat':
            self.scene.actors['worker_a'].pose = 'offer_arm'
        elif self.action == 'finish':
            self.scene.actors['worker_a'].pose = 'arm_rest'

    def _cue(self, name):
        if name == 'kit_deposit':self.kit_owner = 'world'
        elif name == 'kit_pickup':self.kit_owner = 'mira'
        elif name == 'kit_stow':self.kit_owner = 'stowed'
        elif name == 'cloth_pickup':self.cloth_owner = 'mira'
        elif name == 'dressing_release':self.cloth_owner = 'worker'
        self.scene._play_care_sound()

    def update(self, seconds):
        """Consume the whole delta, dispatching each crossed cue exactly once."""
        if self.busy:
            budget = seconds*1000
            while self.busy:
                animation = self.art['poses'][self.action]
                duration = sum(f['duration_ms'] for f in animation['frames'])
                step = min(budget, max(0., duration-self.elapsed_ms))
                self.elapsed_ms += step
                budget -= step
                for name, cue in animation.get('cue_ms', {}).items():
                    if name not in self.fired and self.elapsed_ms >= cue:
                        self.fired.add(name)
                        self._cue(name)
                self.scene.actors['mira'].pose_ms = self.elapsed_ms
                if self.elapsed_ms < duration:break
                purpose = self.purpose
                self._next()
                if not self.busy:
                    if purpose == 'retrieve':
                        self.scene.actors['mira'].pose = None
                    self.scene._care_finished(purpose)
                if budget <= 0:break
        self._runner(seconds)

    def _runner(self, seconds):
        runner = self.scene.actors['runner']
        if self.runner_delivered:return
        if self.scene.blocking.busy('runner'):return
        if not self.runner_started:
            self.runner_started = True
            runner.moving = False
            runner.pose = 'runner_place'
            runner.pose_ms = 0.
            return
        animation = self.art['poses']['runner_place']
        self.runner_elapsed_ms += seconds*1000
        runner.pose_ms = self.runner_elapsed_ms
        release = animation['cue_ms']['linen_deposit']
        runner.carrying = self.runner_elapsed_ms < release
        if not runner.carrying and not self.runner_sounded:
            self.runner_sounded=True
            self.scene._play_care_sound()
        if self.runner_elapsed_ms >= sum(f['duration_ms'] for f in animation['frames']):
            self.runner_delivered = True
            runner.pose = None

    @property
    def runner_linen_placed(self):
        animation = self.art['poses']['runner_place']
        return (self.runner_delivered or self.runner_started
                and self.runner_elapsed_ms >= animation['cue_ms']['linen_deposit'])
