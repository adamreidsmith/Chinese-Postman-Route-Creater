import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import osmnx as ox
from PIL import Image
import csv
import pickle
import argparse

from graphedit import GraphEdit
from mapboxloader import MapboxLoader
import cppsolver
from routeviewer import RouteViewer


# Parse arguments from user
parser = argparse.ArgumentParser()
parser.add_argument('coordinates', type=float, nargs=4, help='The latitude-longitude condinates of the upper left and lower right corners of the bounding box of the path network.')
parser.add_argument('--network_type', type=str, default='drive', help='What type of street network to get. One of ‘walk’, ‘bike’, ‘drive’, ‘drive_service’, ‘all’, or ‘all_private’.')
parser.add_argument('--map_type', type=str, default=None, help='What type of background image to display. One of ‘satellite’, ‘elevation’, ‘terrain’, or ‘streets’. If not specified, no background will be set.')
parser.add_argument('--resolution', type=int, default=15, help='Resolution of the background image if applicable. An integer in [1, 20]. The higher the resolution, the longer the background image will take to generate.')
parser.add_argument('--csv', type=str, default='path.csv', help='The name of the output csv file.')
parser.add_argument('--verbose', action='store_true', help='Output information as the program runs.')
parser.add_argument('--simplify', action='store_true', help='Simplify the graph to remove interstitial nodes. This feature is experimental and may produce undesirable results.')
args = parser.parse_args()

# User Defined Functions

class ChinesePostmanInteractive:

	def __init__(self, tl, br, network_type='drive', map_type=None, resolution=15, verbose=True, simplify=False, out_file='path.csv'):

		self.verbose = verbose
		self.tl = tl
		self.br = br
		self.res = resolution
		self.network_type = network_type
		self.simplify = simplify
		self.map_type = map_type
		self.csv = out_file

		if self.verbose: print('Fetching graph data...')
		self.G = self.get_graph()

		if self.map_type:
			self.bg_img, self.img_tl_lat_lon, self.img_br_lat_lon = self.get_bg_image(map_type)

	def get_window_size(self, max_width=1440, max_height=848):
		# Get the window size which matches the proportions of the graph G

		x_bounds = GraphEdit.get_x_bounds(self.G)
		y_bounds = GraphEdit.get_y_bounds(self.G)
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

	def get_bg_image(self, img_type='satellite'):

		Loader = MapboxLoader(self.tl, self.br, zoom=self.res, verbose=self.verbose)
		img_tl_lat_lon = Loader.num2deg(*Loader.tl_tile, self.res)
		img_br_lat_lon = Loader.num2deg(*Loader.br_tile, self.res)

		img_id = str(sum((sum(self.tl), sum(self.br))) + self.res)

		img_path = './composite_images/' + img_type + img_id + '.png'
		if os.path.exists(img_path):
			if self.verbose: print('Loading background image...')
			return (Image.open(img_path), img_tl_lat_lon, img_br_lat_lon)
		
		if self.verbose: print('Generating background image...')
		Loader.generate_data(img_type)
		img = Loader.compose_image(img_type, remove_temp=True, save=True)
		return (img, img_tl_lat_lon, img_br_lat_lon)

	def get_graph(self):

		g = ox.graph_from_bbox(self.tl[0],
							   self.br[0],
							   self.br[1],
							   self.tl[1],
							   network_type=self.network_type)
		g = ox.project_graph(g)
		return g.to_undirected()

	def simplify_graph(self):
		# Run osmnx's simplify_graph method to remove interstitial nodes

		self.G.graph['simplified'] = False

		# We must make every value in each edge dict hashable
		for edge_id in self.G.edges:
			edge = self.G.edges[edge_id]
			keys = list(edge.keys())
			for key in keys:
				if type(edge[key]) == list:
					edge[key] = edge[key][0]
				if key == 'geometry':
					del edge[key]

		self.G = ox.simplification.simplify_graph(self.G, strict=True, remove_rings=False)

	def save_path(self, path):
		# Save the final Eulerian circuit to a csv file

		if self.csv[-4:] != '.csv':
			self.csv += '.csv'

		if self.verbose: print('Writing path to %s...' % self.csv)

		with open(self.csv, 'w', newline='') as csvfile:
			writer = csv.writer(csvfile, delimiter=',')

			writer.writerow(['START NODE', 
							 'END NODE', 
							 'NAME', 
							 'START LAT', 
							 'START LON', 
							 'END LAT', 
							 'END LON', 
							 'LENGTH'])

			for edge in path:
				n1, n2, data = edge

				n1_data = self.G.nodes[n1]
				n2_data = self.G.nodes[n2]

				try:
					name = data[0]['name'][0] if type(data[0]['name']) == list else data[0]['name']
				except KeyError:
					name = 'unknown'

				length = round(data[0]['length'], 3) if 'length' in data[0] else 0

				writer.writerow([n1, 
								 n2,
								 name,
								 n1_data['lat'],
								 n1_data['lon'],
								 n2_data['lat'],
								 n2_data['lon'],
								 length])

	def print_stats(self, path):
		# Print stats about the Eulerian circuit

		path_length = round(sum([e[2][0]['length'] for e in path if 'length' in e[2][0]]), 3)

		all_roads_length = round(sum([self.G.edges[e]['length'] for e in self.G.edges if 'length' in self.G.edges[e]]), 3)

		print()
		print('Total length of route:           %.3fm' % path_length)
		print('Combined length of all paths:    %.3fm' % all_roads_length)
		print('Length of paths traversed twice: %.3fm' % (path_length - all_roads_length))
		print()

	def main(self):
		# The main routine

		if self.verbose: print('Loading graph editor...')
		window_size = self.get_window_size()
		surface = self.create_window(window_size, title='Chinese Postman Interactive')
		if self.map_type:
			graph_edit = GraphEdit(self.G, surface, window_size, (self.bg_img, 
																  self.img_tl_lat_lon, 
																  self.img_br_lat_lon))
		else:
			graph_edit = GraphEdit(self.G, surface, window_size)

		graph_edit.edit_graph()
		if not graph_edit.get_finished():
			if self.verbose: print('Computation aborted.')
			return
		self.G = graph_edit.get_graph()
		starting_node = graph_edit.get_start_node()
		pygame.quit()

		if self.simplify:
			if self.verbose: print('Simplifying graph...')
			self.simplify_graph()

		if self.verbose: print('Solving Chinese Postman Problem on graph...')
		eulerian_circuit = cppsolver.solve_cpp(self.G, starting_node)

		self.save_path(eulerian_circuit)

		if self.verbose: self.print_stats(eulerian_circuit)

		route = [eulerian_circuit[0][0]] + [e[1] for e in eulerian_circuit]

		if self.verbose: print('Writing pickle files...')
		with open('graph.pkl', 'wb') as graph_file:
			pickle.dump(self.G, graph_file)
		with open('route.pkl', 'wb') as route_file:
			pickle.dump(route, route_file)

if __name__ == '__main__':
	tl = (args.coordinates[0], args.coordinates[1])
	br = (args.coordinates[2], args.coordinates[3])
	cpi = ChinesePostmanInteractive(tl, br, 
									network_type=args.network_type, 
									map_type=args.map_type, 
									resolution=args.resolution,
									verbose=args.verbose,
									simplify=args.simplify,
									out_file=args.csv)
	cpi.main()