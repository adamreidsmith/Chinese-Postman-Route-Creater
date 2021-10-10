import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pygame.locals import *
import numpy as np
from numpy.linalg import norm, inv, LinAlgError
import osmnx as ox
from random import randint
from shapely.geometry import LineString
from networkx.exception import NetworkXError

DELETE = 'delete'
ZOOM = 'zoom'
ADD_NODES = 'add nodes'
ADD_EDGES = 'add edges'
START_NODE = 'set starting node'
UNDO = 'undo'
CONSOLIDATE_GRAPH = 'consolidate_graph'
DISPLAY_HELP = 'display_help'
TOGGLE_BACKGROUND = 'toggle_background'
ZOOM_IDENTITY = np.array([[1,0,0], [0,1,0]])

class GraphEdit:

	def __init__(self, G, surface, window_size, img_data=None):

		self.G = G
		self.surface = surface
		self.window_size = window_size
		self.close_clicked = False
		self.buffer = 10  # Sets a boarder of this many pixels in the visualization
		self.line_color = pygame.Color('white')
		self.bg_color = pygame.Color('black')
		self.main_node_color = pygame.Color('white')
		self.node_delete_color = pygame.Color(255, 0, 0)
		self.add_edge_node_color = pygame.Color(0, 240, 255)
		self.start_node_color = pygame.Color(0, 255, 0)
		self.message_bg_color = pygame.Color(200, 200, 200)
		self.mode_color = pygame.Color(186, 15, 18)
		self.node_radius = 4
		self.orig_x_bounds = self.get_x_bounds(self.G)
		self.orig_y_bounds = self.get_y_bounds(self.G)
		self.nodes_to_delete = []
		self.mode = ZOOM
		self.mode_dict = {K_z:ZOOM, 
						  K_d:DELETE, 
						  K_n:ADD_NODES, 
						  K_e:ADD_EDGES,
						  K_s:START_NODE,
						  K_c:CONSOLIDATE_GRAPH,
						  K_u:UNDO,
						  K_h:DISPLAY_HELP,
						  K_b:TOGGLE_BACKGROUND}
		self.zoom_box_on = False
		self.zoom_box_click_coords = None
		self.zoom_tlbr = ((0,0), window_size)
		self.zoom_matrix = ZOOM_IDENTITY
		self.reverse_zoom_matrix = ZOOM_IDENTITY
		self.zoomed = False
		self.graph_list = []
		self.consolidated = False
		self.edge_adder_node_id = None

		pygame.font.init()
		self.font_size = 14
		self.font = pygame.font.SysFont('arial', self.font_size)
		self.text_color = pygame.Color(0, 0, 0)
		self.text_buffer = 10

		self.message_on = True
		self.help_message = 'Welcome to Chinese Postman Interactive.\n\n' + \
							'This program has 5 modes:\nDELETE, ZOOM, ADD NODES, ADD EDGES, and SET STARTING NODE.\n' + \
							'The current mode is displayed in the upper left corner of the screen.\n' + \
							'Change modes by pressing the \'d\', \'z\', \'n\', \'e\', and \'s\' keys respectfully.\n' + \
							'To remove nodes, change to DELETE mode and click to select the nodes\n' + \
							'you wish to delete.  Then press the delete key to remove them.  Delete edges\n' +\
							'by selecting two nodes connected by an edge and pressing shift-delete.  To\n' + \
							'zoom, change to ZOOM mode and click and drag over thea area you wish to zoom in\n' + \
							'on.  Press the \'z\' key again or click to reset the zoom level.  In ADD NODES\n' + \
							'mode, you may click anywhere to add a node.  To add edges, change to ADD\n' + \
							'EDGES mode, click on two nodes consecutively, and enter an edge length.\n' + \
							'To set the starting node, change to SET STARTING NODE mode and click the\n' +\
							'desired node.  Press the \'u\' key at any time to undo.  Press \'c\' to invoke osmnx\'s\n' + \
							'consolidate_intersections method.  Press \'b\' to turn the background\n' + \
							'image on or off.  Press \'h\' to display this message and press any key\n' +\
							'to close it. Click DONE in the upper right corner when you are finished.'
		self.help_message = self.help_message.splitlines()
		self.message = self.create_message_surface(self.help_message)

		self.font.set_bold(True)
		self.mode_surfaces = {mode:self.font.render(mode.upper(), True, self.mode_color) \
							  for mode in (DELETE, ZOOM, ADD_EDGES, ADD_NODES, START_NODE)}
		self.font.set_bold(False)

		self.input_str = ''
		self.input_on = False
		self.input_message = None
		self.input_done = False
		self.bg_img = None
		self.bg_on = True
		self.starting_node = None

		self.update_graph_attr()

		if img_data is not None:
			self.bg_img, tl_lat_lon, br_lat_lon = img_data
			self.scale_bg_img(tl_lat_lon, br_lat_lon)
			self.bg_img = self.img2pygame(self.bg_img)
			self.bg_img = pygame.transform.smoothscale(self.bg_img, self.window_size)
			self.orig_bg_img = self.bg_img.copy()

		self.create_done()
		self.done = False

	@classmethod
	def get_x_bounds(cls, G, coord='x'):
		# Return the minimum and maximum x coordinates over all nodes and edges of a graph G

		index = 0 if coord == 'x' else 1

		all_xcoords = [G.nodes[id_][coord] for id_ in G.nodes] + \
					  [xy[index] for e in G.edges for xy in G.edges[e]['geometry'].coords]

		return (min(all_xcoords), max(all_xcoords))

	@classmethod
	def get_y_bounds(cls, G):
		# Return the minimum and maximum y coordinates over all nodes and edges of a graph G

		return cls.get_x_bounds(G, coord='y')
		
	def update_graph_attr(self):
		# Update lists and dictionaries specific to the graph

		self.x_bounds = self.get_x_bounds(self.G)
		self.y_bounds = self.get_y_bounds(self.G)
		self.node_ids = list(self.G.nodes)
		self.nodes = self.G.nodes
		self.edge_ids = list(self.G.edges)
		self.edges = self.G.edges
		self.node_colors = {id_:self.main_node_color for id_ in self.node_ids}
		if self.starting_node:
			if self.starting_node in self.node_ids:
				self.node_colors[self.starting_node] = self.start_node_color
			else:
				self.starting_node = None
		self.node_window_coords = self.get_node_window_coords()
		self.edge_window_coords = self.get_edge_window_coords()

		self.osmids = [self.G.edges[i]['osmid'] for i in self.G.edges]

		lat_func = lambda id_:self.nodes[id_]['lat']
		lon_func = lambda id_:self.nodes[id_]['lon']
		self.node_with_min_lat = self.nodes[min(self.node_ids, key=lat_func)]
		self.node_with_max_lat = self.nodes[max(self.node_ids, key=lat_func)]
		self.node_with_min_lon = self.nodes[min(self.node_ids, key=lon_func)]
		self.node_with_max_lon = self.nodes[max(self.node_ids, key=lon_func)]

		if self.bg_img:
			self.scale_bg_img_for_zoom()

	def create_done(self):
		# Create the done surface and rect in the bottom right corner of the screen

		done_font = pygame.font.SysFont('arial', 18, bold=True)
		self.done_surf = done_font.render('DONE', True, self.mode_color)
		self.done_rect = self.done_surf.get_rect()
		self.done_loc = (self.window_size[0] - self.done_rect.width - 2, 2)
		self.done_rect.move_ip(self.done_loc)

	def scale_bg_img(self, img_tl_gps, img_br_gps):
		# Scale the background image

		img_width, img_height = self.bg_img.size

		tl_y = self.coord_transform(self.node_with_max_lat['lat'], 
									img_tl_gps[0], 
									img_br_gps[0], 
									0, 
									img_height)
		tl_x = self.coord_transform(self.node_with_min_lon['lon'], 
									img_tl_gps[1], 
									img_br_gps[1], 
									0, 
									img_width)
		br_y = self.coord_transform(self.node_with_min_lat['lat'], 
									img_tl_gps[0], 
									img_br_gps[0], 
									0, 
									img_height)
		br_x = self.coord_transform(self.node_with_max_lon['lon'], 
									img_tl_gps[1], 
									img_br_gps[1], 
									0, 
									img_width)

		x_buffer = self.coord_transform(self.buffer, 0, self.window_size[0], 0, img_width)
		y_buffer = self.coord_transform(self.buffer, 0, self.window_size[1], 0, img_height)

		self.bg_img = self.bg_img.crop((tl_x-x_buffer, tl_y-y_buffer, br_x+x_buffer, br_y+y_buffer))

	def scale_bg_img_for_zoom(self):
		# Adjust the background image for zoom

		if not self.zoomed:
			self.bg_img = self.orig_bg_img
			return

		width = self.zoom_tlbr[1][0] - self.zoom_tlbr[0][0]
		height = self.zoom_tlbr[1][1] - self.zoom_tlbr[0][1]

		zoom_rect = pygame.Rect(*self.zoom_tlbr[0], width, height)

		orig_copy = self.orig_bg_img.copy()
		self.bg_img = orig_copy.subsurface(zoom_rect)

		self.bg_img = pygame.transform.smoothscale(self.bg_img, self.window_size)

	@staticmethod
	def img2pygame(img):

		mode = img.mode
		size = img.size
		data = img.tobytes()

		return pygame.image.fromstring(data, size, mode)

	def map_to_window(self, coords, coord=None, reverse=False, ws=None, x_bounds=None, y_bounds=None, edge_buffer=None):
		# Map a graph coordinate to window coordinates or vice versa

		if not ws: ws = self.window_size
		if not x_bounds: x_bounds = self.orig_x_bounds
		if not y_bounds: y_bounds = self.orig_y_bounds
		if not edge_buffer: edge_buffer = self.buffer

		if coord is None:
			x, y = coords
			if reverse:
				newx = self.coord_transform(x, edge_buffer, ws[0]-edge_buffer, *x_bounds)
				newy = self.coord_transform(ws[1] - y, edge_buffer, ws[1]-edge_buffer, *y_bounds)
				return (newx, newy)
			newx = self.coord_transform(x, *x_bounds, edge_buffer, ws[0]-edge_buffer)
			newy = self.coord_transform(y, *y_bounds, edge_buffer, ws[1]-edge_buffer)
			return (newx, ws[1] - newy)
		elif coord == 'x':
			if reverse:
				return self.coord_transform(coords, edge_buffer, ws[0]-edge_buffer, *x_bounds)
			return self.coord_transform(coords, *x_bounds, edge_buffer, ws[0]-edge_buffer)
		elif coord == 'y':
			if reverse:
				return self.coord_transform(ws[1] - coords, edge_buffer, ws[1]-edge_buffer, *y_bounds)
			return ws[1]-self.coord_transform(coords, *y_bounds, edge_buffer, ws[1]-edge_buffer)

	def retrieve_lat_lon(self, graph_coords):
		# Retreive the latitude and longitude or a position graph_coords in graph coordinates

		lat = self.coord_transform(graph_coords[1],
								   self.node_with_min_lat['y'],
								   self.node_with_max_lat['y'],
								   self.node_with_min_lat['lat'],
								   self.node_with_max_lat['lat'])
		lon = self.coord_transform(graph_coords[0],
								   self.node_with_min_lon['x'],
								   self.node_with_max_lon['x'],
								   self.node_with_min_lon['lon'],
								   self.node_with_max_lon['lon'])
		return (lat, lon)

	@staticmethod
	def coord_transform(x, a1, a2, b1, b2):
		# Interpolate x from (a1, a2) coords to (b1, b2) coords

		return (x*(b2-b1) - b2*a1 + b1*a2)/(a2-a1)

	def get_node_window_coords(self):
		# Get window coordinates of all nodes in the graph
		# Returns a dictionary with the node id as the key and window coords as the value

		node_window_coords = {}
		for id_ in self.node_ids:
			node = self.nodes[id_]
			node_coords = self.map_to_window((node['x'], node['y']))
			node_window_coords[id_] = self.adjust_coord_for_zoom(node_coords)
		return node_window_coords

	def get_edge_window_coords(self):
		# Get window coordinates of all edge points in the graph
		# Returns a dictionary with the edge id as the key and window coords list as the value

		edge_window_coords = {}
		for id_ in self.edge_ids:
			edge_coords = []
			for coords in self.edges[id_]['geometry'].coords:
				coords_before_zoom = self.map_to_window(coords)
				edge_coords.append(self.adjust_coord_for_zoom(coords_before_zoom))
			edge_window_coords[id_] = edge_coords
		return edge_window_coords

	def draw(self):
		# Draw the graph

		if self.bg_img and self.bg_on:
			self.surface.blit(self.bg_img, (0,0))
		else:
			self.surface.fill(self.bg_color)
		self.draw_edges()
		self.draw_nodes()
		self.draw_mode()
		self.draw_done()
		if self.zoom_box_on:
			self.draw_zoom_box()
		if self.message_on:
			self.draw_message()
		if self.input_on:
			self.draw_input()

	def draw_input(self):
		# Draw the input message

		ws = self.window_size
		ms = self.input_message.get_size()
		dest = (ws[0]//2-ms[0]//2, ws[1]//2-ms[1]//2)
		self.surface.blit(self.input_message, dest)

	def draw_message(self):
		# Draw the message surface object saved in self.message

		if not self.message:
			print('MessageError: No message to display.')
			return

		ws = self.window_size
		ms = self.message.get_size()
		dest = (ws[0]//2-ms[0]//2, ws[1]//2-ms[1]//2)
		self.surface.blit(self.message, dest)

	def draw_mode(self):
		# Draw the current mode in the corner of the window

		self.surface.blit(self.mode_surfaces[self.mode], (2, 2))

	def draw_done(self):
		# Draw the done button

		self.surface.blit(self.done_surf, self.done_loc)

	def draw_edges(self):
		# Draw the edges of the graph

		for coord_list in self.edge_window_coords.values():
			pygame.draw.lines(self.surface, self.line_color, False, coord_list)

	def draw_nodes(self):
		# Draw the nodes of the graph

		for id_ in self.node_window_coords:
			pygame.draw.circle(self.surface, 
							   self.node_colors[id_], 
							   self.node_window_coords[id_],
							   self.node_radius)

	def draw_zoom_box(self):
		# Draw a box while the mouse is pressed

		mouse_pos = pygame.mouse.get_pos()
		dims = np.subtract(mouse_pos, self.zoom_box_click_coords)

		if dims[0] > 0 and dims[1] > 0:
			tl = self.zoom_box_click_coords
		elif dims[0] < 0 and dims[1] < 0:
			tl = mouse_pos
		elif dims[0] < 0 and dims[1] > 0:
			tl = (mouse_pos[0], self.zoom_box_click_coords[1])
		else:
			tl = (self.zoom_box_click_coords[0], mouse_pos[1])

		zoom_box = pygame.Rect(tl, np.abs(dims))
		pygame.draw.rect(self.surface, pygame.Color(140, 140, 140), zoom_box, width=2)

	def edit_graph(self):
		# View the graph

		self.draw()
		while not self.close_clicked:
			self.handle_event()
			if self.done:
				break
			self.draw()
			pygame.display.update()

	def handle_event_for_input(self):
		# Handle user events while getting input

		for event in pygame.event.get():
			if event.type == QUIT:
				self.close_clicked = True

			elif event.type == KEYDOWN:
				key = event.key
				name = pygame.key.name(key)

				if key == K_ESCAPE:
					self.close_clicked = True

				elif key == K_BACKSPACE:
					self.input_str = self.input_str[:-1]

				elif key == K_RETURN:
					self.input_done = True

				elif name.isalnum() or name == '.':
					self.input_str += pygame.key.name(key)

	def handle_event(self):
		# Handle each user event by changing the simulation state appropriately.

		for event in pygame.event.get():
			if event.type == QUIT:
				self.close_clicked = True

			elif self.message_on and event.type == MOUSEBUTTONUP:
				self.message_on = False
				self.message = None

			elif event.type == KEYDOWN:
				key = event.key

				if self.message_on:
					if key == K_ESCAPE:
						self.close_clicked = True
					self.message_on = False
					self.message = None

				elif key == K_ESCAPE:
					self.close_clicked = True

				# Change the mode
				elif key in (K_z, K_d, K_n, K_e, K_s, K_c, K_u, K_h, K_b):
					self.change_mode(key)

				# Remove highlighted nodes (or edge) when delete is pressed in DELETE mode
				elif key == K_BACKSPACE and self.mode == DELETE:
					if event.mod and KMOD_SHIFT:
						self.delete_edge()
					else:
						self.delete_nodes()

			elif event.type == MOUSEBUTTONDOWN and not self.message_on:
				self.handle_mousebuttondown(event)

			elif event.type == MOUSEBUTTONUP:
				self.handle_mousebuttonup(event)

	def handle_mousebuttondown(self, event):
		# Handle mouse clicks on the window

		if self.done_rect.collidepoint(event.pos):
			self.done = True

		elif self.mode == DELETE:
			collided_node_id = self.check_collide_with_node(event.pos)
			if collided_node_id:
				if collided_node_id in self.nodes_to_delete:
					if collided_node_id == self.starting_node:
						self.node_colors[collided_node_id] = self.start_node_color
					else:
						self.node_colors[collided_node_id] = self.main_node_color
					self.nodes_to_delete.remove(collided_node_id)
				else:
					self.node_colors[collided_node_id] = self.node_delete_color
					self.nodes_to_delete.append(collided_node_id)

		elif self.mode == ZOOM:
			if np.array_equal(self.zoom_matrix, ZOOM_IDENTITY):
				self.zoom_box_on = True
				self.zoom_box_click_coords = event.pos

		elif self.mode == ADD_NODES:
			self.add_node(event.pos)

		elif self.mode == ADD_EDGES:
			collided_node_id = self.check_collide_with_node(event.pos)
			if collided_node_id:
				self.add_edge(collided_node_id)

		elif self.mode == START_NODE:
			collided_node_id = self.check_collide_with_node(event.pos)
			if collided_node_id:
				if self.starting_node:
					self.node_colors[self.starting_node] = self.main_node_color
				if self.starting_node == collided_node_id:
					self.starting_node = None
				else:
					self.starting_node = collided_node_id
					self.node_colors[self.starting_node] = self.start_node_color

	def handle_mousebuttonup(self, event):
		# Handle mouse releases on the window

		if self.mode == ZOOM and np.array_equal(self.zoom_matrix, ZOOM_IDENTITY) \
			and self.zoom_box_click_coords is not None:
			p1, p2 = self.zoom_box_click_coords, event.pos
			self.reset_zoom_params()

			if p1 == p2 or p1[0] == p2[0] or p1[1] == p2[1]:
				return

			if p1[0] < p2[0] and p1[1] < p2[1]:
				tl = p1
				br = p2
			elif p1[0] > p2[0] and p1[1] > p2[1]:
				tl = p2
				br = p1
			elif p1[0] < p2[0] and p1[1] > p2[1]:
				tl = (p1[0], p2[1])
				br = (p2[0], p1[1])
			else:
				tl = (p2[0], p1[1])
				br = (p1[0], p2[1])
			self.zoom_tlbr = (tl, br)  # Top left and bottom right postions of the zoom box
			self.set_zoom_matrix()

		elif self.mode == ZOOM and self.zoomed:
			self.set_zoom_matrix(reset=True)

	def change_mode(self, key):
		# Change the mode

		new_mode = self.mode_dict[key]

		# If we exit DELETE mode, return the highlighted nodes to normal
		if self.mode == DELETE and new_mode != DELETE:
			self.node_colors = {id_:self.main_node_color for id_ in self.node_ids}
			if self.starting_node and self.starting_node in self.node_ids:
				self.node_colors[self.starting_node] = self.start_node_color
			self.nodes_to_delete = []

		# If we exit ZOOM mode, reset the zoom parameters
		# This does not reset the zoom of the graph in the window
		if self.mode == ZOOM and new_mode != ZOOM:
			self.reset_zoom_params()

		# If we exit ADD_EDGES mode, reset nodes to original color
		if self.mode == ADD_EDGES and new_mode != ADD_EDGES:
			self.node_colors = {id_:self.main_node_color for id_ in self.node_ids}
			if self.starting_node and self.starting_node in self.node_ids:
				self.node_colors[self.starting_node] = self.start_node_color
			self.edge_adder_node_id = None

		# Reset the zoom if the z key is pressed while zoomed in
		if new_mode == ZOOM and self.zoomed:
			self.set_zoom_matrix(reset=True)

		# Consolidate intersections in the graph
		# This can only be done once
		if new_mode == CONSOLIDATE_GRAPH and not self.consolidated:
			self.consolidate_intersections()

		# Undo the last move
		if new_mode == UNDO:
			self.undo()

		# Display the help message
		if new_mode == DISPLAY_HELP:
			self.message_on = True
			self.message = self.create_message_surface(self.help_message)

		# Turn the background image on or off
		if new_mode == TOGGLE_BACKGROUND:
			self.bg_on = False if self.bg_on else True

		# Change the mode
		if new_mode in (ZOOM, DELETE, ADD_NODES, ADD_EDGES, START_NODE):
			self.mode = new_mode

	def undo(self):
		# Undo the last graph-affecting change

		if self.graph_list:
			if self.graph_list[-1][1] == 'c':
				self.consolidated = False
			self.G = self.graph_list[-1][0]
			del self.graph_list[-1]
			self.update_graph_attr()

	def consolidate_intersections(self):
		# Run the osmnx function osmnx.simplification.consolidate_intersections()

		tol = self.get_input('Enter consolidation tolerance:')
		try:
			tol = int(float(tol))
		except ValueError:
			self.message_on = True
			self.message = self.create_message_surface('Unable to decode tolerance input.')
			return
		self.graph_list.append((self.G.copy(), 'c'))
		self.G = ox.simplification.consolidate_intersections(self.G, 
															 tolerance=tol,
															 rebuild_graph=True,
															 dead_ends=True)
		self.add_missing_attr()
		self.update_graph_attr()
		self.consolidated = True  # Can only do this once

	def add_missing_attr(self):
		# Add missing attributes after we consolidate the graph

		for id_ in self.G.nodes:
			node = self.G.nodes[id_]
			try:
				node['street_count']
			except KeyError:
				node['street_count'] = len(self.G.edges(id_))
			try:
				node['lat']
			except KeyError:
				lat_lon = self.retrieve_lat_lon((node['x'], node['y']))
				node['lat'], node['lon'] = lat_lon

	def set_zoom_matrix(self, reset=False):
		# Set the zoom

		if reset:
			self.zoom_matrix = ZOOM_IDENTITY
			self.reverse_zoom_matrix = ZOOM_IDENTITY
			self.zoomed = False
			self.update_graph_attr()
			return

		zoomed_coords = np.array([[0, self.window_size[0], self.window_size[0]],
								  [0, self.window_size[1], 0]])
		zoomed_coords_for_reverse = np.append(zoomed_coords, [[1,1,1]], axis=0)

		init_coords = np.array([[self.zoom_tlbr[0][0], self.zoom_tlbr[1][0], self.zoom_tlbr[1][0]], 
								[self.zoom_tlbr[0][1], self.zoom_tlbr[1][1], self.zoom_tlbr[0][1]],
								[1,1,1]])
		init_coords_for_reverse = init_coords[:2]

		try:
			inverse = inv(init_coords)
			inverse_for_reverse = inv(zoomed_coords_for_reverse)
		except LinAlgError:
			print('ZoomError: Singular zoom matrix. Resetting zoom level.')
			self.set_zoom_matrix(reset=True)
			return
		self.zoom_matrix = np.matmul(zoomed_coords, inverse)
		self.reverse_zoom_matrix = np.matmul(init_coords_for_reverse, inverse_for_reverse)
		self.zoomed = True
		self.update_graph_attr()

	def adjust_coord_for_zoom(self, coord, reverse=False):
		# Adjust coordinates for the zoom

		if reverse:
			return np.matmul(self.reverse_zoom_matrix, np.transpose(np.array([*coord, 1])))
		return np.matmul(self.zoom_matrix, np.transpose(np.array([*coord, 1])))

	def reset_zoom_params(self):
		# Reset the zooming parameters

		self.zoom_box_on = False
		self.zoom_box_click_coords = None
					
	def check_collide_with_node(self, pos):
		# Check if a point collides with a node on the graph
		
		for node_id in self.node_window_coords:
			if norm(np.subtract(self.node_window_coords[node_id], pos)) < self.node_radius:
				return node_id
		return None

	def delete_nodes(self):
		# Delete highlighted nodes in DELETE mode

		if len(self.nodes_to_delete) == 0:
			return
		self.graph_list.append((self.G.copy(), 'd'))
		for id_ in self.nodes_to_delete:
			self.G.remove_node(id_)
		self.nodes_to_delete = []
		self.update_graph_attr()

	def delete_edge(self):
		# Delete highlighted nodes in DELETE mode

		if len(self.nodes_to_delete) != 2:
			return
		orig_G = self.G.copy()
		try:
			self.G.remove_edge(*self.nodes_to_delete)
		except NetworkXError:
			return

		self.graph_list.append((orig_G, 'd'))
		self.nodes_to_delete = []
		self.update_graph_attr()

	def add_node(self, pos):
		# Add a node a window coordinate pos

		unzoomed_window_coord = self.adjust_coord_for_zoom(pos, reverse=True)
		graph_coord = self.map_to_window(unzoomed_window_coord, reverse=True)
		lat_lon = self.retrieve_lat_lon(graph_coord)

		id_ = randint(1000000000, 9999999999)
		while id_ in self.node_ids:
			id_ = randint(1000000000, 9999999999)

		self.graph_list.append((self.G.copy(), 'n'))
		self.G.add_nodes_from([(id_, {'y':graph_coord[1], 
									  'x':graph_coord[0], 
									  'street_count':0,
									  'lon':lat_lon[1],
									  'lat':lat_lon[0]})])
		self.update_graph_attr()

	def add_edge(self, node_id):
		# Add an edge between nodes

		if not self.edge_adder_node_id:
			self.edge_adder_node_id = node_id
			self.node_colors[node_id] = self.add_edge_node_color
			return

		start_node = self.nodes[self.edge_adder_node_id]
		end_node = self.nodes[node_id]

		osmid = randint(100000000, 999999999)
		while osmid in self.osmids:
			osmid = randint(100000000, 999999999)
		highway = 'new_path'  # or 'unclassified'
		oneway = False
		length = self.get_input('Enter edge length in meters:')
		try:
			length = float(length)
		except ValueError:
			self.message_on = True
			self.message = self.create_message_surface('Unable to decode length input.')
			self.edge_adder_node_id = None
			self.update_graph_attr()
			return
		geometry = LineString([(start_node['x'], start_node['y']), (end_node['x'], end_node['y'])])

		self.graph_list.append((self.G.copy(), 'e'))
		self.G.add_edges_from([(self.edge_adder_node_id, node_id, {'osmid':osmid,
															'highway':highway,
															'oneway':oneway,
															'length':length,
															'geometry':geometry})])
		for id_ in (self.edge_adder_node_id, node_id):
			self.G.nodes[id_]['street_count'] += 1

		self.edge_adder_node_id = None
		self.update_graph_attr()

	def get_input(self, text):
		# Get user input

		self.input_str = ''
		self.message = self.create_message_surface([text, '_'])
		self.input_message = self.create_input_surface()
		self.input_on = True
		while not self.input_done and not self.close_clicked:
			self.draw()
			self.handle_event_for_input()
			pygame.display.update()
			self.input_message = self.create_input_surface()
		self.input_done = False
		self.input_on = False
		return self.input_str

	def create_message_surface(self, message):
		# Create a surface to display message text

		if type(message) == list:
			text_surfaces = [self.font.render(line, True, self.text_color, self.message_bg_color)
							 for line in message]
		else:
			text_surfaces = [self.font.render(message, True, self.text_color, self.message_bg_color)]

		text_heights = [surf.get_height() for surf in text_surfaces]
		text_widths = [surf.get_width() for surf in text_surfaces]

		height = len(text_surfaces)*text_heights[0]

		message_box_size = (max(text_widths)+2*self.text_buffer, height+2*self.text_buffer)
		message_surf = pygame.Surface(message_box_size)
		message_surf.fill(self.message_bg_color)

		for i, surf in enumerate(text_surfaces):
			dest = (message_box_size[0]//2-text_widths[i]//2, i*text_heights[0]+self.text_buffer)
			message_surf.blit(surf, dest)

		return message_surf

	def create_input_surface(self):
		# Create a surface to display to input text

		self.font.set_underline(True)
		input_text_surf = self.font.render(self.input_str, True, self.text_color)
		self.font.set_underline(False)
		input_size = input_text_surf.get_size()
		dest = (self.message.get_width()//2-input_size[0]//2, self.text_buffer+input_size[1])
		input_surf = self.message.copy()
		input_surf.blit(input_text_surf, dest)


		return input_surf

	def get_graph(self):
		# Return the graph in its current form

		return self.G

	def get_finished(self):
		# Return True if the user clicked Done

		return self.done

	def get_start_node(self):
		# Get the starting node.  Returns None if no starting node is set

		return self.starting_node

