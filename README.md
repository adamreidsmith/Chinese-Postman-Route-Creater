# Chinese Postman Route Creater
An interactive program to solve the Chinese Postman Problem over a network of roads or paths.

## Overview
This code solves the [Chinese Postman Problem](https://en.wikipedia.org/wiki/Route_inspection_problem) (CPP) over a network of roads or paths loaded from the geographic database [OpenStreetMap](https://www.openstreetmap.org/).  The CPP is to find the shortest closed path that visits every edge in a connedted, undiredted graph (in this case, a road or trail map).  This program contains a simple editor to refine the road network before computing the optimal, and a program to view the route once it has been created.  This project was originally developed to map a minimal length [route](https://www.strava.com) over all trails at the Revelstoke Nordic Ski Club.  Later, this was used to map a [road cycling route](https://www.strava.com) over all roads in Revelstoke, BC.

## Motivation
This project was originally developed to map a minimal length route over all trails at the Revelstoke Nordic Ski Club.  Later, this was used to map a road cycling route over all roads in Revelstoke, BC.  The ski route is available on Strava [here](/https://www.strava.com), and the road cycling route is available [here](/https://www.strava.com).

## Installation
    $ git clone https://github.com/adamreidsmith/Chinese-Postman-Route-Creater
    $ cd Chinese-Postman-Route-Creater
    $ sudo pip3 install -r requirements.txt

## Usage
The file [`cpp_interactive.py`](/cpp_interactive.py) contains the main program.  The road network is specified by providing latitude-longitude coordinates of the upper left and lower right corners of a box bounding the desred area.  The road/path network within the box is then loaded from the open street map data.  Enter the following code into the command line to run the program,

    $ python3 cpp_interactive.py [upper-left-lat] [upper-left-long] [lower-right-lat] [lower-right-long]

replacing `[upper-left-lat]`, etc. with the corresponding coordinate.  Additionally, the following options may be specified:
    
`--network_type [walk, bike, drive, drive_service, all, or all_private]`  Specify which paths are loaded from osm. <br>
`--map_type [satellite, elevation, terrain, or streets]`  Set a map for the background. <br>
`--resolution [integer between 1 and 20]`  Set the resolution of the background map. <br>
`--csv [string]`  The name of the output csv file. <br>
`--verbose`  Print information as the program runs. <br>
`--simplify`  Simplify the graph to remove interstitial nodes (experimental). <br>

This will compute the minimal length route over the specified paths and output a `csv` file containing a list of nodes with coordinates corresponding to the generated route.  Additionally, the graph and route will be saved in `pickle` files.  Running [`routeviewer.py`](/routeviewer.py) in the same directory allows you to view the route and scroll through the route's nodes using the arrow keys.

## Technology Used
* Python 3
* Mapbox API
* OSMnx
* NetworkX
* Pygame

## LICENSE
[MIT](/LICENSE)
