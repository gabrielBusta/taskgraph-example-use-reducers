import argparse
import json
import logging
from pathlib import Path

import networkx as nx
import taskcluster

DEFAULT_LAYOUT = "multipartite-layout"
DEFAULT_ALIGNMENT = "vertical"
TASKCLUSTER_ROOT_URL = "https://firefox-ci-tc.services.mozilla.com/"


logging.basicConfig(
    level=logging.INFO,
    format=f"{Path(__file__).stem} - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_taskgraph(filename):
    with open(filename) as f:
        data = f.read()
    taskgraph = json.loads(data)
    return taskgraph


def build_digraph_from_taskgraph(taskgraph, name):
    digraph = nx.DiGraph(name=name)
    for tasknode in taskgraph:
        digraph.add_node(tasknode, **taskgraph[tasknode])
        if taskgraph[tasknode]["dependencies"]:
            for dependency in taskgraph[tasknode]["dependencies"]:
                digraph.add_edge(
                    taskgraph[tasknode]["dependencies"][dependency], tasknode
                )
    return digraph


def layout_digraph(digraph, alignment):
    for layer, nodes in enumerate(nx.topological_generations(digraph)):
        # `multipartite_layout` expects the layer as a node attribute, so add the
        # numeric layer value as a node attribute
        for node in nodes:
            digraph.nodes[node]["layer"] = layer
    # Compute the multipartite_layout using the "layer" node attribute
    pos = nx.multipartite_layout(digraph, subset_key="layer", align=alignment)
    return pos


def serialize_digraph(digraph, pos):
    serialized = {"nodes": [], "edges": []}
    graph_size = 0
    for node in digraph.nodes:
        serialized["nodes"].append(
            {
                "key": node,
                "attributes": {
                    "label": digraph.nodes[node]["task"]["metadata"]["name"],
                    "x": pos[node][0],
                    "y": pos[node][1],
                    "data": digraph.nodes[node],
                },
            }
        )
        dependencies = list(digraph.predecessors(node))
        if dependencies:
            for dependency in dependencies:
                serialized["edges"].append(
                    {
                        "key": str(graph_size),
                        "source": dependency,
                        "target": node,
                        "attributes": {
                            "type": "arrow",
                        },
                    }
                )
                graph_size += 1

    return serialized


def build_digraph_for_task_group(task_group):
    options = {"rootUrl": TASKCLUSTER_ROOT_URL}
    queue = taskcluster.Queue(options=options)
    tasks = []

    def pagination(y):
        tasks.extend(y.get("tasks", []))

    queue.listTaskGroup(task_group, paginationHandler=pagination)

    digraph = nx.DiGraph(name=task_group)

    for task in tasks:
        digraph.add_node(task["status"]["taskId"], **task)

    for task in tasks:
        for dep in task["task"]["dependencies"]:
            digraph.add_edge(task["status"]["taskId"], dep)

    return digraph


def main(args):
    if args.task_group:
        name = args.task_group
        input_graph = f"task-group-{args.task_group}"
        digraph = build_digraph_for_task_group(args.task_group)

    if args.decision_task:
        raise NotImplementedError(
            "Can't download and serialize a taskgraph from a decision task (yet.)"
        )

    if args.input_file:
        name = Path(args.input_file).stem
        input_graph = args.input_file
        taskgraph = load_taskgraph(args.input_file)
        digraph = build_digraph_from_taskgraph(taskgraph, name)

    output = (
        args.output
        if args.output
        else f"./data/output/{name}-{args.layout}-{args.alignment}.json"
    )

    pos = layout_digraph(digraph, args.alignment)
    serialized_digraph = serialize_digraph(digraph, pos)
    with open(
        output,
        "w",
    ) as f:
        f.write(json.dumps(serialized_digraph, indent=2))
    config = {
        "graph_name": name,
        "graph_order": f"{digraph.order():,}",
        "graph_size": f"{digraph.size():,}",
        "layout_algorithm": args.layout,
        "layout_alignment": args.alignment,
        "input_graph": input_graph,
        "output_file": output,
    }
    logging.info(f"config {json.dumps(config, indent=2)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A simple CLI tool to serialize Taskcluster Taskgraphs and Task Groups into Graphology Graphs."
    )
    parser.add_argument(
        "-g",
        "--task-group",
        help="a taskcluster task group",
        type=str,
    )
    parser.add_argument(
        "-d",
        "--decision-task",
        help="a taskcluster taskgraph decision task",
        type=str,
    )
    parser.add_argument(
        "-i",
        "--input-file",
        help="path to a taskgraph json file",
        type=str,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="path to the output file to save the serialized graphology graph",
        type=str,
    )
    parser.add_argument(
        "-l",
        "--layout",
        help=f'the layout algorithm of the graph - defaults to "{DEFAULT_LAYOUT}"',
        type=str,
        default=DEFAULT_LAYOUT,
    )
    parser.add_argument(
        "-a",
        "--alignment",
        help='specify the alignment - one of ["vertical", "horizontal"]',
        type=str,
        default=DEFAULT_ALIGNMENT,
    )

    args = parser.parse_args()
    main(args)
