# Chinese Postman Route Creater
An interactive program to solve the Chinese Postman Problem over a network of roads or paths.

## Overview
This code solves the [Chinese Postman Problem](https://en.wikipedia.org/wiki/Route_inspection_problem) over a network of roads or paths loaded from the geographic database open street map.  This program contains a simple editor to refine the road network before computing the optimal route over all roads.  A program is also included to view the route once it has been created.

## Installation
    $ git clone https://github.com/adamreidsmith/Chinese-Postman-Route-Creater
    $ cd Chinese-Postman-Route-Creater
    $ sudo pip3 install -r requirements.txt

## Usage
The [`cpp_interactive.py`](/cpp_interactive.py) contains the main program.  The road network is specified by providing latitude-longitude coordinates of the upper left and lower right corners of a box bounding the desred area.  The road/path network within the box is then loaded from the open street map data.  Enter the following code into the command line to run the program,

    $ python3 cpp_interactive.py [upper-left-lat] [upper-left-long] [lower-right-lat] [lower-right-long]

replacing `[upper-left-lat]`, etc. with the corresponding coordinate.  Additionally, the following options may be specified:
    
`--network_type [walk, bike, drive, drive_service, all, or all_private]`  Specify paths roads are loaded from osm. <br>
`--map_type [satellite, elevation, terrain, or streets]`  Set a map for the background. <br>
`--resolution [integer between 1 and 20]`  Set the resolution of the background map. <br>
`--csv [string]`  The name of the output csv file.
`--verbose`  Print information as the program runs.
`--simplify`  Simplify the graph to remove interstitial nodes (experimental).
