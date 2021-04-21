# second attempt to write this class, this time without reference to Makeig & Jolley, 1996 and simply from
# design conversations had between Brett and Jon

# import types
# from math import cos, sin, sqrt, pi, pow, radians, floor, ceil
from random import randrange

# from klibs import P
# from klibs.KLParams import PILOT_MODE, RESPONSE_MODE
# from klibs.KLGraphics.KLNumpySurface import *
from klibs.KLGraphics.KLDraw import *
from klibs.KLUtilities import *
# from klibs.KLUtilities import colored_stdout as cso
from klibs.KLEnvironment import EnvAgent
# from klibs.KLUserInterface import *
from klibs.KLCommunication import *
from klibs.KLConstants import *
# from klibs.KLTime import precise_time
# from klibs.KLGraphics.colorspaces import const_lum
# from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS
# from klibs.KLResponseCollectors import KeyPressResponse, KeyMap

import sdl2
from numpy import power

# TODO: Make target direction more random (i.e., flips at random time points)
# TODO: Make distribution of PVT events more random


sdl2.SDL_SetRelativeMouseMode(sdl2.SDL_TRUE)
# from inspect import getmembers

# jon **hates** strings because his fingers love typos more than him, and forgets the names of stuff
MOUSE = 'mouse'
TARGET = 'target'
MOUSE_V = 'input_velocity'
VELOCITY = 'velocity'
DIRECTION = 'direction'
LEFT = -1
RIGHT = 1
USER_DIR_CHANGE = 'user_direction_change'
ACCELERATING = 'accelerating'
RESPONSE = 'response'
QUERY_KEYS = {
    'mouse': ('mouse_movement', 'mouse_delta_x'),
    'target': ('target_position', 'target_pos'),
    'input_velocity': ('mouse_velocity', 'mouse_velocity'),
    'velocity': ('target_velocity', 'target_velocity'),
    'distance': ('target_distance', 'target_distance'),
    'direction': ('target_direction', 'target_direction'),
    'response': ('pvt_response', 'pvt_rt')
}
SESSION_START = now()

''' this was unnecessary but a good idea for one day and this code should be moved to utilities.py eventually'''


# def pr(messages, labels=None):
# 	if labels is None:
# 		labels = ''
# 	if not iterable(labels):
# 		if iterable(messages):
# 			labels = [labels]
# 			messages = [messages]
# 		else:
# 			labels = [labels] * len(messages)
#
# 	def stringify(iter_obj):
# 		wrappers = {'list': ("[", "]"), "dict": ("{", "}"), "tuple": ("(", ")")}
# 		wrap_with = None
# 		output = ''
#
# 		if not iterable(iter_obj):
# 			return str(iter_obj)
#
# 		if isinstance(iter_obj, dict):
# 			wrap_with = 'dict'
# 		elif isinstance(iter_obj, list):
# 			wrap_with = 'list'
# 		else:
# 			wrap_with = 'tuple'
#
# 		if iterable(iter_obj):
# 			for i in range(0, len(iter_obj)):
# 				output += stringify(iter_obj) if i == 0 else ", {0}".format(iter_obj)
# 		else:
# 			output += str(iter_obj)
#
# 		return wrappers[wrap_with[0]] + output + wrappers[wrap_with[1]]
#
# 	for i in range(0, len(messages)):
# 		print "{0}: {1}".format(labels[i], stringify(messages[i]))
# 		# if iterable(messages[i]):
# 		# 	txt = ", ".join([str(j) for j in messages[i]])
# 		# else:
# 		# 	txt = messages[i]
# 		# print cso("\n<blue>{0}</blue>: {1}".format(labels[i], txt))


def direction_of(val):
    return RIGHT if val > 0 else LEFT


'''
What Do:

Create a dot. 
Choose a direction
Accelerate to a chosen velocity


'''


class Cache(EnvAgent):
    """ This is literally just a dictionary with more steps, read the API and assume you already understand."""

    def __init__(self):
        super(Cache, self).__init__()
        self.__store = {MOUSE: [], TARGET: [], MOUSE_V: [], VELOCITY: [], DIRECTION: [], RESPONSE: []}

    def write(self, store, data, timestamp=None):
        # data is a list of [position, time]
        stamp = now() if not timestamp else timestamp

        self.__store[store].append([self.exp.target.x if data is None else data, stamp])

        self.db.insert(
            {
                'participant_id': P.participant_id,
                QUERY_KEYS[store][1]: data,
                'timestamp': now() - SESSION_START
            },
            QUERY_KEYS[store][0]
        )

        if store == TARGET:
            self.db.insert(
                {
                    'participant_id': P.participant_id,
                    QUERY_KEYS['distance'][1]: P.screen_c[0] - data,
                    'timestamp': now() - SESSION_START
                },
                QUERY_KEYS['distance'][0]
            )

    def read(self, key, n):
        return self.__store[key][-n]

    def count(self, store):
        return self.__store[store].len

    def fetch(self, key, range):
        return self.__store[key][range[0]:range[1]]

    def dump(self, key=None, to_file=False):
        if to_file:
            with open(P.log_file_path, 'w+') as f:
                for index in self.__store:
                    if key and index is not key:
                        pass
                    f.write("{0}\n".format(index))
                    for row in self.__store[index]:
                        f.write("{0}\n".format(row))
        else:
            print self.__store if not key else self.__store[key]

    def len(self, key):
        return len(self.__store[key])


class Accelerator(EnvAgent):
    """ Currently not in use because the numbers need some massaging; generates acceleration stochastically by
    choosing a net velocity gain to be reached over a given interval, and then adds velocity on each call equal
    proportionate to the elapsed time since last refresh (with reference to goal velocity)"""

    def __init__(self, velocity_range, duration_range, activation_probability):
        super(Accelerator, self).__init__()
        self.start = None
        self.velocity_range = velocity_range  # expressed percent of current velocity; min/max "accelerate to..." values
        self.duration_range = duration_range  # ms
        self.active = False
        self.duration = None
        self.activation_probability = activation_probability
        self.__rate = 0
        self.accumulated_v = []  # for each acceleration period, keeps track of net V gain

    def gain(self):
        if not self.active:
            self.active = randrange(0, 1000) <= 1000 * self.activation_probability
            if self.active:
                self.__goal = self.exp.target.velocity * randrange(*self.velocity_range) / 100.0
                self.start = now()
                self.duration = randrange(*self.duration_range) / 1000.0  # must be expressed in seconds
                # self.__rate = self.__goal / self.duration
                cso("\t\t<blue>Acceleration started</blue> ({0}px/s for {1}s)".format(self.__rate, self.duration))
        else:
            self.active = now() - self.start < self.duration
            if not self.active:
                cso("\t\t<blue_d>Acceleration ended</blue_d> goal: {0}s actual: {1}s".format(self.duration,
                                                                                             now() - self.start))
                self.__rate = 0
                self.duration = None
                self.start = None
                self.accumulated_v = []

        if not self.active:
            return 0
        gain = self.__goal * (now() - self.start)
        self.accumulated_v.append(gain)

        return gain

    def reset(
            self):  # method exists for readability basically; the actual resetting is done in the (if) cond in apply()
        self.active = False

    @property
    def rate(self):
        return self.__rate

    @property
    def average_gain(self):
        try:
            return sum(self.accumulated_v) / len(self.accumulated_v)
        except ZeroDivisionError:
            return 0

    @property
    def net_gain(self):
        return sum(self.accumulated_v)


class PVTarget2(EnvAgent):

    def __init__(self):
        super(PVTarget2, self).__init__()
        self.__init_time = now()
        self.polling = False
        self.velocity_bounds = [5.0, 10.0]  # px/s
        self.max_velocity = 0.5
        self.acceleration_config = {
            'activation_probability': 0.001,  # roughly once every 3 seconds
            'velocity_range': [5, 20],  # percent of current velocity
            'duration_range': [500, 5000]  # acceleration time in ms
        }

        # target position can't exceed a margin of half it's width from either screen edge
        self.x_bounds = [int(0.5 * self.exp.metrics['target_frame_w'][1]),
                         int(P.screen_x - 0.5 * self.exp.metrics['target_frame_w'][1])]
        self.accelerator = Accelerator(**self.acceleration_config)
        self.txtm.add_style('target', self.exp.metrics['target_h'][1], self.exp.palette['red'])
        self.txtm.add_style('target_digits', self.exp.metrics['target_h'][1] * .75, self.exp.palette['white'])
        self.txtm.add_style('dev_info', 12, (255, 255, 255))
        self.assets = {}
        self.assets[TARGET] = message('XXX', 'target', blit_txt=False)
        self.assets['target_wrapper'] = Rectangle(self.exp.metrics['target_frame_w'][1],
                                                  self.exp.metrics['target_frame_h'][1],
                                                  [2, self.exp.palette['red'], STROKE_OUTER]).render()
        self.assets['fixation'] = Circle(self.exp.metrics['fixation_radius'][1], fill=self.exp.palette['white'])
        self.assets['cursor'] = Circle(self.exp.metrics['cursor'][1], fill=self.exp.palette['green'])

        # create & init the cache; because the behaviour of refresh N depends on the state of N-1, we record the
        # history of SDL2 mouse motion events, mouse velocity, target position and target velocity at each refresh
        self.cache = Cache()
        # self.cache.dump()

        # now populate the cache indices with some initial data to avoid index & zerodivision errors
        self.cache.write(DIRECTION, RIGHT if int(str(now())[-1]) % 2 else LEFT)
        self.cache.write(VELOCITY, float(randrange(*self.velocity_bounds) * self.cache.read(DIRECTION, 1)[0]))
        self.x = P.screen_c[0]
        self.x = P.screen_c[0] + self.velocity

        # dev tool for logically controlling the influences on target velocity; should be removed for prod.
        self.cfg = {
            'mouse_input': True,
            'acceleration': False,
            'track_input': False,
            'poll_while_moving': True,
            'poll_at_fixation': False,
            'exp_duration': 150,
            'trial_count': 9,
            'trial_interval_bounds': [10, 15],
            'reset_target_after_poll': True
        }

    def generate_trials(self):
        interval_count = self.cfg['trial_count'] + 1  # because trials are bookended by intervals
        min_t, max_t = self.cfg['trial_interval_bounds'][0], self.cfg['trial_interval_bounds'][1]  # verbosity fail

        if min_t * interval_count > self.cfg['exp_duration']:
            raise ValueError('Minimum interval between trials too large; cannot be run within experiment duration.')

        # the * 1.0 is to prevent rounding errors
        if self.cfg['exp_duration'] * 1.0 / max_t > interval_count:
            raise ValueError('Maximum interval between trials too small; all trials will complete too soon.')

        max_t += 1  # otherwise this value can't be returned by randrange() below

        # generate enough intervals for each trial
        self.intervals = [randrange(min_t, max_t) for i in range(0, interval_count)]

        # adjust intervals at random, whether over exp_duration or under, until that exact value is reached
        while sum(self.intervals) < self.cfg['exp_duration']:
            trial_index = randrange(0, len(self.intervals))
            if self.intervals[trial_index] <= self.cfg['trial_interval_bounds'][1]:
                self.intervals[trial_index] += 1

        while sum(self.intervals) > self.cfg['exp_duration']:
            trial_index = randrange(0, len(self.intervals))
            if self.intervals[trial_index] >= self.cfg['trial_interval_bounds'][0]:
                self.intervals[trial_index] -= 1

    def __fetch_response(self, event_queue):
        if not self.polling:
            return
        for event in event_queue:
            if event.type == SDL_KEYDOWN:
                key = event.key.keysym  # keyboard button event object
                if key.sym is sdl2.keycode.SDLK_SPACE:
                    self.cache.write(RESPONSE,
                                     (now() - self.polling) * 1000)  # Record time between poll onset & response, in ms
                    self.polling = False
                    if self.cfg['reset_target_after_poll']:
                        self.x = P.screen_c[0]

    def refresh(self, event_queue):
        try:
            # the if clause, here, prevents the first poll from happening immediately since the sum of 0 is 0
            next_poll_time = sum(self.intervals[0:self.cache.len(RESPONSE) + 1]) if self.cache.len(RESPONSE) else \
                self.intervals[0]
            if (now() - self.__init_time) > next_poll_time and not self.polling:
                self.polling = now()  # we overload this property a touch; we're storing precise start time here, too

            # we wrap __refresh so we don't have to fall into recursion when handling errors
            self.__fetch_response(event_queue)
            self.__refresh(event_queue)
        except ValueError as e:
            self.cache.write(VELOCITY, 0)
            self.accelerator.reset()
            self.__change_direction()
            self.refresh()

    def __capture_input(self, event_queue):
        for event in event_queue:
            if event.type == sdl2.SDL_MOUSEMOTION:
                # print "\tMOTION: {0}, {1}".format(event.motion.xrel, event.motion.timestamp)
                self.cache.write(MOUSE, event.motion.xrel, event.motion.timestamp)

        try:
            delta_t = self.cache.read(MOUSE, 1)[1] - self.cache.read(MOUSE, 2)[1]
            delta_d = self.cache.read(MOUSE, 1)[0]
        except IndexError:  # until two motion events have been detected, this comparison must fail
            return

        try:
            self.mouse_v = delta_d / delta_t
        except (ZeroDivisionError, TypeError):
            self.mouse_v = 0

        # because the mouse cursor is hidden, users can't tell when they've hit the window edge and are no longer
        # moving the cursor despite moving the mouse; so we warp the mouse back to screen center on every pass
        # such that all input translates to capturable cursor activity
        mouse_pos(False, P.screen_c)

    def __change_direction(self, update_direction):
        ''' We want to change direction whenever velocity falls below 1px/s (which, visually, is essentially zero v);
        and we also want to ensure that the user input can't so overpower the target that a jerky hand-motion can
        abruptly send the target careering off at light speed; so we halt the target and manually reset direction,
        velocity and acceleration'''
        # if responding to a mouse-induced change, the sign of the velocity will not agree with the
        new_direction = -direction_of(self.cache.read(VELOCITY, 2 if update_direction else 1)[0])
        self.cache.write(DIRECTION, new_direction)
        self.cache.write(VELOCITY, randrange(*self.velocity_bounds) * new_direction)

    def __refresh(self, event_queue):
        """ Basically, sequentially apply the relevant influences to target velocity, update target position before
        each pass of __render(), which does the actual blit-flip business. """

        if self.cfg['poll_while_moving'] or not self.polling:  # ie. don't do this if both are True
            if self.cfg['acceleration']:
                self.velocity = self.velocity + self.direction * self.accelerator.gain()

            if self.cfg['mouse_input']:
                self.__capture_input(event_queue)
                try:
                    # "new velocity  is the current velocity plus a value for mouse
                    # velocity expressed as a fraction of it's inverse power function;
                    # jon doesn't know this math, it just means that as mouse velocity gets bigger
                    # it's contribution to target velocity gets smaller so that user input doesn't attempt warp 10
                    self.velocity = self.velocity + self.mouse_v / power(abs(self.mouse_v), 1.0 / abs(self.mouse_v))
                except (TypeError, IndexError, ZeroDivisionError) as e:
                    # until two entries exist in the cache, this call will fail
                    pass
            try:
                # if the direction of travel in the previous refresh isn't the same as it is now, do a direction change
                if direction_of(self.cache.read(VELOCITY, 2)[0]) is not direction_of(self.cache.read(VELOCITY, 1)[0]):
                    self.__change_direction(False)

                # similarly, if velocity falls below 1px/s, treat this as essentially
                # zero velocity & do a direction change
                if abs(self.velocity) < 1.0:
                    self.__change_direction(True)

            except IndexError:
                pass  # again, until two entries exist, 1-back -> 2-back comparisons fail

            # we use the x.setter rather than writing to the cache directly to catch values of x that break things
            self.x = self.x + ((now() - self.cache.read(TARGET, 1)[1]) * self.velocity)

        # blit them shits
        self.__render()

    def __render(self):
        ''' Isn't it nice to read some code you just automatically understand? Ok have a nice day.'''

        target_loc = P.screen_c if self.cfg['poll_at_fixation'] and self.polling else [self.x, P.screen_c[1]]

        # fill(self.exp.palette['grue'] if abs(self.velocity) < self.max_velocity else self.exp.palette['klorange'])
        fill(self.exp.palette['grue'])
        blit(self.assets['fixation'], BL_CENTER, P.screen_c)
        blit(self.assets['target_wrapper'], BL_CENTER, target_loc)

        if self.cfg['track_input']:
            blit(self.assets['cursor'], BL_CENTER, mouse_pos())

        if (self.polling):
            digit_str = str((now() - self.polling) * 1000)[0:4]
            if digit_str[-1] == ".":
                digit_str = digit_str[0:3]
            digits = message(digit_str, 'target_digits', target_loc, flip_screen=False, blit_txt=False)
            blit(digits, BL_CENTER, target_loc)
        else:
            blit(self.assets[TARGET], BL_CENTER, target_loc)

        flip()

    # A note on these properties--they are a bit redundant with Cache.read(); however, in context, it's a helluva lot
    # easier to parse the code above when things are semantically referenced. And, additionally, the setters do some
    # work in sanitizing values. But yes, mostly, these are syntactic sugar
    @property
    def direction(self):
        return LEFT if self.velocity < 0 else RIGHT

    @property
    def x(self):
        return self.cache.read(TARGET, 1)[0]

    @x.setter
    def x(self, val):
        # don't let anything write the target off screen
        if int(val) not in range(*self.x_bounds):
            val = self.x_bounds[0] if val < self.x_bounds[0] else self.x_bounds[1]
        self.cache.write(TARGET, val)

    @property
    def velocity(self):
        return self.cache.read(VELOCITY, 1)[0]

    @velocity.setter
    def velocity(self, val):
        self.cache.write(VELOCITY, self.direction * self.max_velocity if abs(val) > self.max_velocity else val)

    @property
    def mouse_v(self):
        try:
            return self.cache.read(MOUSE_V, 1)[0]
        except IndexError:
            return 0

    @mouse_v.setter
    def mouse_v(self, val):
        # this setter, aside from maintaining a certain continuity, is here in case logic is ever required to modify
        # mouse velocity values before they're used elsewhere in the program
        self.cache.write(MOUSE_V, val)
