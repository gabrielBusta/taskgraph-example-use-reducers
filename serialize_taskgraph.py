import argparse
import json
from pathlib import Path
import networkx as nx

# TASKGRAPH_NAME = "firefox-translations-training-ru-en"
DEFAULT_LAYOUT = "multipartite-layout"
DEFAULT_ALIGNMENT = "vertical"

def load_taskgraph(filename):
    with open(filename) as f:
        data = f.read()
    taskgraph = json.loads(data)
    return taskgraph


def build_digraph(taskgraph, name):
    digraph = nx.DiGraph(name=name)
    for tasknode in taskgraph:
        digraph.add_node(tasknode, **taskgraph[tasknode])
        if taskgraph[tasknode]["dependencies"]:
            for dependency in taskgraph[tasknode]["dependencies"]:
                digraph.add_edge(
                    taskgraph[tasknode]["dependencies"][dependency], tasknode
                )
    print("Order:", f"{digraph.order():,}")
    print("Size:", f"{digraph.size():,}")
    return digraph

def build_kinds_digraph():
    with open("./output/ff-release-kinds.json") as f:
        data = f.read()
    links = json.loads(data)
    digraph = nx.DiGraph(name="links")
    for link in links:
        digraph.add_node(link)
        if links[link]:
            for dependency in links[link]:
                digraph.add_edge(dependency, link)
    print("Order:", f"{digraph.order():,}")
    print("Size:", f"{digraph.size():,}")
    return digraph


def serialize_kinds(kinds, pos):
    serialized = {"nodes": [], "edges": []}
    graph_size = 0
    for kind in kinds:
        serialized["nodes"].append(
            {
                "key": kind,
                "attributes": {
                    "color": "#054096",
                    "label": kind,
                    "size": 5,
                    # "size": .5,
                    "x": pos[kind][0],
                    "y": pos[kind][1],
                },
            }
        )
        dependencies = [edge[0] for edge in list(kinds.in_edges(kind)) if edge]
        if dependencies:
            for dependency in dependencies:
                serialized["edges"].append(
                    {
                        "key": str(graph_size),
                        "source": dependency,
                        "target": kind,
                        "attributes": {
                            # "size": 2.5,
                            "size": 0.25,
                            "type": "arrow",
                            "kind": kind,
                        },
                    }
                )
                graph_size += 1
    return serialized


def layout_digraph(digraph, alignment):
    for layer, nodes in enumerate(nx.topological_generations(digraph)):
        # `multipartite_layout` expects the layer as a node attribute, so add the
        # numeric layer value as a node attribute
        for node in nodes:
            digraph.nodes[node]["layer"] = layer
    # Compute the multipartite_layout using the "layer" node attribute
    pos = nx.multipartite_layout(digraph, subset_key="layer", align=alignment)
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
                    "size": 20,
                    # "size": .5,
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
                        "attributes": {
                            "size": 2.5,
                            # "size": .25,
                            "type": "arrow",
                            "kind": taskgraph[tasknode]["attributes"]["kind"],
                        },
                    }
                )
                graph_size += 1
    return serialized


def main(args):
    assert args.input
    layout = args.layout if args.layout else DEFAULT_LAYOUT
    alignment = args.alignment if args.alignment else DEFAULT_ALIGNMENT
    print(f"Input: {args.input}")
    print(f"Layout: {layout}")
    print(f"Alignment: {alignment}")
    name = Path(args.input).stem
    print(f"Name: {name}")
    output = args.output if args.output else f"./data/output/{name}-{layout}-{alignment}.json"
    print(f"Output: {output}")
    taskgraph = load_taskgraph(args.input)
    # digraph = build_kinds_digraph()
    digraph = build_digraph(taskgraph, name)
    pos = layout_digraph(digraph, alignment)
    # serialized_kinds = serialize_kinds(digraph, pos)
    # with open(f"./output-serialized-ff-release-kinds.json", "w") as f:
    #     f.write(json.dumps(serialized_kinds, indent=2))
    serialized_taskgraph = serialize_taskgraph(taskgraph, pos)
    with open(
        output,
        "w",
    ) as f:
        f.write(json.dumps(serialized_taskgraph, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple CLI tool.")
    parser.add_argument(
        "-i", "--input", help="Path to the input file.", type=str, required=True
    )
    parser.add_argument("-l", "--layout", help="Specify the layout.", type=str)
    parser.add_argument("-a", "--alignment", help="Specify the alignment.", type=str)
    parser.add_argument("-o", "--output", help="Path to the output file.", type=str)

    args = parser.parse_args()
    main(args)
