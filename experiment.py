# -*- coding: utf-8 -*-

__author__ = "J Mulle"

import klibs
from klibs import P
from klibs.KLGraphics import *
from klibs.KLGraphics.KLNumpySurface import *
from klibs.KLGraphics.KLDraw import *
from klibs.KLUtilities import *
from klibs.KLUserInterface import *
from klibs.KLCommunication import *
from PVTarget2 import *
from klibs.KLConstants import *
from random import randrange
from math import radians
import subprocess
from CartesianScreen import CartesianScreen
from collections import namedtuple as nt

'''
Note:

Most of the functionality in this experiment is concerned with the drawing and moving of the target, almost all of which
is encapsulated in the PVTarget class (ExpAssets/Resources/Code/PVTarget.py). Similarly, "trials' in this case are 
part of a continuous process, therefore data is also and collected and written within this class (and thus the 'single-
trial' experiment).
'''



class PhysicsEngine(klibs.Experiment):
	cartesian_grid = CartesianScreen()
	pvt_machine = None
	cursor = None
	user_is_a_fucking_fail = 0
	user_failed_too_fucking_hard = None
	still_fucking_with_cursor = False
	assets = {}
	palette = {
				'grue': 	(025, 025, 28),  # mysteriously, leading zero throws a syntax error in last value
				'klorange': (255, 176, 052),
				'white': 	(255, 255, 255),
				'red': 		(255, 000, 000),
				'black': 	(000, 000, 000),
				'green': 	(000, 255, 000),
			  }

	metrics = {
				'abs_unit': 45,  # px; in Makeig & Jolley this is "1 d.r", but that's not very accurate nomenclature
				'inner_disc_radius': [6, None, None],
				'outer_disc_radius': [20, None, None],
				'fixation_radius': [1, None, None],
				'target_frame_h': [3, None, None],
				'target_frame_w': [6, None, None],
				'target_h': [1.8, None, None],
				'cursor': [0.75, None, None]
			  }

	def setup(self):
		# PVTarget's mouse velocity algo triggers OS X's Settings->Accessibility->Display->Shake Mouse Pointer To Locate
		if not P.development_mode:
			self.check_osx_mouse_shake_setting()

		self.txtm.add_style('UserAlert', 16, self.palette['red'])

		# all graphical aspects of the program are derived from an arbitrary base unit
		for asset in self.metrics:
			if asset is 'abs_unit':
				continue
			self.metrics[asset][1] = self.metrics['abs_unit'] * self.metrics[asset][0]
		self.pvt_machine = PVTarget2()
		self.pvt_machine.generate_trials()

		#######################################
		#									  #
		#		RAY SETTINGS ARE HERE		  #
		#									  #
		#######################################
		self.pvt_machine.velocity_bounds = [5.0, 10.0]  # px/s  must be a float
		# this next one is measured in px/s, but is expressed here as 5% of the monitor in one step; any integer
		# is also fine as a value. warning: this gets crazy quickly, think small
		self.pvt_machine.max_velocity = 0.05 * P.screen_x
		self.pvt_machine.cfg['exp_duration'] = 300  # seconds
		self.pvt_machine.cfg['trial_interval_bounds'] = [10, 15]  # min/max, seconds
		self.pvt_machine.cfg['poll_while_moving'] = True
		self.pvt_machine.cfg['poll_at_fixation'] = True  # this overrides poll_while_moving
		self.pvt_machine.cfg['reset_target_after_poll'] = True  # sets target back to fixation after a response
		self.pvt_machine.cfg['track_input'] = True  # decides whether cursor is visible
		self.pvt_machine.cfg['mouse_input'] = True  # target will ignore user-input

		clear()
		flip()
		mouse_pos(False, P.screen_c)
		hide_mouse_cursor()
		then = now()
		while (now() - then) < 60:
			events = pump(True)
			self.pvt_machine.refresh(events)
			ui_request(queue=events)
		exit()
		# -----------------------------------------!!! TEST  ENDS  HERE !!! -----------------------------------------


		self.pvt_machine.test_force(1, 1, 25)


		exit()

	def block(self):
		pass

	def setup_response_collector(self):
		pass


	def trial_prep(self):
		if self.user_failed_too_fucking_hard:
			self.slap_that_bitch_awake()
		self.still_fucking_with_cursor = True


	def trial(self):
		while self.still_fucking_with_cursor:
			pass
			# self.fuck_around_with_cursor_for_a_bit(self.cursor.gps)
			# self.draw_that_shit()

		while not self.cursor.middled:
			pass
			# self.get_middler()
			# self.draw_that_shit()

		self.red_alert_bitches()

		self.analyze_panic()

		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number
		}


	def trial_clean_up(self):
		pass


	def clean_up(self):
		pass

	def render(self):
		fill()


	def check_osx_mouse_shake_setting(self):
		p = subprocess.Popen("defaults read ~/Library/Preferences/.GlobalPreferences CGDisableCursorLocationMagnification 1", shell=True)
		if p is 0:
			fill(self.palette['grue'])
			blit(NumpySurface(import_image_file('ExpAssets/Resources/image/accessibility_warning.png')), 5, P.screen_c)
			msg = 'Please ensure cursor shake-magnification is off before running this experiment.'
			x_pos = int((P.screen_y - 568) * 0.25) + 16
			message(msg, 'UserAlert', [P.screen_c[0], x_pos], 5)
			flip()
			any_key()
			qui()
