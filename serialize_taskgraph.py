import json
import networkx as nx

TASKGRAPH_NAME = 'firefox-translations-training'
LAYOUT_NAME = 'multipartite-layout'

def load_taskgraph():
    f = open(f"./{TASKGRAPH_NAME}-taskgraph.json")
    data = f.read()
    f.close()
    taskgraph = json.loads(data)
    return taskgraph


def build_digraph(taskgraph):
    digraph = nx.DiGraph(name=TASKGRAPH_NAME)
    for tasknode in taskgraph:
        digraph.add_node(tasknode, **taskgraph[tasknode])
        if taskgraph[tasknode]["dependencies"]:
            for dependency in taskgraph[tasknode]["dependencies"]:
                digraph.add_edge(
                    taskgraph[tasknode]["dependencies"][dependency], tasknode
                )
    print("graph_name:", digraph.name)
    print("graph_order:", f"{digraph.order():,}")
    print("graph_size:", f"{digraph.size():,}")
    return digraph


def layout_digraph(digraph):
    if LAYOUT_NAME == 'kamada-kawai-layout':
        return nx.kamada_kawai_layout(digraph)
    for layer, nodes in enumerate(nx.topological_generations(digraph)):
        # `multipartite_layout` expects the layer as a node attribute, so add the
        # numeric layer value as a node attribute
        for node in nodes:
            digraph.nodes[node]["layer"] = layer
    # Compute the multipartite_layout using the "layer" node attribute
    pos = nx.multipartite_layout(digraph, subset_key="layer")
    return pos


def serialize_taskgraph(taskgraph, pos):
    serialized = {"nodes": [], "edges": []}
    graph_size = 0
    for tasknode in taskgraph:
        serialized["nodes"].append(
            {
                "key": tasknode,
                "attributes": {
                    "color": "#B30000",
                    "label": taskgraph[tasknode]["label"],
                    "size": 5,
                    "x": pos[tasknode][0],
                    "y": pos[tasknode][1],
                },
            }
        )
        if taskgraph[tasknode]["dependencies"]:
            for dependency in taskgraph[tasknode]["dependencies"]:
                serialized["edges"].append(
                    {
                        "key": str(graph_size),
                        "source": taskgraph[tasknode]["dependencies"][dependency],
                        "target": tasknode,
                        "attributes": {"size": 2.5, "type": "arrow", 'kind': taskgraph[tasknode]['attributes']['kind']},
                    }
                )
                graph_size += 1
    return serialized


def main():
    taskgraph = load_taskgraph()
    digraph = build_digraph(taskgraph)
    pos = layout_digraph(digraph)
    serialized_taskgraph = serialize_taskgraph(taskgraph, pos)
    with open(f"./{TASKGRAPH_NAME}-serialized-taskgraph-{LAYOUT_NAME}.json", "w") as f:
        f.write(json.dumps(serialized_taskgraph, indent=2))


__name__ == "__main__" and main()
