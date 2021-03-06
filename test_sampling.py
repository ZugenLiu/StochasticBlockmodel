#!/usr/bin/env python

# Looking into different sampling schemes to give "sparse scaling"
# (which, paradoxically, is better for small subnetwork inference).
# Daniel Klein, 5/1/2013

import numpy as np

from Network import network_from_edges
from Experiment import RandomSubnetworks, Results, add_array_stats

# Parameters
params = { 'N': 400,
           'D': 5,
           'num_reps': 5,
           'sub_sizes': np.arange(10, 110, 10, dtype = np.int),
           'sampling_methods': ['random_node', 'random_edge',
                                'link_trace', 'link_trace_f'],
           'plot_network': True }


# Set random seed for reproducible output
np.random.seed(137)

# Initialize full network
blocks = params['N'] / params['D']
edges = []
for block in range(blocks):
    for i in range(params['D']):
        v_1 = 'n_%d' % (block * params['D'] + i)
        for j in range(params['D']):
            v_2 = 'n_%d' % (((block + 1) * params['D'] + j) % params['N'])
            edges.append((v_1, v_2))
net = network_from_edges(edges)

# Set up recording of results from experiment
results_by_method = { }
for method_name in params['sampling_methods']:
    results = Results(params['sub_sizes'], params['sub_sizes'],
                      params['num_reps'], title = method_name)
    add_array_stats(results, network = True)
    results.new('# Active', 'n',
                lambda n: np.isfinite(n.offset.matrix()).sum())
    results_by_method[method_name] = results

for sub_size in params['sub_sizes']:
    size = (sub_size, sub_size)
    print 'subnetwork size = %s' % str(size)

    generators = \
      { 'random_node': RandomSubnetworks(net, size, method = 'node'),
        'random_edge': RandomSubnetworks(net, size, method = 'edge'),
        'link_trace': RandomSubnetworks(net, size, method = 'link'),
        'link_trace_f': RandomSubnetworks(net, size, method = 'link_f') }
    for generator in generators:
        if not generator in params['sampling_methods']: continue
        print generator
        for rep in range(params['num_reps']):
            subnet = generators[generator].sample(as_network = True)

            subnet.offset_extremes()

            results_by_method[generator].record(size, rep, subnet)

# Output results
print
for method_name in params['sampling_methods']:
    print method_name

    results = results_by_method[method_name]
    results.summary()
    if params['plot_network']:
        results.plot([('Density', {'ymin': 0, 'plot_mean': True}),
                      (['Out-degree', 'Max row-sum', 'Min row-sum'],
                       {'ymin': 0, 'plot_mean': True}),
                      (['In-degree', 'Max col-sum', 'Min col-sum'],
                       {'ymin': 0, 'plot_mean': True}),
                      ('Self-loop density', {'ymin': 0, 'plot_mean': True}),
                      ('# Active', {'ymin': 0 })])

    print

# Report parameters for the run
print 'Parameters:'
for field in params:
    print '%s: %s' % (field, str(params[field]))
