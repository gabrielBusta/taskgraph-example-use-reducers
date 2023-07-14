import json
import networkx as nx
import re

TASKGRAPH_NAME = "ship-firefox-115.0"
LAYOUT_NAME = "multipartite-layout"
LAYOUT_ALIGNMENT = "horizontal"


all_locales = [
    "ach",
    "af",
    "an",
    "ar",
    "ast",
    "az",
    "be",
    "bg",
    "bn",
    "bo",
    "br",
    "brx",
    "bs",
    "ca",
    "ca-valencia",
    "cak",
    "ckb",
    "cs",
    "cy",
    "da",
    "de",
    "dsb",
    "el",
    "en-CA",
    "en-GB",
    "en-US",
    "eo",
    "es-AR",
    "es-CL",
    "es-ES",
    "es-MX",
    "et",
    "eu",
    "fa",
    "ff",
    "fi",
    "fr",
    "fur",
    "fy-NL",
    "ga-IE",
    "gd",
    "gl",
    "gn",
    "gu-IN",
    "he",
    "hi-IN",
    "hr",
    "hsb",
    "hu",
    "hy-AM",
    "hye",
    "ia",
    "id",
    "is",
    "it",
    "ja",
    "ja-JP-mac",
    "ka",
    "kab",
    "kk",
    "km",
    "kn",
    "ko",
    "lij",
    "lo",
    "lt",
    "ltg",
    "lv",
    "meh",
    "mk",
    "mr",
    "ms",
    "my",
    "nb-NO",
    "ne-NP",
    "nl",
    "nn-NO",
    "oc",
    "pa-IN",
    "pl",
    "pt-BR",
    "pt-PT",
    "rm",
    "ro",
    "ru",
    "sat",
    "sc",
    "scn",
    "sco",
    "si",
    "sk",
    "skr",
    "sl",
    "son",
    "sq",
    "sr",
    "sv-SE",
    "szl",
    "ta",
    "te",
    "tg",
    "th",
    "tl",
    "tr",
    "trs",
    "uk",
    "ur",
    "uz",
    "vi",
    "wo",
    "xh",
    "zh-CN",
    "zh-TW",
]


def dechunkify(label):
    """Removes any chunked parts of a label, eg: locale names, chunk numbers, etc."""
    # Chunked jobs, like update verify
    label = re.sub("-[0-9]+/[0-9]+", "", label)
    label = re.sub("-[0-9]+/opt", "", label)
    # dummies from reverse_chunk_deps
    label = re.sub("-[0-9]+$", "", label)
    # l10n
    for l in reversed(all_locales):
        label = label.replace(f"-{l}-", "-l10n-")
        # Some (but not all) jobs already have "l10n" in their name
        label = label.replace("l10n-l10n", "l10n")
        # some partner repacks have locale at the end
        label = re.sub(f"-{l}$", "-l10n", label)

    # partner jobs
    label = re.sub("(release-partner-.*shippable).*", "\1", label)

    return label


def load_taskgraph():
    f = open(f"./{TASKGRAPH_NAME}-taskgraph.json")
    data = f.read()
    f.close()
    taskgraph = json.loads(data)
    return taskgraph


def build_digraph(taskgraph):
    digraph = nx.DiGraph(name=TASKGRAPH_NAME)
    seen_labels = set()
    for tasknode in taskgraph:
        label = dechunkify(taskgraph[tasknode]["label"])
        if label in seen_labels:
            continue

        seen_labels.add(label)

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
    for layer, nodes in enumerate(nx.topological_generations(digraph)):
        # `multipartite_layout` expects the layer as a node attribute, so add the
        # numeric layer value as a node attribute
        for node in nodes:
            digraph.nodes[node]["layer"] = layer
    # Compute the multipartite_layout using the "layer" node attribute
    pos = nx.multipartite_layout(digraph, subset_key="layer", align=LAYOUT_ALIGNMENT)
    return pos


def serialize_taskgraph(taskgraph, pos):
    serialized = {"nodes": [], "edges": []}
    graph_size = 0
    seen_labels = set()
    seen_edges = set()
    for tasknode in taskgraph:
        label = dechunkify(taskgraph[tasknode]["label"])
        if label in seen_labels:
            continue

        seen_labels.add(label)
        serialized["nodes"].append(
            {
                "key": label,
                "attributes": {
                    "color": "#B30000",
                    "label": label,
                    # "size": 5,
                    "size": .5,
                    "x": pos[tasknode][0],
                    "y": pos[tasknode][1],
                },
            }
        )
        if taskgraph[tasknode]["dependencies"]:
            for dependency in taskgraph[tasknode]["dependencies"]:
                upstream_label = dechunkify(taskgraph[tasknode]["dependencies"][dependency])
                if (upstream_label, label) in seen_edges:
                    continue

                seen_edges.add((upstream_label, label))
                serialized["edges"].append(
                    {
                        "key": str(graph_size),
                        "source": upstream_label,
                        "target": label,
                        "attributes": {
                            # "size": 2.5,
                            "size": .25,
                            "type": "arrow",
                            "kind": taskgraph[tasknode]["attributes"]["kind"],
                        },
                    }
                )
                graph_size += 1
    return serialized


def main():
    taskgraph = load_taskgraph()
    digraph = build_digraph(taskgraph)
    pos = layout_digraph(digraph)
    serialized_taskgraph = serialize_taskgraph(taskgraph, pos)
    with open(f"./{TASKGRAPH_NAME}-serialized-taskgraph-{LAYOUT_NAME}-{LAYOUT_ALIGNMENT}.json", "w") as f:
        f.write(json.dumps(serialized_taskgraph, indent=2))


__name__ == "__main__" and main()
