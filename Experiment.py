#!/usr/bin/env python

# Code used for testing and quantifying network inference
# Daniel Klein, 5/15/2012

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt

class RandomSubnetworks:
    def __init__(self, network, train_size, test_size = 0, method = 'node'):
        self.network = network
        self.train_size = train_size
        self.test_size = test_size
        self.method = method

        if self.method == 'node':
            self.inds = np.arange(self.network.N)
        elif self.method == 'edge':
            edges = self.network.network.nonzero()
            edges_i, edges_j = edges[0], edges[1]
            self.edges_i = edges_i
            self.edges_j = edges_j
            self.num_edges = len(edges_i)
        elif self.method in ['link', 'link_f'] :
            edges = self.network.network.nonzero()
            neighbors = { n: set() for n in range(self.network.N) }
            for i, j in zip(edges[0], edges[1]):
                neighbors[i].add(j)
                if self.method == 'link':
                    neighbors[j].add(i)
            self.neighbors = { n: list(neighbors[n]) for n in neighbors }

    def sample(self):
        if self.method == 'node':
            np.random.shuffle(self.inds)
            sub_train = self.inds[0:self.train_size]
        elif self.method == 'edge':
            added = set()
            while len(added) < self.train_size:
                e = np.random.randint(self.num_edges)
                edge_i = self.edges_i[e]
                edge_j = self.edges_j[e]
                if len(added) == self.train_size - 1:
                    # Edge case, since otherwise would bias to tail node
                    if np.random.random() < 0.5:
                        added.add(edge_i)
                    else:
                        added.add(edge_j)
                added.add(edge_i)
                added.add(edge_j)
            sub_train = np.array(list(added))
        elif self.method in ['link', 'link_f']:
            added = set()
            loc = np.random.randint(self.network.N)
            while len(added) < self.train_size:
                added.add(loc)
                if added.issuperset(self.neighbors[loc]):
                    loc = np.random.randint(self.network.N)
                    continue
                new_i = np.random.randint(len(self.neighbors[loc]))
                loc = self.neighbors[loc][new_i]
            sub_train = np.array(list(added))

        if self.test_size == 0:
            return self.network.subnetwork(sub_train)
        else:
            sub_full = self.inds[0:(self.train_size + self.test_size)]
            return (self.network.subnetwork(sub_train),
                    self.network.subnetwork(sub_full))

# A major purpose of this package is studying the consistency. Hence,
# a natural experimental setup will be repeating an inference
# procedure on a range of network sizes. This class is designed to
# expedite such experiments.

class Results:
    def __init__(self, sub_sizes, num_reps, title = None):
        self.sub_sizes = sub_sizes
        self.N_subs = len(sub_sizes)
        self.N_reps = num_reps
        self.title = title
        self.results = {}

        self.sub_size_to_ind = {}
        for i, sub_size in enumerate(sub_sizes):
            self.sub_size_to_ind[sub_size] = i

    # Return a copy of the result structure, with new allocated storage
    def copy(self):
        dup = Results(self.sub_sizes, self.N_reps, title = self.title)

        for result_name in self.results:
            result = self.results[result_name]
            f, f_type = result['f'], result['f_type']

            dup.new(result_name, f_type, f)

        return dup

    # Values expected for "f_type": 'a' (adjacency)
    #                               'n' (network)
    #                               'm' (models),
    #                               'nm' (network and models)
    def new(self, name, f_type, f):
        assert(f_type in ['a', 'n', 'm', 'nm'])
        self.results[name] = { 'f': f, 'f_type': f_type,
                               'data': np.empty((self.N_subs, self.N_reps)) }

        return name

    def record(self, sub_size, rep, network,
               data_model = None, fit_model = None):
        for result in self.results:
            f = self.results[result]['f']
            f_type = self.results[result]['f_type']
            if f_type == 'a':
                val = f(network.adjacency_matrix())
            elif f_type == 'n':
                val = f(network)
            elif f_type == 'm':
                val = f(data_model, fit_model)
            elif f_type == 'nm':
                val = f(network, data_model, fit_model)

            data = self.results[result]['data']
            data[self.sub_size_to_ind[sub_size], rep] = val

    # To be called after all results have been recorded...
    def estimate_mse(self, name, true, estimate):
        self.results[name] = {'data': np.empty((self.N_subs,1))}

        t = self.results[true]['data']
        e = self.results[estimate]['data']

        for n in range(self.N_subs):
            self.results[name]['data'][n,0] = np.mean((t[n]-e[n])**2)

    def summary(self):
        for field in self.results:
            data = self.results[field]['data']
            average_data = np.mean(data, 1)
            print '%s: %s' % (field, str(average_data))
        
    def plot(self, requests = None):
        if requests == None:
            requests = self.results.keys()
        num_plots = len(requests)

        f, axarr = plt.subplots(num_plots, sharex = True)
        if num_plots == 1:
            axarr = [axarr]
            
        if self.title:
            axarr[0].set_title(self.title)

        for i, request in enumerate(requests):
            ax = axarr[i]

            if type(request) != str:
                names, options = request
            else:
                names, options = request, {}

            if type(names) == str:
                names = [names, names]
            plot_name, names = names[0], names[1:]
            for name in names:
                result = self.results[name]
                data = result['data']
                if 'plot_mean' in options and options['plot_mean']:
                    ax.plot(self.sub_sizes, data.mean(1))
                else:
                    for rep in range(data.shape[1]):
                        ax.scatter(self.sub_sizes, data[:,rep])

            if 'baseline' in options:
                ax.plot(self.sub_sizes,
                        np.repeat(options['baseline'], len(self.sub_sizes)),
                        'k:')

            ax.set_ylabel(plot_name)
            if 'ymin' in options and 'ymax' in options:
                ax.set_ylim(options['ymin'], options['ymax'])
            elif 'ymin' in options:
                ax.set_ylim(ymin = options['ymin'])
            elif 'ymax' in options:
                ax.set_ylim(ymax = options['ymax'])

            if 'loglog' in options:
                ax.set_xscale('log')
                ax.set_yscale('log')

        axarr[-1].set_xlabel('N_sub')
        f.subplots_adjust(hspace = 0)
        plt.setp([a.get_xticklabels() for a in axarr[:-1]], visible = False)

        plt.show()

# Add a suite of standard network statistics to a Results instance
def add_network_stats(results):
    results.new('Average degree', 'a', lambda a: 1.0 * np.sum(a) / a.shape[0])
    results.new('Max out-degree', 'a', lambda a: np.max(a.sum(1)))
    results.new('Min out-degree', 'a', lambda a: np.min(a.sum(1)))
    results.new('Max in-degree', 'a', lambda a: np.max(a.sum(0)))
    results.new('Min in-degree', 'a', lambda a: np.min(a.sum(0)))
    results.new('Self-loop density', 'a', lambda a: np.mean(np.diagonal(a)))

# Find the minimum of a disagreement function from true class labels
# over distinct relabelings of the estimated class labels
#
# Eventually should add option to use Hungarian algorithm, although
# this is probably unnecessary for, say, K <= 6.
def minimum_disagreement(z_true, z_est, f = None, normalized = True):
    from itertools import permutations

    assert(len(z_true) == len(z_est))

    if not f:
        N = len(z_true)
        def f(x, y):
            return np.sum(x != y) / N

    true_classes = list(set(z_true))
    est_classes = list(set(z_est))
    if len(est_classes) < len(true_classes):
        est_classes += [-1] * (len(true_classes) - len(est_classes))
    best = np.inf
    for est_permutation in permutations(est_classes, len(true_classes)):
        z_est_perm = np.tile(-1, len(z_est))
        for s, t in zip(est_permutation, true_classes):
            z_est_perm[z_est == s] = t
        best = min(best, f(z_true, z_est_perm))

    if normalized:
        best_constant = np.inf
        for z in set(z_true):
            z_constant = np.repeat(z, len(z_true))
            best_constant = min(best_constant, f(z_true, z_constant))
        best /= best_constant
        
    return best

# Differences of infinities make sense in this context...
def robust_mse(x, y):
    diff = x - y
    equal_cells = (x == y)
    diff[equal_cells] = 0
    return np.mean(diff ** 2)
    
def rel_mse(est_1, est_2, truth):
    return robust_mse(est_1, truth) / robust_mse(est_2, truth)
