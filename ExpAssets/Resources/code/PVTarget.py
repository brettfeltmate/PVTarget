from math import cos, sin, sqrt, pi, pow, radians
from random import randrange

from klibs import P
from klibs.KLParams import PILOT_MODE, RESPONSE_MODE
from klibs.KLGraphics.KLNumpySurface import *
from klibs.KLGraphics.KLDraw import *
from klibs.KLUtilities import *
from klibs.KLEnvironment import EnvAgent
from klibs.KLUserInterface import *
from klibs.KLCommunication import *
from klibs.KLConstants import *
from klibs.KLTime import precise_time
from klibs.KLGraphics.colorspaces import const_lum
from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS
from experiment import PhysicsEngine


coefficients = {
				'drag': 0.957,
				'inertia': 0.0003,
				'gravity': 0.0005382,
				'env_input': .00008288
			   }

c_x = (1 + sqrt(5)) / 2.0  # no clue what these are or which units it describes
c_y = pi / 2.0  # just lifted it  from Makeig & Jolley, 1996


# these are simply for syntactic tidiness:
def d(n): return n * coefficients['drag']


def i(n): return n * coefficients['inertia']


def g(n): return n * coefficients['gravity']


def e(n): return n * coefficients['env_input']


def px_to_m(px):
	return px / P.ppi * 0.00254



# easier to encapsulate in an iterator the persistent frames retrieved in order, but honestly this is a bit much lol
#todo: add this to KLAnimate
class FrameIterator(object):

		def __init__(self):
			self.__frames = []
			self.length = 0
			self.i = 0


		def add_frame(self, frame):
			self.__frames.append(frame)
			self.length = len(self.__frames)


		def next(self):  # alias for python2
			return self.__next__()

		def skip_to(self, index):
			self.i = index

		def reset(self):
			self.i = 0


		def __iter__(self):
			return self


		def __len__(self):
			return self.length


		def __getitem__(self, i):
			return self.blocks[i]


		def __setitem__(self, i, x):
			self.frames[i] = x


		def __next__(self):
			if self.i >= self.length:
				self.i = 0  # reset index so we can iterate over it again
				raise StopIteration
			else:
				self.i += 1
				return self.__frames[self.i]



class PVTarget(EnvAgent):

	def __init__(self, refresh_mode=None):
		super(PVTarget, self).__init__()

		'''
		Ok. I shorthanded this shit b/c I  hate typing informative but long methods/properties over and over again.
		Also the requirement of Params.screen_xy to be initialized before the CartesianScreen can be itself init is why
		this shit is so hideously nested, just run with it
		'''
		self.cp = self.exp.cartesian_grid.cartesian_pos
		self.sp = self.exp.cartesian_grid.screen_pos
		self.cd = self.exp.cartesian_grid.cartesian_dist
		self.sd = self.exp.cartesian_grid.screen_dist

		# demo-controls for ray & testing
		self.using = {'m': False, 'd': False, 'i': False, 'g': True, 'e': False, 'e2': False}
		self.restrict_y = False
		# these lines just for tidy expression
		m = self.exp.metrics
		p = self.exp.palette
		self.__refresh_mode = None  	# best to require the exp to always explicitly set this
		self.__last_mode_change = None
		self.__history = {'mouse': [], 'target': []}
		self.phase_angles = [radians(randrange(-361, 361)) for i in range(0, 6)]
		self.txtm.add_style('Target', m['target_h'][2], p['red'])
		self.assets = {}
		self.assets['target'] = message('XXX', 'Target', blit_txt=False)
		self.assets['target_wrapper'] = Rectangle(m['target_frame_w'][2], m['target_frame_h'][2],
												  [2, p['red'], STROKE_OUTER]).render()
		self.assets['counter_frames'] = FrameIterator()

		# pre-render count-up frames
		for i in range(0, 67):
			int_str = str_pad(str(i), 3, '0', 'l') if i < 100 else str(i)
			self.assets['counter_frames'].add_frame(message(int_str, 'Target', blit_txt=False))

		self.__x = None
		self.__y = None
		self.xy = (5.0, 5.0)
		self.last_mouse_position = mouse_pos()
		self.refresh_mode = refresh_mode
		# print [self.sp([10, 10]), self.sp([-10, -10]), self.sp([10, -10]), self.sp([-10, 10])]
		# print [self.cp([1480, 1220]), self.cp([1480, 820]), self.cp([1080, 1220]), self.cp([1080, 820])]
		# fill()
		# r_dot = Ellipse(5, 5, [1, (255,0,0)], [255, 0, 0])
		# b_dot = Ellipse(5, 5, [1, (0,0,255)], [0, 0, 255])
		# blit(r_dot, 5, self.sp([10, 10]))
		# blit(r_dot, 5, self.sp([-10, -10]))
		# blit(r_dot, 5, self.sp([10, -10]))
		# blit(r_dot, 5, self.sp([-10, 10]))
		# blit(b_dot, 5, self.cp([1480, 1220]))
		# blit(b_dot, 5, self.cp([1480, 820]))
		# blit(b_dot, 5, self.cp([1080, 1220]))
		# blit(b_dot, 5, self.cp([1080, 820]))
		# flip()
		# any_key()
		# self.exp.quit()

		clear()

	def test_force(self, mouse_coef, buff_coef, duration):
		mouse_pos(False, P.screen_c)
		self.last_mouse_position = mouse_pos()
		dot = Ellipse(10, fill=(211, 63, 106, 255))
		coords = [P.screen_c]

		then = self.time
		i = 0
		# for a in range(0, 361,15):
		# 	x, y = randrange(640, 1920), randrange(480, 1440)
		# 	d_dx = randrange(100, 500)
		# 	pos_dx = [(d_dx * cos(radians(a))), (d_dx * sin(radians(a)))]
		# 	new_pos = (x + pos_dx[0], y + pos_dx[1])
		# 	args = [a, x, y, d_dx, pos_dx[0], pos_dx[1], new_pos[0], new_pos[1], line_segment_len(new_pos, [x,y])]
		# 	print "a: {0}  |  pos: ({1},{2})  |  d_dx: {3}  |  pos_dx: ({4}, {5})  |  new_pos: ({6},{7})  |  lsl:{8}".format(*args)
		# self.exp.quit()
		fix = FixationCross(20, 4, [3, [255,255,255,255]])
		while self.remaining(then, duration):
			fill()
			prev = self.last_mouse_position[0]
			# if True:
			# 	prev = self.last_mouse_position[0]
			# 	self.last_mouse_position = mouse_pos()
			# 	mouse_pos(False, P.screen_c)
			# 	hide_mouse_cursor()
			# 	angle_between(prev, self.last_mouse_position[0])
			self.last_mouse_position = mouse_pos()
			if self.last_mouse_position[0] in [0, P.screen_x] or self.last_mouse_position[1] in [0, P.screen_y]:
				mouse_pos(False, P.screen_c)
			# mouse_pos(False, P.screen_c)
			# mouse_pos(False, P.screen_c)
			hide_mouse_cursor()
			last_x = coords[-1][0]
			last_y = coords[-1][1]
			ui_request()
			curs = cursor(self.exp.palette['klorange'])
			pos_dx = None
			# if f is 'buffet':
			buff_dx = self.buffet_x, self.buffet_y
				# new_pos = last_x + self.buffet_x, last_y + self.buffet_y
			# elif f is 'mouse':
			a = angle_between(self.sp(prev), self.sp(self.last_mouse_position[0]))
			d_dx = line_segment_len(self.sp(prev), self.sp(self.last_mouse_position[0]))
			# d_dx = sd(self.mouse_velocity())
			pos_dx = [mouse_coef * d_dx * cos(radians(a)), mouse_coef * d_dx * sin(radians(a))]

			new_pos = [buff_coef * buff_dx[0] + last_x + pos_dx[0], buff_coef * buff_dx[1] + last_y - pos_dx[1]]
			lsl = line_segment_len(new_pos, coords[-1])
			args = [a, last_x, last_y, d_dx, pos_dx[0], pos_dx[1], new_pos[0], new_pos[1], lsl]
			# print "a: {0}  |  pos: ({1},{2})  |  d_dx: {3}  |  pos_dx: ({4}, {5})  |  new_pos: ({6},{7})  |  lsl:{8}".format(*args)
			# new_pos = (last_x + (last_x - pos_dx[0]), last_y + (last_y - pos_dx[1]))
			# print pos_dx
			# print "test_force() >>> new_pos: {0},{1}".format(*new_pos)
			coords.append(new_pos)
			self.xy = self.cp(new_pos)
			blit(fix, 5, P.screen_c)
			blit(self.assets['target'], 5, coords[-1])
			# blit(curs, 5,mouse_pos())
			# blit
			flip()
			# try:
			# 	blit(dot, 5, coords[-1])
			# except IndexError:
			# 	pass
			# flip()


	def remaining(self, start, end):
		left = end - (self.time - start)
		return False if left <= 0 else left


	def __render(self):
		fill()
		print "xy: {0}, origin: {1}, screen_xy: {2}".format(self.xy, self.exp.cartesian_grid.origin, self.sp(self.xy))

		if self.refresh_mode is PILOT_MODE:
			loc = [self.sp(self.xy)[0], 720] if self.restrict_y else self.sp(self.xy)
			blit(self.assets['target_wrapper'], BL_CENTER, loc)
			blit(self.assets['target'], BL_CENTER, loc)
		else:

			frame = int(ceil(self.time / 0.016))  # roughly a screen refresh72
			self.assets['counter_frames'].skip_to(frame)
			blit(self.assets['target_wrapper'], BL_CENTER, P.screen_c)
			blit(self.assets['counter_frames'].next(), BL_CENTER, P.screen_c)
		flip()

	def refresh(self):
		# warps mouse to center of screen to prevent screen edge capping input values
		# mouse_pos(False, P.screen_c)
		hide_mouse_cursor()
		print "-" * 80
		# start computing the independent terms for adjusting the x,y pos of the PVTarget
		terms = {'x': [], 'y': []}

		if self.refresh_mode is PILOT_MODE:
			for axis in ['x', 'y']:

				# momentum
				terms[axis].append(self.n_back(1, axis) if self.using['m'] else 0)
				terms[axis].append(d(self.n_back(1, axis) - self.n_back(2, axis)) if self.using['d'] else 0)
				terms[axis].append(i(self.n_back(2, axis)) if self.using['i'] else 0)

				# surface force
				terms[axis].append(g(self.surface_force) if self.using['g'] else 0)

				# wind & input forces
				#terms[axis].append(e( self.mouse_velocity()) if self.using['e'] else 0)
				terms[axis].append(e(self.buffet_x if axis is "x" else self.buffet_y) if self.using['e'] else 0)
				terms[axis].append(e(self.buffet_x if axis is "x" else self.buffet_y + self.mouse_velocity()) if self.using['e2'] else 0)

			# update that shit
			print "X:{0} (nBack:{1}, d:{2}, i:{3}: g:{4}, e:{5}".format(sum(terms['x']), *terms['x'])
			print "Y:{0} (nBack:{1}, d:{2}, i:{3}: g:{4}, e:{5}".format(sum(terms['y']), *terms['y'])

			self.xy = (sum(terms['x']), sum(terms['y']))

		if not self.exp.cartesian_grid.within(self.xy, True):
			raise ValueError("Screen bounds exceeded; target position was {0}".format(self.sp(self.xy)))

		self.__render()

	def cache(self, data=None):
		if self.refresh_mode is RESPONSE_MODE:
			return
		if data:
			store = 'mouse'
		else:
			store = 'target'
			data = self.xy
		self.__history[store].append(data)

	def mouse_velocity(self):
		prev = self.last_mouse_position
		self.last_mouse_position = mouse_pos()
		d_t = self.last_mouse_position[1] - prev[1]
		d_d = line_segment_len(self.last_mouse_position[0], prev[0]) / 72 / 2.55 / 1000
		# print "d_dx: {0}, {1}".format(d_d, sd(d_d))
		return d_d / d_t

		# return d_d

	def n_back(self, n=1, axis=None):
		# for the first two passes there won't be enough history
		if len(self.__history['target']) < n:
			return self.n_back(n - 1, axis)

		if not axis:
			return self.__history['target'][-n]
		else:
			return self.__history['target'][-n][0] if axis is 'x' else self.__history['target'][-n][1]


	@property
	def time(self):
		try:
			return precise_time() - self.__last_mode_change
		except TypeError:
			return 0  # ie. experiment hasn't started yet

	@property
	def xy(self):
		return [self.__x, self.__y]

	@xy.setter
	def xy(self, vals):
		try:
			iter(vals)
		except TypeError:
			raise TypeError("PVTarget.xy must be iterable (ie. tuple, list); {0} provided.".format(type(vals)))
		self.__x, self.__y = vals
		self.cache()

	@property
	def x(self):
		return self.__x

	@property
	def y(self):
		return self.__y

	@property
	def fixation_r(self):
		# r = line_segment_len(self.xy, self.cp(P.screen_c)) / P.ppi * 0.00254
		# r2 = line_segment_len(self.xy, P.screen_c) / P.ppi * 0.00254
		r = line_segment_len(self.xy, self.cp(P.screen_c))
		print r
		return r if r else 1

	@property
	def surface_force(self):
		if self.fixation_r <= self.exp.metrics['inner_disc_radius'][2]:
			sf = pow(self.fixation_r, 2) * 0.5
		elif self.fixation_r <= self.exp.metrics['outer_disc_radius'][2]:
			sf = 1.5 * (self.fixation_r - self.exp.metrics['outer_disc_radius'][2])
		else:
			sf = 0
			# sf = 1.5 * (self.exp.metrics['outer_disc_radius'][2] - self.fixation_r)  #jc version
		return sf

	@property
	def refresh_mode(self):
		return self.__refresh_mode

	@refresh_mode.setter
	def refresh_mode(self, rmode):
		if rmode is None:
			return
		if rmode in [PILOT_MODE, RESPONSE_MODE] and rmode is not self.__refresh_mode:
			self.assets['counter_frames'].reset()
			self.__last_mode_change = precise_time()
			self.__refresh_mode = rmode

	@property
	def last_mouse_position(self):
		return self.__history['mouse'][-1]

	@last_mouse_position.setter
	def last_mouse_position(self, pos):
		pos = self.cp(pos)
		try:
			prev = self.__history['mouse'][-1]
		except IndexError:
			self.cache([pos, self.time])
			return
		try:
			two_back = self.__history['mouse'][-2]
			prev_v = line_segment_len(two_back[0], prev[0]) / prev[1] - two_back[1]
		except IndexError:
			prev_v = 0
		self.cache([pos, self.time])
		cur = self.last_mouse_position
		cur_v = line_segment_len(prev[0],cur[0]) / cur[1] - prev[1]
		fargs = [line_segment_len(prev[0],cur[0]), prev[0],cur[0], cur[1] - prev[1], prev[1], cur[1], cur_v, abs(cur_v - prev_v)]

		# print "Mouse dXY: {0} {{{1} -> {2}}}, dT: {3} {{{4} -> {5}}}, V:{6}, dV:{7}".format(*fargs)

	@property
	def buffet_x(self):
		return sum([pow(c_x, n) * cos(pow(c_x, n) * self.time + self.phase_angles[-n]) for n in range(0, -6, -1)])

	@property
	def buffet_y(self):
		return sum([pow(c_y, n) * sin(pow(c_y, n) * self.time + self.phase_angles[-n]) for n in range(0, -6, -1)])


