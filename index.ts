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

  // Zoom and Attraction logic here
  const nodePosition = renderer.getNodeDisplayData(node) as Coordinates;

  renderer.getCamera().animate(
    {
      x: nodePosition.x,
      y: nodePosition.y,
      ratio: .25, // Adjust this value for desired zoom level
    },
    {
      duration: 500,
    }
  );

  renderer.refresh();
});

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
  }
  return res;
});

function drawLabel(context, data, settings) {
  if (!data.label) return;

  const size = settings.labelSize,
    font = settings.labelFont,
    weight = settings.labelWeight;

  context.font = `${weight} ${size}px ${font}`;
  const width = context.measureText(data.label).width + 8;

  // Center the label's background inside the node
  context.fillStyle = "#ffffffcc";
  context.fillRect(
    data.x - width / 2, // Adjust for centering
    data.y - size / 2, // Adjust for centering
    width,
    size
  );

  context.fillStyle = "#000";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(data.label, data.x, data.y);
}

function drawHover(context, data, settings) {
  // const size = settings.labelSize,
  //   font = settings.labelFont,
  //   weight = settings.labelWeight;

  // context.font = `${weight} ${size}px ${font}`;

  // // Then we draw the label background
  // context.fillStyle = "#FFF";

  // const PADDING = 2;

  // if (typeof data.label === "string") {
  //   const textWidth = context.measureText(data.label).width,
  //     boxWidth = Math.round(textWidth + 5),
  //     boxHeight = Math.round(size + 2 * PADDING),
  //     radius = Math.max(data.size, size / 2) + PADDING;

  //   const angleRadian = Math.asin(boxHeight / 2 / radius);
  //   const xDeltaCoord = data.x - Math.sqrt(Math.abs(Math.pow(radius, 2) - Math.pow(boxHeight / 2, 2)));

  //   context.beginPath();
  //   context.moveTo(xDeltaCoord - boxWidth / 2, data.y + boxHeight / 2);
  //   context.lineTo(xDeltaCoord + boxWidth / 2, data.y + boxHeight / 2);
  //   context.lineTo(xDeltaCoord + boxWidth / 2, data.y - boxHeight / 2);
  //   context.lineTo(xDeltaCoord - boxWidth / 2, data.y - boxHeight / 2);
  //   context.arc(data.x, data.y, radius, angleRadian, -angleRadian);
  //   context.closePath();
  //   context.fill();
  // } else {
  //   context.beginPath();
  //   context.arc(data.x, data.y, data.size + PADDING, 0, Math.PI * 2);
  //   context.closePath();
  //   context.fill();
  // }

  // drawLabel(context, data, settings);
}

renderer.setSetting("hoverRenderer", drawHover);
renderer.setSetting("labelRenderer", drawLabel);

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
