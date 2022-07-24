# Run tiled operations on corresponding hardware modules

import os
import math
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec

from ops import *
from tiled_ops import *
from modules import *
from pe import ProcessingElement
from buffer import Buffer


class Accelerator(object):
	"""Accelerator class
	
	Attributes:
		pes (list): list of ProcessingElement objects
		activation_buffer (Buffer): Buffer class object for activations
		mask_buffer (Buffer): Buffer class object for binary masks
		weight_buffer (Buffer): Buffer class object for weights
	"""
	def __init__(self, config, constants):
		self.pes = []
		for p in range(config['pe']):
			self.pes.append(ProcessingElement(f'pe{p}', config, constants))

		self.activation_buffer = Buffer('activation', config, constants)
		self.weight_buffer = Buffer('weight', config, constants)
		self.mask_buffer = Buffer('mask', config, constants)

		self.area = 0
		for pe in self.pes:
			self.area += pe.area
		self.area = self.area + self.activation_buffer.area + self.weight_buffer.area + self.mask_buffer.area

		self.cycle = 0

		# TODO: add main memory object with its leakage energy

	def set_required(self, compute_op):
		for data_name in compute_op.required_in_buffer:
			if self.activation_buffer.data_in_buffer(data_name):
				self.activation_buffer.get_data(data_name).required_in_buffer = True
			if self.weight_buffer.data_in_buffer(data_name):
				self.weight_buffer.get_data(data_name).required_in_buffer = True
			if self.mask_buffer.data_in_buffer(data_name):
				self.mask_buffer.get_data(data_name).required_in_buffer = True

	def set_not_required(self, compute_op):
		assert compute_op.done is True
		for data_name in compute_op.required_in_buffer:
			if self.activation_buffer.data_in_buffer(data_name):
				self.activation_buffer.get_data(data_name).required_in_buffer = False
			if self.weight_buffer.data_in_buffer(data_name):
				self.weight_buffer.get_data(data_name).required_in_buffer = False
			if self.mask_buffer.data_in_buffer(data_name):
				self.mask_buffer.get_data(data_name).required_in_buffer = False

	def all_macs_free(self):
		for pe in self.pes:
			for mac_lane in pe.mac_lanes:
				if not mac_lane.ready: return False
		return True

	def plot_utilization(self, utilization_dir):
		if not os.path.exists(utilization_dir): os.makedirs(utilization_dir)

		fig = plt.figure()
		buff_grid, pe_grid_sup = gridspec.GridSpec(1, 2, hspace=0, wspace=0.05, width_ratios=[1, 4])
		pe_grid = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=pe_grid_sup, hspace=0, wspace=0)

		act_buff, weight_buff, mask_buff = gridspec.GridSpecFromSubplotSpec(3, 1, 
			subplot_spec=buff_grid, hspace=0, wspace=0, height_ratios=[self.activation_buffer.buffer_size, self.weight_buffer.buffer_size, self.mask_buffer.buffer_size])

		num_ones = math.ceil(self.activation_buffer.used * 1.0 / self.activation_buffer.buffer_size * self.activation_buffer.buffer_size * 16)
		act_arr = np.zeros((self.activation_buffer.buffer_size, 16))
		count = 0
		for i in range(act_arr.shape[0]):
			for j in range(act_arr.shape[1]):
				act_arr[i, j] = 1
				count += 1
				if count == num_ones: break

		act_ax = plt.Subplot(fig, act_buff)
		act_ax.imshow(act_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Greys', vmin=0, vmax=1.5)
		act_ax.set_xticks([])
		act_ax.set_yticks([])
		fig.add_subplot(act_ax)

		num_ones = math.ceil(self.weight_buffer.used * 1.0 / self.weight_buffer.buffer_size * self.weight_buffer.buffer_size * 16)
		weight_arr = np.zeros((self.weight_buffer.buffer_size, 16))
		count = 0
		for i in range(weight_arr.shape[0]):
			for j in range(weight_arr.shape[1]):
				weight_arr[i, j] = 1
				count += 1
				if count == num_ones: break

		weight_ax = plt.Subplot(fig, weight_buff)
		weight_ax.imshow(weight_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Greys', vmin=0, vmax=1.5)
		weight_ax.set_xticks([])
		weight_ax.set_yticks([])
		fig.add_subplot(weight_ax)

		num_ones = math.ceil(self.mask_buffer.used * 1.0 / self.mask_buffer.buffer_size * self.mask_buffer.buffer_size * 16)
		mask_arr = np.zeros((self.mask_buffer.buffer_size, 16))
		count = 0
		for i in range(mask_arr.shape[0]):
			for j in range(mask_arr.shape[1]):
				mask_arr[i, j] = 1
				count += 1
				if count == num_ones: break

		mask_ax = plt.Subplot(fig, mask_buff)
		mask_ax.imshow(mask_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Greys', vmin=0, vmax=1.5)
		mask_ax.set_xticks([])
		mask_ax.set_yticks([])
		fig.add_subplot(mask_ax)

		for pe_col in pe_grid:
			pes = gridspec.GridSpecFromSubplotSpec(len(self.pes)/4, 1, wspace=0, hspace=0,
				subplot_spec=pe_col)
			pe_count = 0
			for pe in pes:
				mac_lanes, sp_modules = gridspec.GridSpecFromSubplotSpec(2, 1, wspace=0, hspace=0, 
					height_ratios=[2, 1], subplot_spec=pe)
				
				ln, sftm = gridspec.GridSpecFromSubplotSpec(1, 2, wspace=0, hspace=0, subplot_spec=sp_modules)

				mac_lane_arr = np.zeros((2, len(self.pes[pe_count].mac_lanes)/2))
				mac_lane_count = 0
				for i in range(mac_lane_arr.shape[0]):
					for j in range(mac_lane_arr.shape[1]):
						mac_lane_arr[i, j] = 1 if not self.pes[pe_count].mac_lanes[mac_lane_count].ready else 0
						mac_lane_count += 1
				
				ax = plt.Subplot(fig, mac_lanes)
				ax.imshow(mac_lane_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Blues', vmin=0, vmax=1.5)
				ax.set_xticks([])
				ax.set_yticks([])
				fig.add_subplot(ax)
				
				ln_arr = np.zeros((1, 1))
				ln_arr[0][0] = 1 if not self.pes[pe_count].layer_norm.ready else 0

				ax = plt.Subplot(fig, ln)
				ax.imshow(ln_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Purples', vmin=0, vmax=1.5)
				ax.set_xticks([])
				ax.set_yticks([])
				fig.add_subplot(ax)

				sftm_arr = np.zeros((1, 1))
				sftm_arr[0][0] = 1 if not self.pes[pe_count].softmax.ready else 0
				
				ax = plt.Subplot(fig, sftm)
				ax.imshow(sftm_arr, interpolation='none', aspect='auto', 
						  rasterized=True, cmap='Greens', vmin=0, vmax=1.5)
				ax.set_xticks([])
				ax.set_yticks([])
				fig.add_subplot(ax)

		fig.subplots_adjust(wspace=0, hspace=0)
		fig.sup_title(f'Cycle: {self.cycle}')
		plt.savefig(os.path.join(utilization_dir, f'cycle_{self.cycle}.pdf'), dpi=300)

	def process_cycle(self, memory_ops, compute_ops):
		total_pe_energy = [0, 0]
		for pe in self.pes:
			pe_energy = pe.process_cycle()
			total_pe_energy[0] += pe_energy[0]; total_pe_energy[1] += pe_energy[1]

		activation_buffer_energy = self.activation_buffer.process_cycle()
		weight_buffer_energy = self.weight_buffer.process_cycle()
		mask_buffer_energy = self.mask_buffer.process_cycle()

		# Mark operations as done if their corresponding modules are ready
		activation_memory_ops = [op for op in memory_ops if op.data_type == 'activation']
		weight_memory_ops = [op for op in memory_ops if op.data_type == 'weight']
		if self.activation_buffer.ready:
			for memory_op in activation_memory_ops:
				if memory_op.done == False:
					memory_op.done = True
					break
		if self.weight_buffer.ready:
			for memory_op in weight_memory_ops:
				if memory_op.done == False:
					memory_op.done = True
					break

		# If a compute_op is done, its corresponding data is not required in buffer anymore
		for compute_op in compute_ops:
			if compute_op.done == True:
				self.set_not_required(compute_op)
			else:
				break

		# All energy in nJ
		return tuple(total_pe_energy), activation_buffer_energy, weight_buffer_energy, mask_buffer_energy

	def assign_op(self, op):
		assert op.compute_op is True
		assigned_op = False

		for pe in self.pes:
			assigned_op = pe.assign_op(op)
			if assigned_op == True: break

		return assigned_op

