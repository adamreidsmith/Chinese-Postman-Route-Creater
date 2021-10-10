import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pygame.locals import *
import networkx as nx
import pickle

from graphedit import GraphEdit as ge

class RouteViewer:

	def __init__(self, graph, route):

		self.G = graph
		self.route = route
		self.window_size = self.get_window_size()
		self.surface = self.create_window(self.window_size, 'Route Viewer')

		self.orig_x_bounds = ge.get_x_bounds(self.G)
		self.orig_y_bounds = ge.get_y_bounds(self.G)
		self.buffer = 10

		self.nodes = self.G.nodes
		self.node_ids = list(self.nodes)
		self.edges = self.G.edges
		self.edge_ids = list(self.edges)
		self.node_window_coords = self.get_node_window_coords()
		self.edge_window_coords = self.get_edge_window_coords()

		self.close_clicked = False

		self.bg_color = pygame.Color('black')
		self.node_main_color = pygame.Color('white')
		self.edge_color = pygame.Color('white')
		self.selected_color = pygame.Color('red')
		self.selected_node_color = pygame.Color('green')
		self.node_radius = 2

		self.selected_index = 0

	def get_window_size(self, max_width=1440, max_height=848):
		# Get the window size which matches the proportions of the graph G

		x_bounds = ge.get_x_bounds(self.G)
		y_bounds = ge.get_y_bounds(self.G)
		width = int( max_height*(x_bounds[1] - x_bounds[0])/(y_bounds[1] - y_bounds[0]) )
		if width <= max_width:
			return (width, max_height)
		height = int( max_width*(y_bounds[1] - y_bounds[0])/(x_bounds[1] - x_bounds[0]) )
		return (max_width, height)

	def create_window(self, size, title=''):
		# Open a window on the display and return its surface.

		pygame.init()
		surface = pygame.display.set_mode(size)
		pygame.display.set_caption(title)
		return surface

	def get_node_window_coords(self):
		# Get window coordinates of all nodes in the graph
		# Returns a dictionary with the node id as the key and window coords as the value

		node_window_coords = {}
		for id_ in self.node_ids:
			node = self.nodes[id_]
			node_window_coords[id_] = ge.map_to_window(ge, 
													   (node['x'], node['y']), 
													   ws=self.window_size,
													   x_bounds=self.orig_x_bounds,
													   y_bounds=self.orig_y_bounds,
													   edge_buffer=self.buffer)
		return node_window_coords

	def get_edge_window_coords(self):
		# Get window coordinates of all edge points in the graph
		# Returns a dictionary with the edge id as the key and window coords list as the value

		edge_window_coords = {}
		for id_ in self.edge_ids:
			edge_coords = []
			for coords in self.edges[id_]['geometry'].coords:
				edge_coords.append(ge.map_to_window(ge, 
													coords,
													ws=self.window_size,
													x_bounds=self.orig_x_bounds,
													y_bounds=self.orig_y_bounds,
													edge_buffer=self.buffer))
			edge_window_coords[id_] = edge_coords
		return edge_window_coords

	def view_route(self):

		self.draw()
		while not self.close_clicked:
			self.handle_event()
			self.draw()
			pygame.display.update()
		pygame.quit()

	def draw(self):
		# Draw the window objects

		self.surface.fill(self.bg_color)
		self.draw_edges()
		self.draw_nodes()
		self.draw_selected()

	def draw_edges(self):
		# Draw the edges of the graph on the window

		for coord_list in self.edge_window_coords.values():
			pygame.draw.lines(self.surface, self.edge_color, False, coord_list)

	def draw_nodes(self):
		# Draw the graph nodes on the window

		for id_ in self.node_window_coords:
			if id_ == self.route[0]:
				pygame.draw.circle(self.surface, 
								   self.selected_node_color, 
								   self.node_window_coords[id_],
								   self.node_radius)
			else:
				pygame.draw.circle(self.surface, 
								   self.node_main_color, 
								   self.node_window_coords[id_],
								   self.node_radius)

	def draw_selected(self):
		# Highlight the selected node

		selected_id = self.route[self.selected_index]

		pygame.draw.circle(self.surface,
						   self.selected_color,
						   self.node_window_coords[selected_id],
						   self.node_radius)

	def handle_event(self):
		# Handle user events

		for event in pygame.event.get():
			if event.type == QUIT:
				self.close_clicked = True

			elif event.type == KEYDOWN:
				if event.key == K_ESCAPE:
					self.close_clicked = True
				elif event.key in (K_UP, K_RIGHT):
					self.increment_index()
				elif event.key in (K_DOWN, K_LEFT):
					self.increment_index(-1)

	def increment_index(self, amount=1):
		# Increment the selected node index

		self.selected_index += amount
		self.selected_index %= len(self.route)

def main():

	with open('graph.pkl', 'rb') as graph_file:
		graph = pickle.load(graph_file)
	with open('route.pkl', 'rb') as route_file:
		route = pickle.load(route_file)

	route_viewer = RouteViewer(graph, route)

	route_viewer.view_route()

if __name__ == '__main__':
	main()




