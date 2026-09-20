import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  Database,
  Factory,
  Globe2,
  RotateCcw,
  TrendingUp,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import "./ButterflyMap.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function getNodeType(node) {
  return node?.node_type || node?.type || "unknown";
}

function getNodeRadius(node) {
  switch (getNodeType(node)) {
    case "region":
      return 22;
    case "market":
      return 19;
    case "logistics":
      return 17;
    case "commodity":
      return 15;
    case "input":
      return 15;
    default:
      return 15;
  }
}

function getNodeColor(node) {
  const type = getNodeType(node);

  if (node.id === "europe") return "#69f19a";

  switch (type) {
    case "region":
      return "#54d98a";
    case "commodity":
      return "#ffd15c";
    case "logistics":
      return "#56c8ff";
    case "market":
      return "#c88cff";
    case "input":
      return "#f5c95b";
    default:
      return "#8be8ad";
  }
}

function getNodeIcon(node) {
  const type = getNodeType(node);

  switch (type) {
    case "region":
      return "🌳";
    case "commodity":
      return "🌾";
    case "logistics":
      return "🚢";
    case "market":
      return "🌍";
    case "input":
      return "⚙️";
    default:
      return "●";
  }
}

function getNodeRole(node) {
  const type = getNodeType(node);

  if (node.role === "producer") {
    return "Wheat production & trade";
  }

  if (node.role === "importer") {
    return "Wheat import market";
  }

  switch (type) {
    case "region":
      return "Regional production & trade";
    case "commodity":
      return "Commodity dependency";
    case "logistics":
      return "Logistics infrastructure";
    case "market":
      return "Market / demand node";
    case "input":
      return "Production input dependency";
    default:
      return "Dependency graph node";
  }
}

function getEdgeType(edge) {
  return edge?.relationship || edge?.type || "UNKNOWN";
}

function getEdgeColor(edge) {
  switch (getEdgeType(edge)) {
    case "SUPPLIES_TO":
      return "#68e89b";
    case "PRODUCES":
      return "#ffd15c";
    case "CONNECTS_ROUTE":
      return "#56c8ff";
    case "PRICE_TRANSMISSION":
      return "#c88cff";
    case "AFFECTS_MARKET":
      return "#d0a2ff";
    case "AFFECTS_LOGISTICS":
      return "#69d5ff";
    case "REQUIRES_INPUT":
      return "#f5c95b";
    case "USES_LOGISTICS":
      return "#56c8ff";
    default:
      return "#8fd9ac";
  }
}

function formatTonnes(value) {
  if (value === undefined || value === null) {
    return "—";
  }

  const tonnes = Number(value);

  if (!Number.isFinite(tonnes)) {
    return "—";
  }

  return `${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(tonnes)} t`;
}

function formatCurrency(value) {
  if (value === undefined || value === null) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(number);
}

function formatPercent(value) {
  if (value === undefined || value === null) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(2)}%`;
}

function getNodeStats(node, graph) {
  const incoming =
    graph?.edges?.filter(
      (edge) => edge.target === node.id
    ).length || 0;

  const outgoing =
    graph?.edges?.filter(
      (edge) => edge.source === node.id
    ).length || 0;

  return { incoming, outgoing };
}

function getNodeProduction(node) {
  return (
    node?.production_tonnes ??
    node?.production ??
    null
  );
}

function getSelectedTradeStats(node, graph) {
  if (!node || !graph?.edges) {
    return {
      importValue: 0,
      exportValue: 0,
      tradeFlows: 0,
    };
  }

  let importValue = 0;
  let exportValue = 0;
  let tradeFlows = 0;
  const tradeValue = (edge) =>
    edge?.trade_value_usd ?? edge?.trade_value ?? null;

  for (const edge of graph.edges) {
    if (getEdgeType(edge) !== "SUPPLIES_TO") {
      continue;
    }

    if (edge.source === node.id) {
      const value = tradeValue(edge);
      if (value !== null) exportValue += Number(value);
      tradeFlows += 1;
    }

    if (edge.target === node.id) {
      const value = tradeValue(edge);
      if (value !== null) importValue += Number(value);
      tradeFlows += 1;
    }
  }

  return {
    importValue,
    exportValue,
    tradeFlows,
  };
}

function getRiskClass(risk) {
  switch (risk) {
    case "HIGH":
      return "high";
    case "MODERATE":
      return "moderate";
    case "LOW":
      return "low";
    default:
      return "";
  }
}

export default function ButterflyMap({
  graph,
  simulation,
}) {
  const svgRef = useRef(null);
  const wrapperRef = useRef(null);
  const zoomRef = useRef(null);

  const [selectedNode, setSelectedNode] =
    useState(null);

  const [zoomLevel, setZoomLevel] =
    useState(1);

  const [nodeScenario, setNodeScenario] =
    useState(null);

  const [nodeScenarioLoading, setNodeScenarioLoading] =
    useState(false);

  const [nodeScenarioError, setNodeScenarioError] =
    useState(null);

  useEffect(() => {
    if (
      !graph?.nodes?.length ||
      !graph?.edges?.length ||
      !svgRef.current
    ) {
      return;
    }

    const svg = d3.select(svgRef.current);

    svg.selectAll("*").remove();

    const width =
      wrapperRef.current?.clientWidth ||
      900;

    const height = 560;

    svg
      .attr(
        "viewBox",
        `0 0 ${width} ${height}`
      )
      .attr(
        "preserveAspectRatio",
        "xMidYMid meet"
      );

    const defs = svg.append("defs");

    const glow = defs
      .append("filter")
      .attr("id", "atlas-node-glow")
      .attr("x", "-100%")
      .attr("y", "-100%")
      .attr("width", "300%")
      .attr("height", "300%");

    glow
      .append("feGaussianBlur")
      .attr("stdDeviation", "3")
      .attr("result", "blur");

    const merge = glow.append("feMerge");

    merge
      .append("feMergeNode")
      .attr("in", "blur");

    merge
      .append("feMergeNode")
      .attr(
        "in",
        "SourceGraphic"
      );

    const arrow = defs
      .append("marker")
      .attr("id", "atlas-arrow")
      .attr(
        "viewBox",
        "0 -5 10 10"
      )
      .attr("refX", 11)
      .attr("refY", 0)
      .attr(
        "markerWidth",
        7
      )
      .attr(
        "markerHeight",
        7
      )
      .attr(
        "orient",
        "auto"
      );

    arrow
      .append("path")
      .attr(
        "d",
        "M0,-4L9,0L0,4"
      )
      .attr(
        "fill",
        "#7be9a6"
      )
      .attr(
        "opacity",
        0.75
      );

    const container = svg
      .append("g")
      .attr(
        "class",
        "atlas-graph-world"
      );

    const zoom = d3
      .zoom()
      .scaleExtent([
        0.45,
        2.4,
      ])
      .on(
        "zoom",
        (event) => {
          container.attr(
            "transform",
            event.transform
          );

          setZoomLevel(
            event.transform.k
          );
        }
      );

    zoomRef.current = zoom;

    svg.call(zoom);

    const nodes =
      graph.nodes.map(
        (node) => ({
          ...node,
        })
      );

    const nodeMap =
      new Map(
        nodes.map(
          (node) => [
            node.id,
            node,
          ]
        )
      );

    const links =
      graph.edges
        .map((edge) => ({
          ...edge,
          source:
            nodeMap.get(
              edge.source
            ),
          target:
            nodeMap.get(
              edge.target
            ),
        }))
        .filter(
          (edge) =>
            edge.source &&
            edge.target
        );

    const simulationForce =
      d3
        .forceSimulation(
          nodes
        )
        .force(
          "link",
          d3
            .forceLink(
              links
            )
            .id(
              (d) => d.id
            )
            .distance(
              (d) => {
                const type =
                  getEdgeType(d);

                if (
                  type ===
                  "SUPPLIES_TO"
                ) {
                  return 150;
                }

                if (
                  type ===
                  "CONNECTS_ROUTE"
                ) {
                  return 145;
                }

                if (
                  type ===
                  "PRICE_TRANSMISSION"
                ) {
                  return 125;
                }

                return 120;
              }
            )
            .strength(0.5)
        )
        .force(
          "charge",
          d3
            .forceManyBody()
            .strength(-650)
        )
        .force(
          "center",
          d3.forceCenter(
            width / 2,
            height / 2
          )
        )
        .force(
          "collision",
          d3
            .forceCollide()
            .radius(
              (d) =>
                getNodeRadius(
                  d
                ) + 34
            )
            .strength(0.95)
        );

    const edgeGroup =
      container
        .append("g")
        .attr(
          "class",
          "atlas-edge-group"
        );

    const edge =
      edgeGroup
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr(
          "class",
          "atlas-edge"
        )
        .attr(
          "stroke",
          (d) =>
            getEdgeColor(d)
        )
        .attr(
          "stroke-width",
          (d) =>
            Math.max(
              1.4,
              Number(
                d.dependency_weight ??
                  d.weight ??
                  0.35
              ) * 4.5
            )
        )
        .attr(
          "stroke-opacity",
          0.55
        )
        .attr(
          "stroke-dasharray",
          (d) =>
            getEdgeType(d) ===
            "PRICE_TRANSMISSION"
              ? "7 6"
              : null
        )
        .attr(
          "marker-end",
          "url(#atlas-arrow)"
        );

    const nodeGroup =
      container
        .append("g")
        .attr(
          "class",
          "atlas-node-group"
        );

    const node =
      nodeGroup
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .attr(
          "class",
          "atlas-node"
        )
        .style(
          "cursor",
          "pointer"
        )
        .call(
          d3
            .drag()
            .on(
              "start",
              (
                event,
                d
              ) => {
                if (
                  !event.active
                ) {
                  simulationForce
                    .alphaTarget(
                      0.25
                    )
                    .restart();
                }

                d.fx =
                  d.x;
                d.fy =
                  d.y;
              }
            )
            .on(
              "drag",
              (
                event,
                d
              ) => {
                d.fx =
                  event.x;
                d.fy =
                  event.y;
              }
            )
            .on(
              "end",
              (
                event,
                d
              ) => {
                if (
                  !event.active
                ) {
                  simulationForce
                    .alphaTarget(
                      0
                    );
                }

                d.fx =
                  null;
                d.fy =
                  null;
              }
            )
        );

    node
      .append("circle")
      .attr(
        "class",
        "atlas-node-glow"
      )
      .attr(
        "r",
        (d) =>
          getNodeRadius(
            d
          ) + 7
      )
      .attr(
        "fill",
        "none"
      )
      .attr(
        "stroke",
        (d) =>
          getNodeColor(
            d
          )
      )
      .attr(
        "stroke-width",
        1
      )
      .attr(
        "stroke-opacity",
        0.28
      );

    node
      .append("circle")
      .attr(
        "class",
        "atlas-node-circle"
      )
      .attr(
        "r",
        (d) =>
          getNodeRadius(
            d
          )
      )
      .attr(
        "fill",
        "rgba(4,25,17,0.94)"
      )
      .attr(
        "stroke",
        (d) =>
          getNodeColor(
            d
          )
      )
      .attr(
        "stroke-width",
        2.2
      );

    node
      .append("circle")
      .attr(
        "class",
        "atlas-node-inner"
      )
      .attr(
        "r",
        (d) =>
          getNodeRadius(
            d
          ) - 5
      )
      .attr(
        "fill",
        (d) =>
          getNodeColor(
            d
          )
      )
      .attr(
        "fill-opacity",
        0.10
      )
      .attr(
        "stroke",
        "none"
      );

    node
      .append("text")
      .attr(
        "class",
        "atlas-node-icon"
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "dominant-baseline",
        "central"
      )
      .attr(
        "font-size",
        (d) => {
          const type =
            getNodeType(d);

          if (
            type ===
            "region"
          ) {
            return 19;
          }

          if (
            type ===
            "market"
          ) {
            return 17;
          }

          return 15;
        }
      )
      .text((d) =>
        getNodeIcon(d)
      );

    node
      .append("text")
      .attr(
        "class",
        "atlas-node-name"
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "y",
        (d) =>
          getNodeRadius(
            d
          ) + 19
      )
      .text(
        (d) =>
          d.name
      );

    node
      .append("text")
      .attr(
        "class",
        "atlas-node-type"
      )
      .attr(
        "text-anchor",
        "middle"
      )
      .attr(
        "y",
        (d) =>
          getNodeRadius(
            d
          ) + 32
      )
      .text(
        (d) =>
          String(
            getNodeType(d)
          ).toUpperCase()
      );

    node
      .on(
        "mouseenter",
        function (
          _,
          d
        ) {
          d3.select(
            this
          )
            .select(
              ".atlas-node-circle"
            )
            .attr(
              "stroke-width",
              4
            );

          d3.select(
            this
          )
            .select(
              ".atlas-node-glow"
            )
            .attr(
              "stroke-opacity",
              0.65
            )
            .attr(
              "r",
              getNodeRadius(
                d
              ) + 10
            );

          edge.attr(
            "stroke-opacity",
            (edgeData) => {
              if (
                edgeData
                  .source
                  .id ===
                  d.id ||
                edgeData
                  .target
                  .id ===
                  d.id
              ) {
                return 0.95;
              }

              return 0.12;
            }
          );
        }
      )
      .on(
        "mouseleave",
        function (
          _,
          d
        ) {
          d3.select(
            this
          )
            .select(
              ".atlas-node-circle"
            )
            .attr(
              "stroke-width",
              2.2
            );

          d3.select(
            this
          )
            .select(
              ".atlas-node-glow"
            )
            .attr(
              "stroke-opacity",
              0.28
            )
            .attr(
              "r",
              getNodeRadius(
                d
              ) + 7
            );

          edge.attr(
            "stroke-opacity",
            0.55
          );
        }
      )
      .on(
        "click",
        async (_, d) => {
          setSelectedNode(d);
          setNodeScenario(null);
          setNodeScenarioError(null);
          setNodeScenarioLoading(true);

          try {
            const shockPercent =
              Number(
                simulation?.scenario
                  ?.shock_percent ??
                  simulation?.request
                    ?.shock_percent ??
                  simulation?.inputs
                    ?.shock_percent ??
                  -20
              );

            const horizon =
              Number(
                simulation?.scenario
                  ?.time_horizon_months ??
                  simulation?.request
                    ?.time_horizon_months ??
                  simulation?.inputs
                    ?.time_horizon_months ??
                  6
              );

            const alternateSupply =
              Number(
                simulation?.scenario
                  ?.alternate_supply_percent ??
                  simulation?.request
                    ?.alternate_supply_percent ??
                  simulation?.inputs
                    ?.alternate_supply_percent ??
                  10
              );

            const response =
              await fetch(
                `${API_URL}/api/scenario/node/${encodeURIComponent(
                  d.id
                )}`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type":
                      "application/json",
                  },
                  body: JSON.stringify({
                    shock_region:
                      "europe",
                    shock_percent:
                      Number.isFinite(
                        shockPercent
                      )
                        ? shockPercent
                        : -20,
                    time_horizon_months:
                      Number.isFinite(
                        horizon
                      )
                        ? horizon
                        : 6,
                    alternate_supply_percent:
                      Number.isFinite(
                        alternateSupply
                      )
                        ? alternateSupply
                        : 10,
                  }),
                }
              );

            if (!response.ok) {
              let detail =
                `Node scenario request failed (${response.status})`;

              try {
                const errorBody =
                  await response.json();

                if (
                  errorBody?.detail
                ) {
                  detail =
                    errorBody.detail;
                }
              } catch {
                // Keep the fallback message.
              }

              throw new Error(
                detail
              );
            }

            const result =
              await response.json();

            setNodeScenario(
              result
            );
          } catch (error) {
            console.error(
              "ATLAS node scenario request failed:",
              error
            );

            setNodeScenarioError(
              error?.message ||
                "Unable to load backend scenario data."
            );
          } finally {
            setNodeScenarioLoading(
              false
            );
          }
        }
      );

    simulationForce.on(
      "tick",
      () => {
        edge
          .attr(
            "x1",
            (d) =>
              d.source.x
          )
          .attr(
            "y1",
            (d) =>
              d.source.y
          )
          .attr(
            "x2",
            (d) =>
              d.target.x
          )
          .attr(
            "y2",
            (d) =>
              d.target.y
          );

        node.attr(
          "transform",
          (d) =>
            `translate(${d.x},${d.y})`
        );
      }
    );

    return () => {
      simulationForce.stop();
      zoomRef.current = null;
    };
  }, [graph, simulation]);

  function zoomIn() {
    if (
      !svgRef.current ||
      !zoomRef.current
    ) {
      return;
    }

    d3.select(
      svgRef.current
    )
      .transition()
      .duration(250)
      .call(
        zoomRef.current.scaleBy,
        1.25
      );
  }

  function zoomOut() {
    if (
      !svgRef.current ||
      !zoomRef.current
    ) {
      return;
    }

    d3.select(
      svgRef.current
    )
      .transition()
      .duration(250)
      .call(
        zoomRef.current.scaleBy,
        0.8
      );
  }

  function resetZoom() {
    if (
      !svgRef.current ||
      !zoomRef.current
    ) {
      return;
    }

    d3.select(
      svgRef.current
    )
      .transition()
      .duration(300)
      .call(
        zoomRef.current.transform,
        d3.zoomIdentity
      );
  }

  if (!graph?.nodes?.length) {
    return (
      <section className="atlas-butterfly-section">
        <div className="atlas-butterfly-empty">
          <Globe2 size={30} />

          <h2>
            Butterfly Map
          </h2>

          <p>
            Waiting for the
            ATLAS dependency
            graph...
          </p>
        </div>
      </section>
    );
  }

  const selectedStats =
    selectedNode
      ? getNodeStats(
          selectedNode,
          graph
        )
      : null;

  const selectedTradeStats =
    selectedNode
      ? getSelectedTradeStats(
          selectedNode,
          graph
        )
      : null;

  const backendImpact =
    nodeScenario?.impact ||
    null;

  const backendIntervention =
    nodeScenario?.intervention ||
    null;

  const backendPaths =
    nodeScenario?.paths ||
    null;

  const backendProvenance =
    nodeScenario?.provenance ||
    null;

  const activePaths =
    backendPaths?.active_path_count ??
    0;

  const cascadePressure =
    backendImpact?.deficit_percent ??
    0;

  const directlyExposed =
    backendImpact !== null;

  const isSourceNode =
    nodeScenario &&
    nodeScenario.scenario?.shock_sources?.includes(
      selectedNode?.id
    );

  return (
    <section className="atlas-butterfly-section">
      <div className="atlas-butterfly-header">
        <div>
          <div className="atlas-butterfly-kicker">
            <Globe2 size={14} />
            KNOWLEDGE GRAPH
          </div>

          <h2>
            Butterfly Map
          </h2>

          <p>
            Explore how a regional wheat
            shock propagates through
            production, trade, logistics
            and downstream markets.
          </p>
        </div>

        <div className="atlas-live-status">
          <span className="atlas-live-dot" />
          LIVE GRAPH
        </div>
      </div>

      <div className="atlas-butterfly-layout">
        <div
          className="atlas-graph-card"
          ref={wrapperRef}
        >
          <div className="atlas-graph-toolbar">
            <div className="atlas-graph-heading">
              <div className="atlas-graph-icon">
                🌍
              </div>

              <div>
                <strong>
                  Global Wheat Dependency
                  Network
                </strong>

                <span>
                  Production · Trade · Logistics ·
                  Markets
                </span>
              </div>
            </div>

            <div className="atlas-zoom-controls">
              <button
                type="button"
                onClick={zoomOut}
                title="Zoom out"
              >
                <ZoomOut size={16} />
              </button>

              <span>
                {Math.round(
                  zoomLevel * 100
                )}
                %
              </span>

              <button
                type="button"
                onClick={zoomIn}
                title="Zoom in"
              >
                <ZoomIn size={16} />
              </button>

              <button
                type="button"
                onClick={resetZoom}
                title="Reset view"
              >
                <RotateCcw size={15} />
              </button>
            </div>
          </div>

          <div className="atlas-graph-instruction">
            <span>↕</span>
            Drag nodes
            <span>•</span>
            Click a node to inspect
          </div>

          <svg
            ref={svgRef}
            className="atlas-butterfly-svg"
          />

          <div className="atlas-graph-legend">
            <LegendDot
              color="#54d98a"
              label="Regions"
            />

            <LegendDot
              color="#ffd15c"
              label="Commodity"
            />

            <LegendDot
              color="#56c8ff"
              label="Logistics"
            />

            <LegendDot
              color="#c88cff"
              label="Market"
            />

            <LegendDot
              color="#f5c95b"
              label="Inputs"
            />
          </div>

          <div className="atlas-edge-legend">
            <span className="atlas-edge-sample" />
            Supply

            <span className="atlas-edge-sample route" />
            Route

            <span className="atlas-edge-sample price" />
            Price
          </div>

          <div className="atlas-floating-butterfly butterfly-a">
            🦋
          </div>

          <div className="atlas-floating-butterfly butterfly-b">
            🦋
          </div>

          <div className="atlas-floating-leaf leaf-a">
            🍃
          </div>
        </div>

        <aside className="atlas-node-inspector">
          {!selectedNode ? (
            <div className="atlas-inspector-empty">
              <div className="atlas-empty-icon">
                🔎
              </div>

              <span className="atlas-inspector-kicker">
                NODE INSPECTOR
              </span>

              <h3>
                Select a node
              </h3>

              <p>
                Click any region, commodity,
                logistics or market node to
                inspect its role and modeled
                relationships.
              </p>

              <div className="atlas-empty-hint">
                <ArrowRight size={14} />
                Click a node on the map
              </div>
            </div>
          ) : (
            <>
              <div className="atlas-inspector-top">
                <div
                  className="atlas-inspector-node-icon"
                  style={{
                    borderColor:
                      getNodeColor(
                        selectedNode
                      ),
                    boxShadow: `0 0 24px ${getNodeColor(
                      selectedNode
                    )}22`,
                  }}
                >
                  {getNodeIcon(
                    selectedNode
                  )}
                </div>

                <div>
                  <span className="atlas-inspector-type">
                    {getNodeType(
                      selectedNode
                    )}
                  </span>

                  <h3>
                    {selectedNode.name}
                  </h3>

                  <p>
                    {getNodeRole(
                      selectedNode
                    )}
                  </p>
                </div>
              </div>

              <div className="atlas-inspector-divider" />

              <div className="atlas-inspector-section-title">
                <Database size={13} />
                NODE DATA
              </div>

              <InspectorRow
                icon={
                  <Factory size={14} />
                }
                label="Production"
                value={formatTonnes(
                  getNodeProduction(
                    selectedNode
                  )
                )}
              />

              <InspectorRow
                icon={
                  <ArrowRight size={14} />
                }
                label="Exports"
                value={
                  selectedTradeStats
                    ? formatCurrency(
                        selectedTradeStats.exportValue
                      )
                    : "—"
                }
              />

              <InspectorRow
                icon={
                  <ArrowDownRight
                    size={14}
                  />
                }
                label="Imports"
                value={
                  selectedTradeStats
                    ? formatCurrency(
                        selectedTradeStats.importValue
                      )
                    : "—"
                }
              />

              {selectedNode.production_data_source && (
                <InspectorRow
                  icon={
                    <Database size={14} />
                  }
                  label="Production source"
                  value={
                    selectedNode.production_data_source
                  }
                />
              )}

              {selectedNode.production_reference_year && (
                <InspectorRow
                  icon={
                    <Activity size={14} />
                  }
                  label="Reference year"
                  value={
                    selectedNode.production_reference_year
                  }
                />
              )}

              <div className="atlas-inspector-divider" />

              <div className="atlas-inspector-section-title">
                <Activity size={13} />
                GRAPH RELATIONSHIPS
              </div>

              <InspectorRow
                icon={
                  <ArrowDownRight
                    size={14}
                  />
                }
                label="Incoming"
                value={
                  selectedStats.incoming
                }
              />

              <InspectorRow
                icon={
                  <ArrowRight size={14} />
                }
                label="Outgoing"
                value={
                  selectedStats.outgoing
                }
              />

              <InspectorRow
                icon={
                  <TrendingUp size={14} />
                }
                label="Trade flows"
                value={
                  selectedTradeStats.tradeFlows
                }
              />

              <div className="atlas-inspector-divider" />

              <div className="atlas-inspector-section-title">
                <TrendingUp size={13} />
                SCENARIO STATE
              </div>

              {nodeScenarioLoading ? (
                <div className="atlas-scenario-box">
                  <div>
                    <span>
                      Backend simulation
                    </span>

                    <strong>
                      Loading…
                    </strong>
                  </div>
                </div>
              ) : nodeScenarioError ? (
                <div className="atlas-inspector-note">
                  Unable to load backend scenario:
                  {" "}
                  {nodeScenarioError}
                </div>
              ) : (
                <>
                  <div className="atlas-scenario-box">
                    <div>
                      <span>
                        Active paths
                      </span>

                      <strong>
                        {activePaths}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Deficit indicator
                      </span>

                      <strong>
                        {formatPercent(
                          cascadePressure
                        )}
                      </strong>
                    </div>
                  </div>

                  {backendImpact && (
                    <>
                      <InspectorRow
                        icon={
                          <TrendingUp size={14} />
                        }
                        label="Price pressure"
                        value={formatPercent(
                          backendImpact.price_pressure_percent
                        )}
                      />

                      <InspectorRow
                        icon={
                          <Database size={14} />
                        }
                        label="Baseline imports"
                        value={formatCurrency(
                          backendImpact.baseline_imports
                        )}
                      />

                      <InspectorRow
                        icon={
                          <ArrowDownRight size={14} />
                        }
                        label="Shock supply loss"
                        value={formatCurrency(
                          backendImpact.shock_supply_loss
                        )}
                      />

                      <InspectorRow
                        icon={
                          <Activity size={14} />
                        }
                        label="Risk"
                        value={
                          backendImpact.risk ||
                          "—"
                        }
                      />

                      <InspectorRow
                        icon={
                          <Activity size={14} />
                        }
                        label="Confidence"
                        value={formatPercent(
                          Number(
                            backendImpact.confidence
                          ) * 100
                        )}
                      />
                    </>
                  )}

                  {backendIntervention && (
                    <div className="atlas-inspector-note">
                      With +
                      {nodeScenario?.scenario
                        ?.alternate_supply_percent ??
                        10}
                      % alternate supply, the
                      modeled deficit indicator
                      changes from{" "}
                      {formatPercent(
                        backendImpact?.deficit_percent
                      )}{" "}
                      to{" "}
                      {formatPercent(
                        backendIntervention.deficit_percent
                      )}
                      .
                    </div>
                  )}

                  {isSourceNode ? (
                    <div className="atlas-inspector-note">
                      This node is one of the
                      production sources included
                      in the active shock scenario.
                    </div>
                  ) : directlyExposed ? (
                    <div className="atlas-inspector-note">
                      This node has a direct modeled
                      trade impact from the active
                      production shock.
                    </div>
                  ) : activePaths > 0 ? (
                    <div className="atlas-inspector-note">
                      This node appears in active
                      downstream pathways identified
                      by the backend graph traversal.
                    </div>
                  ) : (
                    <div className="atlas-inspector-note">
                      No active downstream scenario
                      pathway reaches this node within
                      the selected time horizon.
                    </div>
                  )}

                  {backendProvenance && (
                    <div className="atlas-inspector-note">
                      Model v
                      {backendProvenance.model_version ||
                        "—"}
                      . Scenario values are
                      deterministic model indicators,
                      not validated real-world
                      forecasts.
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </section>
  );
}

function LegendDot({
  color,
  label,
}) {
  return (
    <span className="atlas-legend-item">
      <i
        style={{
          background: color,
          boxShadow: `0 0 9px ${color}`,
        }}
      />

      {label}
    </span>
  );
}

function InspectorRow({
  icon,
  label,
  value,
}) {
  return (
    <div className="atlas-inspector-row">
      <span>
        {icon}
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}