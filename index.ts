import Sigma from "sigma";
import { Coordinates, EdgeDisplayData, NodeDisplayData } from "sigma/types";
import { DirectedGraph as Graph } from "graphology";
// import data from "./mc-desktop-nightly-serialized-taskgraph-multipartite-layout.json";
// import data from "./mc-onpush-serialized-taskgraph-multipartite-layout.json";
// import data from "./ship-firefox-115.0-serialized-taskgraph-multipartite-layout.json";
// import data from "./firefox-translations-training-serialized-taskgraph-multipartite-layout.json";
// import data from "./mr-promote-firefox-serialized-taskgraph-multipartite-layout.json";
// import data from "./mr-onpush-serialized-taskgraph-multipartite-layout.json";
// import data from "./mr-onpush-geckoview-serialized-taskgraph-multipartite-layout.json";
// import data from "./ship-mozilla-vpn-client-serialized-taskgraph-multipartite-layout.json";
// import data from "./main-onpush-mozilla-vpn-client-serialized-taskgraph-multipartite-layout.json";
// import data from "./nss-try-push-serialized-taskgraph-multipartite-layout.json";
// import data from "./firefox-translations-training-fr-en-serialized-taskgraph-multipartite-layout.json";
// import data from "./firefox-translations-training-fr-en-serialized-taskgraph-multipartite-layout-horizontal.json";
// import data from "./firefox-translations-training-ru-en-serialized-taskgraph-multipartite-layout-horizontal.json";
// import data from "./serialized_kinds.json";
// import data from "./serialized-mc-desktop-nightly-kinds.json.json";
import data from "./ser-ff-release-kinds.json";

// Retrieve some useful DOM elements:
const container = document.getElementById("sigma-container") as HTMLElement;
const searchInput = document.getElementById("search-input") as HTMLInputElement;
const searchSuggestions = document.getElementById(
  "suggestions"
) as HTMLDataListElement;

// Instantiate sigma:
const graph = new Graph();
graph.import(data);
const renderer = new Sigma(graph, container);

let originalPositions = {};

graph.nodes().forEach((nodeKey) => {
  const position = renderer.getNodeDisplayData(nodeKey);
  originalPositions[nodeKey] = { ...position };
});

// Type and declare internal state:
interface State {
  hoveredNode?: string;
  hoveredNeighbors?: Set<string>;

  searchQuery: string;

  // State derived from query:
  selectedNode?: string;
  suggestions?: Set<string>;

  pinnedSet: Set<string>;
  viewSet: Set<string>;
}
const state: State = {
  searchQuery: "",
  pinnedSet: new Set(),
  viewSet: new Set(),
};

// Feed the datalist autocomplete values:
searchSuggestions.innerHTML = graph
  .nodes()
  .map(
    (node) =>
      `<option value="${graph.getNodeAttribute(node, "label")}"></option>`
  )
  .join("\n");

// Actions:
function setSearchQuery(query: string) {
  state.searchQuery = query;

  if (searchInput.value !== query) searchInput.value = query;

  if (query) {
    const lcQuery = query.toLowerCase();
    const suggestions = graph
      .nodes()
      .map((n) => ({
        id: n,
        label: graph.getNodeAttribute(n, "label") as string,
      }))
      .filter(({ label }) => label.toLowerCase().includes(lcQuery));

    // If we have a single perfect match, them we remove the suggestions, and
    // we consider the user has selected a node through the datalist
    // autocomplete:
    if (suggestions.length === 1 && suggestions[0].label === query) {
      state.selectedNode = suggestions[0].id;
      state.suggestions = undefined;

      // Move the camera to center it on the selected node:
      const nodePosition = renderer.getNodeDisplayData(
        state.selectedNode
      ) as Coordinates;
      renderer.getCamera().animate(nodePosition, {
        duration: 500,
      });
    }
    // Else, we display the suggestions list:
    else {
      state.selectedNode = undefined;
      state.suggestions = new Set(suggestions.map(({ id }) => id));
    }
  }
  // If the query is empty, then we reset the selectedNode / suggestions state:
  else {
    state.selectedNode = undefined;
    state.suggestions = undefined;
  }

  // Refresh rendering:
  renderer.refresh();
}

// Bind search input interactions:
searchInput.addEventListener("input", () => {
  setSearchQuery(searchInput.value || "");
});

searchInput.addEventListener("blur", () => {
  setSearchQuery("");
});

renderer.on("enterNode", ({ node }) => {
  state.hoveredNode = node;
  state.hoveredNeighbors = new Set(graph.neighbors(node));
  renderer.refresh();
});

renderer.on("leaveNode", () => {
  state.hoveredNode = undefined;
  state.hoveredNeighbors = undefined;
  renderer.refresh();
});

renderer.on("clickNode", ({ node }) => {
  if (state.pinnedSet.has(node)) {
    // Unpin the node if it's already pinned
    state.pinnedSet.delete(node);
    state.viewSet.clear();
  } else if (
    Array.from(state.pinnedSet).some((pinned) =>
      graph.areNeighbors(pinned, node)
    )
  ) {
    // If the clicked node is a neighbor of any pinned node
    state.viewSet.add(node);
    graph.neighbors(node).forEach((neighbor) => state.viewSet.add(neighbor));
  } else {
    // If the clicked node is neither pinned nor a neighbor of a pinned node
    state.pinnedSet.clear();
    state.viewSet.clear();
    state.pinnedSet.add(node);
    graph.neighbors(node).forEach((neighbor) => state.viewSet.add(neighbor));
  }

  // Compute the bounding box of the viewSet
  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;

  state.viewSet.forEach((viewNode) => {
    const position = renderer.getNodeDisplayData(viewNode) as Coordinates;
    minX = Math.min(minX, position.x);
    maxX = Math.max(maxX, position.x);
    minY = Math.min(minY, position.y);
    maxY = Math.max(maxY, position.y);
  });

  const nodePosition = renderer.getNodeDisplayData(node) as Coordinates;

  // Compute the center of the bounding box
  const boundingBoxCenterX = (minX + maxX) / 2;
  const boundingBoxCenterY = (minY + maxY) / 2;

  // Determine the offset of the clicked node from the center of the bounding box
  const offsetX = nodePosition.x - boundingBoxCenterX;
  const offsetY = nodePosition.y - boundingBoxCenterY;

  // Adjust the center coordinates by the offset
  const adjustedCenterX = boundingBoxCenterX + offsetX;
  const adjustedCenterY = boundingBoxCenterY + offsetY;

  // Compute the width and height of the bounding box
  const width = maxX - minX;
  const height = maxY - minY;

  // Use the maximum of width and height to determine the zoom ratio
  const maxDimension = Math.max(width, height);
  const dimensions = renderer.getDimensions();
  const screenDimension = Math.min(dimensions.width, dimensions.height); 
  const desiredZoom = (screenDimension / (maxDimension + 20)) * .08; // Add some margin

  // Animate the camera to the new position and zoom
  renderer.getCamera().animate(
    {
      x: adjustedCenterX,
      y: adjustedCenterY,
      ratio: 1 / desiredZoom,
    },
    {
      duration: 500,
    }
  );


  renderer.refresh();
});

renderer.setSetting("defaultEdgeColor", "black");
renderer.setSetting("defaultNodeColor", "#054096");
renderer.setSetting("labelDensity", 0.5);
renderer.setSetting("labelGridCellSize", 60);

renderer.setSetting("nodeReducer", (node, data) => {
  const res: Partial<NodeDisplayData> = { ...data };

  if (state.pinnedSet.has(node) || state.hoveredNode === node) {
    res.highlighted = true;
  } else if (
    (!state.pinnedSet.size &&
      state.hoveredNeighbors &&
      !state.hoveredNeighbors.has(node)) ||
    (state.pinnedSet.size && !state.viewSet.has(node))
  ) {
    res.hidden = true;
  } else if (
    state.viewSet.has(node)
  ) {
    res.forceLabel = true;
  }

  return res;
});

renderer.setSetting("edgeReducer", (edge, data) => {
  const res: Partial<EdgeDisplayData> = { ...data };
  const source = graph.source(edge);
  const target = graph.target(edge);

  const isHoveredEdge =
    state.hoveredNode &&
    (state.hoveredNode === source || state.hoveredNode === target);
  const isPinnedOrViewEdge =
    state.pinnedSet.has(source) ||
    state.viewSet.has(source) ||
    state.pinnedSet.has(target) ||
    state.viewSet.has(target);

  // If no node is pinned, just display all edges. Otherwise, check the edge against our conditions:
  if (!state.pinnedSet.size) {
    res.hidden = false; // Display all edges
  } else if (!isHoveredEdge && !isPinnedOrViewEdge) {
    res.hidden = true;
  }
  return res;
});
