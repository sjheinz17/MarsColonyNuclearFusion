from __future__ import annotations
# Cost and resource classification helpers for the fusion comparison.
# This file backs the parts of the report that ask when fusion starts to look
# believable and how its cost stacks up against solar and fission.

import pandas as pd

from mars_power.common import BASE_LAUNCH_COST_PER_KG, load_fusion_specs, load_nuclear_capacity


def classify_resource(certainty: float, commerciality: float) -> str:
    if certainty >= 0.5 and commerciality >= 0.5:
        return "Proved Reserve"
    if certainty >= 0.5 or commerciality >= 0.5:
        return "Prospective Resource"
    return "Contingent Resource"


def build_resource_classification() -> pd.DataFrame:
    fusion = load_fusion_specs()
    nuclear = load_nuclear_capacity()

    rows = [
        {
            "source": "Solar PV",
            "category": "Prospective Resource",
            "certainty_of_existence": 0.95,
            "chance_of_commerciality": 0.40,
            "net_power_kw": 50,
            "notes": "Sunlight is certain but dust, night, and storms cut usable output.",
        },
        {
            "source": "Fission (Kilopower-class)",
            "category": "Proved Reserve",
            "certainty_of_existence": 0.99,
            "chance_of_commerciality": 0.92,
            "net_power_kw": 40,
            "notes": f"EIA fleet average capacity factor: {nuclear['Capacity Factor'].iloc[-1]}",
        },
    ]

    fusion_inputs = [
        (0, 0.70, 0.25),
        (1, 0.50, 0.15),
        (2, 0.30, 0.10),
    ]
    # These scores are the simple judgment calls behind the McKelvey style plot.
    for index, certainty, commerciality in fusion_inputs:
        source = fusion.iloc[index]
        rows.append(
            {
                "source": source["reactor"],
                "category": "Contingent Resource",
                "certainty_of_existence": certainty,
                "chance_of_commerciality": commerciality,
                "net_power_kw": float(source["net_electric_mw"]) * 1000,
                "notes": f"TRL {source['trl']}, Q={source['plasma_gain_Q']}",
            }
        )

    return pd.DataFrame(rows)


def base_cost_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source": "Solar PV",
                "unit_power_kw": 50,
                "hardware_mass_kg": 2500,
                "deployment_mass_kg": 500,
                "capex_earth_M": 5,
                "annual_opex_M": 0.2,
                "lifetime_years": 15,
                "capacity_factor": 0.25,
                "notes": "Dust losses and long nights keep the capacity factor low.",
            },
            {
                "source": "Fission (Kilopower-class)",
                "unit_power_kw": 40,
                "hardware_mass_kg": 1500,
                "deployment_mass_kg": 300,
                "capex_earth_M": 30,
                "annual_opex_M": 0.5,
                "lifetime_years": 15,
                "capacity_factor": 0.92,
                "notes": "Modeled as a high availability baseload source.",
            },
            {
                "source": "CFS SPARC",
                "unit_power_kw": 50000,
                "hardware_mass_kg": 100000,
                "deployment_mass_kg": 20000,
                "capex_earth_M": 5000,
                "annual_opex_M": 50,
                "lifetime_years": 30,
                "capacity_factor": 0.80,
                "notes": "Large tokamak concept with high mass and strong scale.",
            },
            {
                "source": "Princeton FRC",
                "unit_power_kw": 2500,
                "hardware_mass_kg": 5000,
                "deployment_mass_kg": 1000,
                "capex_earth_M": 500,
                "annual_opex_M": 10,
                "lifetime_years": 20,
                "capacity_factor": 0.75,
                "notes": "Compact concept with midrange size and cost.",
            },
            {
                "source": "Avalanche Orbitron",
                "unit_power_kw": 500,
                "hardware_mass_kg": 500,
                "deployment_mass_kg": 100,
                "capex_earth_M": 100,
                "annual_opex_M": 2,
                "lifetime_years": 20,
                "capacity_factor": 0.70,
                "notes": "Smallest concept, but still low TRL.",
            },
        ]
    )


def apply_launch_cost(
    costs: pd.DataFrame | None = None,
    launch_cost_per_kg: float = BASE_LAUNCH_COST_PER_KG,
) -> pd.DataFrame:
    table = base_cost_table() if costs is None else costs.copy()
    # We count launch mass here because it is part of the actual Mars deployment cost.
    table["launch_cost_M"] = (
        (table["hardware_mass_kg"] + table["deployment_mass_kg"]) * launch_cost_per_kg / 1e6
    )
    table["total_capex_M"] = table["capex_earth_M"] + table["launch_cost_M"]
    table["lifetime_energy_MWh"] = (
        table["unit_power_kw"] * table["capacity_factor"] * 8760 * table["lifetime_years"] / 1000
    )
    total_cost_M = table["total_capex_M"] + table["annual_opex_M"] * table["lifetime_years"]
    table["lcoe_dollar_per_MWh"] = total_cost_M * 1e6 / table["lifetime_energy_MWh"]
    table["lcoe_dollar_per_kWh"] = table["lcoe_dollar_per_MWh"] / 1000
    return table
