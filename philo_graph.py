import csv
import pprint
import networkx as nx
import matplotlib.pyplot as plt
from pyvis import network as pvnet
import ipycytoscape
import ipywidgets as widgets
import copy
import os
import re 
#import pygraphviz
import networkx.drawing.nx_agraph as nx_agraph
import sys

def load_data(in_file, in_file_nodes_done, G, nodes_done):
    with open(in_file_nodes_done) as nodes_done_file:
        all_lines = nodes_done_file.readlines()
        nodes_done[:] = [line.rstrip() for line in all_lines]
    with open(in_file) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        i = 0
        for row in reader:
            if (i == 0):
                header = row
            else:
                if(row[0] != ''):
                    G.add_nodes_from([(row[0], {'lab': row[1], 'dist': -1, 'cycle': set(), 'color': ''})])
                if(row[2] != ''):
                    G.add_nodes_from([(row[2], {'lab': row[3], 'dist': -1, 'cycle': set(), 'color': ''})])
                if (row[0] != '' and row[2] != ''):
                  G.add_edge(row[0], row[2])
            i = i+1


def find_cycles(g):
    print("\tFind simple cycles")
    cycles = nx.simple_cycles(g)
    cycles1 = list()
    cycles2 = list()
    print("\tCreate lists of cycles")
    for c in cycles:
        cycles1.append(set(c))
        cycles2.append(set(c))
    
    intersect_exist = True
    while (intersect_exist):
        newcycles = list()
        intersect_exist = False
        for c1 in cycles1:
            newcycle = copy.deepcopy(c1)
            for c2 in cycles2:
                if (not c1 == c2):
                    intersect = not c1.isdisjoint(c2)
                    if (intersect == True):
                        newcycle = newcycle | c2
                        intersect_exist = True
            newcycles.append(set(newcycle))
        cycles1 = copy.deepcopy(newcycles)
        cycles2 = copy.deepcopy(newcycles)

    for i in range(len(newcycles)):
        for j in range(len(newcycles)):
            equals = newcycles[i] == newcycles[j]
    newcycles = list(set(item) for item in set(frozenset(item) for item in newcycles))
    return(newcycles)

def remove_cycles(g, cycles):
    i = 0
    for c in cycles:
        g.add_nodes_from([(f'cycleNode{i}', {'lab': f'CN{i}', 'dist': -1, 'cycle': copy.deepcopy(c)})])
        for n in c:
            for succ in g.successors(n):
                if ((succ not in c) and (succ != f"cycleNode{i}")):
                  g.add_edge(f'cycleNode{i}', succ)
            for pred in g.predecessors(n):
                g.add_edge(pred, f'cycleNode{i}')
            g.remove_node(n)
        i = i+1

def set_colors(g, nodes_done):
    for n in g.nodes:
        color = '#95C0F9'
        all_succ_done = True
        for n_succ in g.successors(n):
            if (n_succ not in nodes_done):
                all_succ_done = False
        if (n in nodes_done):
            color = '#808080'
        elif (len(list(g.successors(n))) == 0 or all_succ_done):
            color = '#C0F995'
        g.nodes[n]['color'] = color

def create_subdirs(out_dir):
    try:
        os.makedirs(out_dir+"/pyvis/with_cycles/")
    except OSError as error:
        pass
    try:
        os.makedirs(out_dir+"/pyvis/without_cycles/")
    except OSError as error:
        pass
    try:
        os.makedirs(out_dir+"/gexf/with_cycles/")
    except OSError as error:
        pass
    try:
        os.makedirs(out_dir+"/gexf/without_cycles/")
    except OSError as error:
        pass

def get_source_node(g, source):
    for n in g.nodes:
        if (n == source):
            return(n)
        elif (source in g.nodes[n]['cycle']):
            return(n)

def dist_from_impl(g, source, dist, pred):
    if(source in pred):
        assert(False)
    if (dist+1 > g.nodes[source]['dist']):
        g.nodes[source]['dist'] = dist+1
    else:
        return
    for n in g.successors(source):
        list_arg = copy.deepcopy(pred)
        list_arg.append(source)
        dist_from_impl(g, n, g.nodes[source]['dist'], list_arg) 

def dist_from(g, source):
    source = get_source_node(g, source)
    dist_from_impl(g, source, -1, list())

def set_dists(g_source, g_target):
    for n in g_source.nodes:
        if (len(g_source.nodes[n]['cycle']) == 0):
            g_target.nodes[n]['dist'] = g_source.nodes[n]['dist']
        else:
            for n2 in g_source.nodes[n]['cycle']:
                g_target.nodes[n2]['dist'] = g_source.nodes[n]['dist']

def prune(g):
    for n in copy.deepcopy(g.nodes):
        if (n in g.nodes and g.nodes[n]['dist'] == -1):
            g.remove_node(n)

def count_status(g):
    ready = 0
    not_ready = 0
    done = 0
    for n in g.nodes:
        if (g.nodes[n]['color'] == '#808080'):
            done = done + 1
        elif (g.nodes[n]['color'] == '#C0F995'):
            ready = ready + 1
        else:
            not_ready = not_ready + 1
    return {'ready': ready, 'not_ready': not_ready, 'done': done}

def save_pyvis(g, g_orig, out_dir, subdir, filename, root_label):
    status = count_status(g)
    #title=f"{root_label}: {len(g.nodes)}[{len(g.nodes)/len(g_orig.nodes)*100:.2f}%] nodes (ready: {status['ready']}[{status['ready']/len(g.nodes)*100:.2f}%], not ready: {status['not_ready']}[{status['not_ready']/len(g.nodes)*100:.2f}%], done: {status['done']}[{status['done']/len(g.nodes)*100:.2f}%])"
    title=f"{len(g.nodes)}[{len(g.nodes)/len(g_orig.nodes)*100:.2f}%] nodes (ready: {status['ready']}[{status['ready']/len(g.nodes)*100:.2f}%], not ready: {status['not_ready']}[{status['not_ready']/len(g.nodes)*100:.2f}%], done: {status['done']}[{status['done']/len(g.nodes)*100:.2f}%])"
    gp=pvnet.Network(height='800px', width='100%',heading=title,bgcolor='black',font_color="white",directed=True, layout=True)
    #gp.show_buttons()
    #gp.show_buttons(filter_=['physics', 'layout', 'interaction'])
    gp.set_options("""
    const options = {
    "nodes": {
        "color": {
          "highlight": "#F9CE95"
      },
    "fixed": {
      "y": false 
    }
    },
    "edges": {
      "color": {
          "highlight": "#F9CE95"
      }
    },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "sortMethod": "directed",
          "shakeTowards": "leaves",
          "direction": "LR",
          "levelSeparation": 210,
          "nodeSpacing": 100,
          "parentCentralization": true
        }
      },
      "physics": {
        "enabled": false,
        "hierarchicalRepulsion": {
          "centralGravity": 0,
          "avoidOverlap": 1,
          "nodeDistance": 100
        },
        "minVelocity": 0.75,
        "maxVelocity": 50,
        "solver": "hierarchicalRepulsion"
      }
    }
    """)
    for n2 in g.nodes:
        g.nodes[n2]['cycle'] = list(g.nodes[n2]['cycle'])
        gp.add_node(n2,label=g.nodes[n2]['lab']+"|"+f"{g.nodes[n2]['dist']}", title=g.nodes[n2]['lab']+"|"+f"{g.nodes[n2]['dist']}"+"|"+f"{g.nodes[n2]['cycle']}", level=g.nodes[n2]['dist'], color=g.nodes[n2]['color'])
        #gp.add_node(n2,label=" ", title=g.nodes[n2]['lab']+"|"+f"{g.nodes[n2]['dist']}"+"|"+f"{g.nodes[n2]['cycle']}", level=g.nodes[n2]['dist'], color=g.nodes[n2]['color'])
    for e2 in g.edges:
        gp.add_edge(e2[0], e2[1])
    gp.save_graph(out_dir+"/pyvis/"+subdir+"/"+f"{filename}.html")


def draw_each(G, G_no_cycles, out_dir):
    n_nodes = len(G.nodes)
    i = 0
    print(f"{n_nodes} nodes")
    max_g1 = ""
    max_g1_val = 0
    max_g2 = ""
    max_g2_val = 0
    for n in G.nodes:
        i = i + 1
        print("Node", n, f'{i}/{n_nodes} ({i/n_nodes*100})')
        G1 = copy.deepcopy(G)
        G2 = copy.deepcopy(G_no_cycles)
        print("\tCompute dists")
        dist_from(G2, n)
        print("\tSet dists")
        set_dists(G2, G1)
        
        print("\tPrune 1")
        prune(G1)
        print("\tPrune 2")
        prune(G2)
    
        root_label = G.nodes[n]['lab']
        if (n == ''):
            filename = '_'
        else:
            filename = re.sub(r"^.*/", '', n)
    
        #for n2 in G1.nodes:
        #    G1.nodes[n2]['cycle'] = list(G1.nodes[n2]['cycle'])

        #for n2 in G2.nodes:
        #    G2.nodes[n2]['cycle'] = list(G1.nodes[n2]['cycle'])
    
        print("\tDraw graph 1")
        save_pyvis(G1, G, out_dir, "with_cycles", filename, root_label)
        print("\tDraw graph 2")
        save_pyvis(G2, G_no_cycles, out_dir, "without_cycles", filename, root_label)

        new_max_g1 = False
        new_max_g2 = False
        if (len(G1.nodes) > max_g1_val):
            max_g1 = n
            max_g1_val = len(G1.nodes)
            new_max_g1 = True
            print("\tG1 max")
        if (len(G2.nodes) > max_g2_val):
            max_g2 = n
            max_g2_val = len(G2.nodes)
            new_max_g2 = True
            print("\tG2 max")
        assert(new_max_g1 == new_max_g2)
            

        #nx.write_gexf(G1, out_dir+"/gexf/with_cycles/"+f"{filename}.gexf")
        #nx.write_gexf(G2, out_dir+"/gexf/without_cycles/"+f"{filename}.gexf")
    print(f"Graph with cycles: {len(G.nodes)}")
    print(f"Max graph with cycles: {max_g1}, {max_g1_val}[{max_g1_val/len(G.nodes):.2f}%]")
    print(f"Graph with cycles: {len(G_no_cycles.nodes)}")
    print(f"Max graph without cycles: {max_g2}, {max_g2_val}[{max_g2_val/len(G_no_cycles.nodes):.2f}%]")



in_file = 'philosophers.csv'
in_file_nodes_done = 'philosophers_done.txt'
out_dir, extension = os.path.splitext(in_file)
G = nx.DiGraph()
nodes_done = list()
print("Load")
#load_data(G, nodes_done)
load_data(in_file, in_file_nodes_done, G, nodes_done)
G_no_cycles = copy.deepcopy(G)
print("Find cycles")
cycles = find_cycles(G_no_cycles)
print(f"\tFound {len(cycles)} cycles")
print(cycles)
print("Remove cycles")
remove_cycles(G_no_cycles, cycles)
set_colors(G, nodes_done)
set_colors(G_no_cycles, nodes_done)
assert_cycles = nx.simple_cycles(G_no_cycles)
create_subdirs(out_dir)
draw_each(G, G_no_cycles, out_dir)
print("Cycles:")
for c in cycles:
    print(c)

