import osmnx as ox
import networkx as nx
import pandas as pd
from networkx.algorithms.matching import max_weight_matching
from networkx.algorithms.components import is_connected
from itertools import combinations

def solve_cpp(G, starting_node=None, verbose=True):
	''' 
	Find the most efficient path over all edges in the graph G.  That is, solve the 
	Chinese Postman Problem on G.
	'''

	# Graph must be undirected and connected
	if nx.is_directed(G):
		if verbose: print('Graph is directed. Converting to undirected.')
		G = G.to_undirected()
	assert is_connected(G), 'Graph is not connected.'

	# Get a list of all nodes of odd degree
	odd_deg_nodes = [n for n, d in G.degree if d % 2 == 1]
	
	# Get a list of all pairs of odd degree nodes
	odd_node_pairs = list(combinations(odd_deg_nodes, 2))

	# Get the length of the shortest path between each pair of nodes
	if verbose: print('    Getting shortest path length between all odd node pairs...')
	odd_node_pairs_shortest_paths = _get_shortest_paths_lengths(G, odd_node_pairs, 'length')

	# Create a completely connected graph using the odd nodes and the shortest path lengths between them
	g_odd_complete = _create_complete_graph(odd_node_pairs_shortest_paths)

	# Compute minimum weight matching. Takes O(n ** 3) time
	if verbose: print('    Performing minimum weight matching...')
	odd_matching_dupes = max_weight_matching(g_odd_complete, True)

	# Remove duplicate minimum weight pairs
	odd_matching = list(pd.unique([tuple(sorted([n1, n2])) for n1, n2 in odd_matching_dupes]))

	# Add the min weight matching edges to the original graph
	G_aug = _add_augmenting_path_to_graph(G, odd_matching)

	if verbose: print('    Creating Eulerian circuit...')
	return _create_eulerian_circuit(G_aug, G, starting_node=starting_node)

	#circuit_nodes = [eulerian_circuit[0][0]] + [n[1] for n in eulerian_circuit]

def _get_shortest_paths_lengths(G, pairs, edge_weight_name):
	'''
	Compute shortest distance between each pair of nodes in a graph.  Return a 
	dictionary keyed on node pairs (tuples).
	'''

	path_lengths = {}
	for pair in pairs:
		path_lengths[pair] = nx.dijkstra_path_length(G, pair[0], pair[1], weight=edge_weight_name)
	return path_lengths

def _create_complete_graph(pair_weights, flip_weights=True):
	'''
	Create a completely connected graph using a list of vertex pairs and the 
	shortest path distances between them.
	Parameters: 
		pair_weights: list[tuple] from the output of get_shortest_paths_distances
		flip_weights: Boolean. Should we negate the edge attribute in pair_weights?
	'''
	
	g = nx.Graph()
	for k, v in pair_weights.items():
		wt_i = -v if flip_weights else v

		g.add_edge(k[0], k[1], **{'length': v, 'weight': wt_i})  
	return g

def _add_augmenting_path_to_graph(G, min_weight_pairs):
	'''
	Add the min weight matching edges to the original graph
	Parameters:
		G: NetworkX graph 
		min_weight_pairs: list[tuples] of node pairs from min weight matching
	Returns:
		augmented NetworkX graph
	'''

	# We need to make the augmented graph a MultiGraph so we can add parallel edges
	G_aug = nx.MultiGraph(G.copy())
	for pair in min_weight_pairs:
		G_aug.add_edge(pair[0], 
					   pair[1], 
					   **{'length': nx.dijkstra_path_length(G, pair[0], pair[1]), 'trail': 'augmented'})

	# Make sure each edge has a trail attribute
	for edge_id in G_aug.edges:
		if 'trail' not in G_aug.edges[edge_id]:
			G_aug.edges[edge_id]['trail'] = 'original'

	return G_aug

def _create_eulerian_circuit(graph_augmented, graph_original, starting_node=None):
	'''
	Create the Eulerian path using only edges from the original graph.
	'''

	euler_circuit = []
	naive_circuit = list(nx.eulerian_circuit(graph_augmented, source=starting_node))

	for edge in naive_circuit:
		edge_data = graph_augmented.get_edge_data(edge[0], edge[1])

		if edge_data[0]['trail'] != 'augmented':
			# If 'edge' exists in original graph, grab the edge attributes and add to eulerian circuit.
			edge_att = graph_original[edge[0]][edge[1]]
			euler_circuit.append((edge[0], edge[1], dict(edge_att))) 
		else: 
			aug_path = nx.shortest_path(graph_original, edge[0], edge[1], weight='length')
			aug_path_pairs = list(zip(aug_path[:-1], aug_path[1:]))

			# If 'edge' does not exist in original graph, find the shortest path between its nodes and 
			# add the edge attributes for each link in the shortest path.
			for edge_aug in aug_path_pairs:
				edge_aug_att = graph_original[edge_aug[0]][edge_aug[1]]
				euler_circuit.append((edge_aug[0], edge_aug[1], dict(edge_aug_att)))

	return euler_circuit


if __name__ == '__main__':
	tl = (51.,-118.20094232802526)
	br = (50.983281785654624,-118.1811147141947)
	g = ox.graph_from_bbox(tl[0],
						   br[0],
						   br[1],
						   tl[1],
						   network_type='drive')
	g = ox.project_graph(g)
	g = g.to_undirected()
	solve_cpp(g)





