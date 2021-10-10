#import mercantile
from PIL import Image
import math
import requests
import shutil
import os

API_KEY = #YOUR MAPBOX API KEY HERE

class MapboxLoader:

	def __init__(self, top_left, bottom_right, zoom=15, verbose=False, api_key=None):

		self.tl = top_left  # Top left lat-lon coords
		self.br = bottom_right  # Bottom right lat-lon coords
		self.z = zoom  # Sets the resolution (max at 15)
		self.verbose = verbose

		self.tl_tile = self.deg2num(*self.tl, self.z)
		self.br_tile = self.deg2num(*self.br, self.z)
		self.tl_tile = (self.tl_tile[0] - 1, self.tl_tile[1] - 1)
		self.br_tile = (self.br_tile[0] + 1, self.br_tile[1] + 1)
		self.x_tile_range = (self.tl_tile[0], self.br_tile[0])
		self.y_tile_range = (self.tl_tile[1], self.br_tile[1])

		self.api_key = api_key if api_key else API_KEY

		self.img_id = str(sum((sum(top_left), sum(bottom_right))) + zoom)

	def generate_data(self, img_type='satellite'):

		tileset_ids = {'satellite':'mapbox.satellite',
					   'elevation':'mapbox.terrain-rgb',
					   'terrain':'mapbox.mapbox-terrain-v2',
					   'streets':'mapbox.mapbox-streets-v8'}

		dirname = './' + img_type + '/'

		os.makedirs(dirname, exist_ok=True)

		n_imgs = (self.br_tile[0]-self.tl_tile[0]+1) * (self.br_tile[1]-self.tl_tile[1]+1)
		if self.verbose: print('    Retrieving %i images...' % n_imgs)

		# Loop over the tile ranges
		for i,x in enumerate(range(self.x_tile_range[0], self.x_tile_range[1]+1)):
			for j,y in enumerate(range(self.y_tile_range[0], self.y_tile_range[1]+1)):

				#Call the URL to get the terrain image back
				r = requests.get('https://api.mapbox.com/v4/' + tileset_ids[img_type] + \
								 '/' + str(self.z) + '/' + str(x) + '/' + str(y) + \
							 	 '@2x.pngraw?access_token=' + self.api_key, stream=True)

				# Write the raw content to an image
				with open(dirname + str(i) + '.' + str(j) + '.png', 'wb') as f:
					r.raw.decode_content = True
					shutil.copyfileobj(r.raw, f) 

	def compose_image(self, dirname, remove_temp=False, save=False):

		assert dirname in os.listdir(), 'No image directory. Run generate_data method first.'

		if self.verbose: print('    Composing images...')
		img = self._compose_from_set(dirname, save)

		if remove_temp:
			try:
				shutil.rmtree(dirname)
			except FileNotFoundError:
				pass

		return img

	def _compose_from_set(self, dirname, save):

		assert dirname in ('satellite', 'elevation', 'terrain', 'streets',
						   'satellite/', 'elevation/', 'terrain/', 'streets/',
						   './satellite', './elevation', './terrain', './streets',
						   './satellite/', './elevation/', './terrain/', './streets/'), 'Run generate_data ' +\
								'method to generate image directory.'

		if dirname[-1] != '/':
			dirname = dirname + '/'
		if dirname[:2] != './':
			dirname = './' + dirname

		# Make a list of the image names
		image_files = [dirname + f for f in os.listdir(dirname)]

		# Calculate the number of image tiles in each direction
		edge_length_x = self.x_tile_range[1] - self.x_tile_range[0]
		edge_length_y = self.y_tile_range[1] - self.y_tile_range[0]
		edge_length_x = max(1, edge_length_x)
		edge_length_y = max(1, edge_length_y)

		# Find the final composed image dimensions  
		width, height = Image.open(image_files[0]).size
		total_width = width * edge_length_x
		total_height = height * edge_length_y

		# Create a new blank image we will fill in
		composite = Image.new('RGB', (total_width, total_height))

		# Loop over the x and y ranges
		y_offset = 0
		for i in range(edge_length_x):
			x_offset = 0
			for j in range(edge_length_y):
				# Open up the image file and paste it into the composed image at the given offset position
				tmp_img = Image.open(dirname + str(i) + '.' + str(j) + '.png')
				composite.paste(tmp_img, (y_offset, x_offset))
				x_offset += width # Update the width
			y_offset += height # Update the height

		if save:
			os.makedirs('./composite_images', exist_ok=True)
			img_name = dirname[2:-1]
			composite.save('./composite_images/' + img_name + self.img_id + '.png')

		return composite

	@staticmethod
	def deg2num(lat_deg, lon_deg, zoom):
		lat_rad = math.radians(lat_deg)
		n = 2.0 ** zoom
		xtile = int((lon_deg + 180.0) / 360.0 * n)
		ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
		return (xtile, ytile)

	@staticmethod
	def num2deg(xtile, ytile, zoom):
		n = 2.0 ** zoom
		lon_deg = xtile / n * 360.0 - 180.0
		lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
		lat_deg = math.degrees(lat_rad)
		return (lat_deg, lon_deg)



