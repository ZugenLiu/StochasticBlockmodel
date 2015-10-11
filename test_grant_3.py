#!/usr/bin/env python

# Some tests written in support of Matt's grant-writing.
# Daniel Klein, 10/26/2012

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

import os
os.environ['PATH'] += ':/usr/texbin'
from matplotlib import rc
rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
rc('text', usetex = True)

from Network import Network
from Models import StationaryLogistic, NonstationaryLogistic
from Models import FixedMargins, alpha_norm
from BinaryMatrix import approximate_conditional_nll
from BinaryMatrix import approximate_from_margins_weights
from BinaryMatrix import log_partition_is

# Parameters
N = 25
G = 20
alpha_sd = 2.0
theta_true = { 'x_1': 2.0, 'x_2': -1.0 }
target_degree = 2

# Setup network
net = Network(N)
alpha_norm(net, alpha_sd)

# Setup data model and network covariates
data_model = NonstationaryLogistic()
covariates = []
for name in theta_true:
    covariates.append(name)

    data_model.beta[name] = theta_true[name]

    def f_x(i_1, i_2):
        return np.random.normal(0, 1.0)
    net.new_edge_covariate(name).from_binary_function_ind(f_x)

# Instantiate network according to data model
data_model.match_kappa(net, ('row_sum', target_degree))
net.generate(data_model)
#net.show_heatmap('alpha_out')
#net.show_heatmap('alpha_in')

# Display network
plt.figure(figsize = (17, 8.5))
plt.subplot(241)
plt.title('Network')
graph = nx.DiGraph()
A = net.adjacency_matrix()
for i in range(N):
    graph.add_node(i)
for i in range(N):
    for j in range(N):
        if A[i,j]:
            graph.add_edge(i,j)
pos = nx.graphviz_layout(graph, prog = 'neato')
nx.draw(graph, pos, node_size = 60, with_labels = False)

def grid_fit(fit_model, f_nll, plot = True):
    # Evaluate likelihoods on a grid
    theta_star_1 = data_model.beta[covariates[0]]
    theta_star_2 = data_model.beta[covariates[1]]
    x = np.linspace(theta_star_1 - 2.0, theta_star_1 + 2.0, G)
    y = np.linspace(theta_star_2 - 2.0, theta_star_2 + 2.0, G)
    z = np.empty((G,G))
    for i, theta_1 in enumerate(x):
        for j, theta_2 in enumerate(y):
            fit_model.beta[covariates[0]] = theta_1
            fit_model.beta[covariates[1]] = theta_2
            print 'theta_1 = %.2f, theta_2 = %.2f' % (theta_1, theta_2)
            z[i,j] = f_nll(net, fit_model)

    nll_min = np.min(z)
    theta_opt_min = np.where(z == nll_min)
    theta_opt_1 = x[theta_opt_min[0][0]]
    theta_opt_2 = y[theta_opt_min[1][0]]

    if plot:
        # contour expects x, y, z generated by meshgrid...
        CS = plt.contour(x, y, np.transpose(z), colors = 'k')
        plt.plot(theta_star_1, theta_star_2, 'b*', markersize = 12)
        plt.plot(theta_opt_1, theta_opt_2, 'ro', markersize = 12)
        # plt.clabel(CS, inline = 1, fontsize = 10, fmt = '%1.1f')
        plt.xlabel(r'$\theta_2$', fontsize = 14)
        plt.ylabel(r'$\theta_1$', fontsize = 14)

    return theta_opt_1, theta_opt_2

# Grid search for stationary and non-stationary fits
plt.subplot(242)
plt.title('Stationary')
grid_fit(StationaryLogistic(), lambda n, m: m.nll(net))
plt.subplot(243)
plt.title('Nonstationary')
grid_fit(NonstationaryLogistic(), lambda n, m: m.nll(net))

# Grid search for approximate conditional fit
plt.subplot(244)
plt.title('Approximate Conditional')
def f_nll(net, fit_model):
    P = fit_model.edge_probabilities(net)
    w = P / (1.0 - P)
    A = np.array(net.adjacency_matrix())
    return approximate_conditional_nll(A, w)
grid_fit(StationaryLogistic(), f_nll)

# Grid search for importance-sampled conditional fit
for i, T in enumerate([1, 3, 10, 30]):
    plt.subplot(2, 4, (5+i))
    plt.title('IS Conditional (T = %d)' % T)

    def f_nll(net, fit_model):
        P = fit_model.edge_probabilities(net)
        w = P / (1.0 - P)
        A = np.array(net.adjacency_matrix())
        r, c = A.sum(1), A.sum(0)

        z = approximate_from_margins_weights(r, c, w, T,
                                             sort_by_wopt_var = False)
        logkappa, logcvsq = log_partition_is(z, cvsq = True)
        print 'est. cv^2 = %.2f (T = %d)' % (np.exp(logcvsq), T)
        return (logkappa - np.sum(np.log(w[A])))
    grid_fit(StationaryLogistic(), f_nll)

#for c in covariates:
#    plt.figure()
#    plt.scatter(net.edge_covariates[c].matrix(), net.adjacency_matrix())
#    plt.show()

#plt.savefig('../grant/figs/simulated_data_no_wopt_sort_10.eps')
plt.show()
