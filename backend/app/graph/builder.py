from __future__ import annotations

from collections import defaultdict

import networkx as nx

from app.data.contracts import MetricType
from app.data.loaders import DATA_ROOT, load_comtrade_trade_csv, load_faostat_production_csv


def _normalize_node_id(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _read_fixture_graph() -> tuple[
    dict[str, float],
    dict[tuple[str, str], dict[str, float]],
    set[str],
]:
    production_bundle = load_faostat_production_csv(
        DATA_ROOT / "raw" / "faostat" / "wheat-production.csv"
    )
    trade_bundle = load_comtrade_trade_csv(
        DATA_ROOT / "raw" / "comtrade" / "wheat-global-trade.csv"
    )

    latest_by_country: dict[str, float] = {}
    for record in production_bundle.records:
        if record.metric == MetricType.PRODUCTION and record.notes is None:
            latest_by_country[_normalize_node_id(record.region_name)] = float(record.value)

    supplier_trade: dict[tuple[str, str], dict[str, float]] = {}
    for record in trade_bundle.records:
        if not record.flow or not record.partner_region or record.flow.lower() != "export":
            continue
        src = _normalize_node_id(record.region_name)
        dst = _normalize_node_id(record.partner_region)
        pair = supplier_trade.setdefault((src, dst), {"value_usd": 0.0, "quantity_kg": 0.0})
        if record.unit == "USD":
            pair["value_usd"] += float(record.value)
        elif record.unit == "kg":
            pair["quantity_kg"] += float(record.value)

    countries = set(latest_by_country)
    for record in trade_bundle.records:
        if record.partner_region:
            countries.add(_normalize_node_id(record.region_name))
            countries.add(_normalize_node_id(record.partner_region))
    return latest_by_country, supplier_trade, countries


def build_wheat_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("wheat", type="commodity", name="Wheat", role="global_commodity")
    graph.add_node("fertilizer", type="commodity", name="Fertilizer", role="input")
    graph.add_node("fuel", type="commodity", name="Fuel", role="input")
    graph.add_node("global_wheat_market", type="market", name="Global Wheat Market", role="global_market")
    graph.add_node("north_africa_food_market", type="market", name="North Africa Food Market", role="regional_market")
    graph.add_node("mediterranean_shipping", type="logistics", name="Mediterranean Shipping Network", role="shipping_route")
    graph.add_node("north_africa_port_network", type="logistics", name="North Africa Port Network", role="port_network")

    production_by_country, trade_by_pair, countries = _read_fixture_graph()
    for country_name in sorted(countries):
        graph.add_node(
            country_name,
            type="country",
            name=country_name.replace("_", " ").title(),
            role="producer",
            production=production_by_country.get(country_name, 0.0),
        )

    europe_nodes = {"france", "germany", "poland", "romania", "spain"}
    graph.add_node(
        "europe",
        type="region",
        name="Europe",
        production=sum(production_by_country.get(country, 0.0) for country in europe_nodes),
        exports=0.0,
        role="producer",
    )
    graph.add_edge(
        "europe", "wheat", relationship="PRODUCES", weight=1.0, order=1,
        propagation_delay_months=1, status="derived", source_dataset="FAOSTAT",
    )
    for country in europe_nodes:
        if country in graph:
            graph.add_edge(
                country, "wheat", relationship="PRODUCES", weight=1.0, order=1,
                propagation_delay_months=1, status="observed",
                source_dataset="FAOSTAT", reference_year=2024, unit="tonnes",
            )

    importer_totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"value_usd": 0.0, "quantity_kg": 0.0}
    )
    for (source, target), pair in trade_by_pair.items():
        importer_totals[target]["value_usd"] += pair["value_usd"]
        importer_totals[target]["quantity_kg"] += pair["quantity_kg"]

    for (source, target), pair in trade_by_pair.items():
        if source not in graph:
            graph.add_node(source, type="country", name=source.replace("_", " ").title(), role="producer")
        if target not in graph:
            graph.add_node(target, type="country", name=target.replace("_", " ").title(), role="importer")
        if target in {"egypt", "morocco", "algeria"}:
            graph.nodes[target]["imports"] = importer_totals[target]["quantity_kg"]
            graph.nodes[target]["imports_unit"] = "kg"
        total_imports = max(importer_totals[target]["quantity_kg"], 1.0)
        graph.add_edge(
            source,
            target,
            relationship="SUPPLIES_TO",
            weight=round(pair["quantity_kg"] / total_imports, 4),
            order=1,
            propagation_delay_months=1,
            source_dataset="UN Comtrade",
            reference_year=2024,
            commodity="wheat",
            trade_value_usd=round(pair["value_usd"], 2),
            trade_quantity_kg=round(pair["quantity_kg"], 2),
            unit="kg",
            status="observed",
        )

    for importer in ("egypt", "morocco", "algeria"):
        total_eu_exports = {
            "value_usd": sum(
                pair["value_usd"] for (source, target), pair in trade_by_pair.items()
                if source in europe_nodes and target == importer
            ),
            "quantity_kg": sum(
                pair["quantity_kg"] for (source, target), pair in trade_by_pair.items()
                if source in europe_nodes and target == importer
            ),
        }
        if total_eu_exports["quantity_kg"]:
            total_imports = max(importer_totals[importer]["quantity_kg"], 1.0)
            graph.add_edge(
                "europe", importer, relationship="SUPPLIES_TO",
                weight=round(total_eu_exports["quantity_kg"] / total_imports, 4),
                order=1, propagation_delay_months=1,
                source_dataset="FAOSTAT + UN Comtrade", commodity="wheat",
                reference_year=2024,
                trade_value_usd=round(total_eu_exports["value_usd"], 2),
                trade_quantity_kg=round(total_eu_exports["quantity_kg"], 2),
                unit="kg", status="derived",
                source_edges="country-level observed trade edges",
            )

    for importer in ("egypt", "morocco", "algeria"):
        if importer in graph:
            graph.add_edge(
                importer, "north_africa_food_market",
                relationship="AFFECTS_MARKET", weight=0.8, order=2,
                propagation_delay_months=1, status="provisional",
            )
    graph.add_edge(
        "wheat", "global_wheat_market", relationship="AFFECTS_MARKET",
        weight=0.8, order=2, propagation_delay_months=2, status="provisional",
    )
    graph.add_edge(
        "global_wheat_market", "north_africa_food_market",
        relationship="PRICE_TRANSMISSION", weight=0.55, order=3,
        propagation_delay_months=1, status="provisional",
    )
    graph.add_edge(
        "europe", "mediterranean_shipping", relationship="CONNECTS_ROUTE",
        weight=0.45, order=2, propagation_delay_months=1, status="provisional",
    )
    graph.add_edge(
        "mediterranean_shipping", "north_africa_port_network",
        relationship="CONNECTS_ROUTE", weight=0.7, order=2,
        propagation_delay_months=1, status="provisional",
    )
    graph.add_edge(
        "north_africa_port_network", "north_africa_food_market",
        relationship="AFFECTS_LOGISTICS", weight=0.6, order=3,
        propagation_delay_months=1, status="provisional",
    )
    return graph
