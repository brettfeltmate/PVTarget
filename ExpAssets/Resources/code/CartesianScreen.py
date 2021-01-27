from klibs.KLUtilities import iterable
# todo: add this shit to klibs


not_all_numbers = "Not all members of argument '{0}' were found to be numbers."
not_all_int = "Not all members of argument '{0}' were found to be integers."
not_a_number = "Argument '{0}' must be a number; {1} passed."
not_iterable = "Argument '{0}}' must be iterable; {1} passed."


class CartesianScreen(object):

	def __init__(self, screen_size=None, origin=None, abs_bounds=None):
		super(CartesianScreen, self).__init__()

		self.initialized = False

		try:
			self.initialize(screen_size, origin, abs_bounds)
		except TypeError:
			pass

	# initialization's done  in a separate method b/c the expected use-case for it  may require it to be created at
	# runtime, before KLParams.screen_xy is initialized, which in turn is almost certainly going to be the most common
	# x/y_max value
	def initialize(self, screen_size, origin=None, abs_bounds=None):
		for v in screen_size, origin:
			try:
				assert(all([type(d) is int for d in v]))
			except AssertionError:
				raise TypeError(not_all_int.format(v.__repr__()))
		try:
			assert (all([type(d) in [int, float, long] for d in abs_bounds]))
		except AssertionError:
			raise TypeError(not_all_numbers.format(abs_bounds.__repr__()))

		self.__x_px, self.__y_px = screen_size
		self.__origin = None
		self.__x_scale = 1.0 if abs_bounds is None else screen_size[0] / abs_bounds[0] * 1.0
		self.__y_scale = 1.0 if abs_bounds is None else screen_size[1] / abs_bounds[1] * 1.0
		self.initialized = True
		self.origin = origin

	def __init_check(self):
		if not self.initialized:
			raise RuntimeError("Instance of CartesianScreen has not been initialized ")

	def cartesian_pos(self, screen_pos):
		self.__init_check()
		try:
			iter(screen_pos)
			assert (all([type(d) in [int, float, long] for d in screen_pos]))
		except TypeError:
			raise TypeError(not_iterable.format('screen_pos', type(screen_pos)))
		except AssertionError:
			raise TypeError(not_all_numbers.format('screen_pos'))
		x, y = screen_pos
		x_px = self.origin[0] + (x - self.origin[0])
		y_px = self.origin[1] - (y - self.origin[1])
		return [x_px / self.__x_scale, y_px / self.__y_scale]

	def cartesian_dist(self, screen_dist, scale_axis='x',  preserve_sign=True):
		if scale_axis not in ['x', 'y']:
			raise ValueError("CartesianScreen.screen_dist() requires argument 'scale_axis' to be either 'x' or 'y'.")
		try:
			assert (type(screen_dist) in [int, long, float])
		except AssertionError:
			raise TypeError(not_a_number.format('cartesian_dist', screen_dist))
		if self.__x_scale is self.__y_scale:
			cart_dist = screen_dist / self.__x_scale
		else:
			cart_dist = screen_dist / (self.__x_scale if scale_axis is 'x' else self.__y_scale)
		# print cart_dist
		return abs(cart_dist)

	def screen_pos(self, cartesian_pos):
		self.__init_check()
		try:
			assert (all([type(d) in [int, float, long] for d in cartesian_pos]))
		except AssertionError:
			raise TypeError(not_all_int.format(cartesian_pos.__repr__()))
		x = int(self.origin[0] + self.screen_dist(cartesian_pos[0]))
		y = int(self.origin[1] - self.screen_dist(cartesian_pos[1]))
		return x, y

	def screen_dist(self, cartesian_dist, scale_axis='x', preserve_sign=False):
		if scale_axis not in ['x', 'y']:
			raise ValueError("CartesianScreen.screen_dist() requires argument 'scale_axis' to be either 'x' or 'y'.")
		try:
			assert (type(cartesian_dist) in [int, long, float])
		except AssertionError:
			raise TypeError(not_a_number.format('cartesian_dist', cartesian_dist))
		if self.__x_scale is self.__y_scale:
			screen_dist = cartesian_dist * self.__x_scale
		else:
			screen_dist = cartesian_dist * (self.__x_scale if scale_axis is 'x' else self.__y_scale)
		return abs(screen_dist) if not preserve_sign else screen_dist

	def within_x(self, val, val_is_cartesian=False):
		self.__init_check()
		try:
			assert(type(val) in [int, long, float])
		except AssertionError:
			raise TypeError(not_a_number.format('val', val))
		if val_is_cartesian:
			val = self.screen_dist(float(val))
		return self.x_screen_range[0] <= val <= self.x_screen_range[1]

	def within_y(self, val, val_is_cartesian=False):
		self.__init_check()
		try:
			assert (type(val) in [int, long, float])
		except AssertionError:
			raise TypeError(not_a_number.format('val', val))
		if val_is_cartesian:
			val = self.screen_dist(val, 'y')
		return self.y_screen_range[0] <= val <= self.y_screen_range[1]

	def within(self, vals, val_is_cartesian=False):
		self.__init_check()
		try:
			iter(vals)
		except TypeError:
			raise TypeError(not_iterable.format('vals', type(vals)))
		return self.within_x(vals[0], val_is_cartesian) and self.within_y(vals[1], val_is_cartesian)

	@property
	def x_screen_range(self):
		return [0, self.__x_px]

	@property
	def y_screen_range(self):
		return [0, self.__y_px]

	@property
	def origin(self):
		return self.__origin

	@origin.setter
	def origin(self, screen_pos=None):
		self.__init_check()
		if not screen_pos:
			self.__origin = self.__x_px // 2, self.__y_px // 2
		else:
			try:
				iter(screen_pos)
				(all([type(d) is int for d in screen_pos]))
			except TypeError:
				raise TypeError(not_iterable.format('xy_pos', type(screen_pos)))
			except AssertionError:
				raise TypeError("Coordinate values for origin must be integers")

			if not self.within(screen_pos):
				raise ValueError("The provided origin is outside screen bounds.".format(screen_pos[0]))

			self.__origin = screen_pos

	@property
	def scale(self):
		return self.__x_scale, self.__y_scale

