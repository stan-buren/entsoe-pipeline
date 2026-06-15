# Copyright 2026 Stanislav Burundukov
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Scratch script to repair and complete the ENTSO-E domains overview catalog.

This script updates and corrects the catalog entries to ensure compliance with
the template schema and structural sync with overview.yml.
"""

import copy

from ruamel.yaml import YAML


def main() -> None:
    """Load, repair, and dump the business context catalog."""
    yaml = YAML()
    yaml.width = 80
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True

    from pathlib import Path

    file_path = Path(
        "fms_metadata/business_context_catalog/entsoe_domains_overview_detailed.yml"
    )
    with file_path.open(encoding="utf-8") as f:
        data = yaml.load(f)

    domains = data["domains"]

    # 1. Fix ActualTotalLoad_6.1.A_r3 compliance typo and nesting
    load_section = domains["Load"]
    atl = load_section["ActualTotalLoad_6.1.A_r3"]
    if "compiance" in atl:
        atl["compliance"] = atl.pop("compiance")

    # Move unnested spec fields to technical_specification
    tech_spec = atl["technical_specification"]
    for field in [
        "parsing_key_feature",
        "parsing_technical_challenges",
        "data_quality_issues",
        "anomalies",
    ]:
        if field in atl:
            tech_spec[field] = atl.pop(field)

    # 2. Move Balancing items from Market to Balancing
    market_section = domains["Market"]
    balancing_section = domains["Balancing"]

    keys_to_move = [
        "PricesOfActivatedBalancingEnergy_17.1.F_r3",
        "ProcuredBalancingCapacity_12.3.F_r3",
        "TotalImbalanceVolumes_17.1.H_r3",
    ]
    for k in keys_to_move:
        if k in market_section:
            balancing_section[k] = market_section.pop(k)

    # 3. Handle duplicates with different suffixes/names
    # ProcuredBalancingCapacity_12.3.F_r3.1
    pbc_r3 = balancing_section["ProcuredBalancingCapacity_12.3.F_r3"]
    pbc_r31 = copy.deepcopy(pbc_r3)
    pbc_r31["title"] = "Procured Balancing Capacity [12.3.F]"
    pbc_r31["suffix"] = "r3.1"
    # Update deprecation warning in r3.1 description or anomalies
    balancing_section["ProcuredBalancingCapacity_12.3.F_r3.1"] = pbc_r31

    # RedispatchingInternal_13.1.A_r3
    ops_section = domains["Operations"]
    ri_r31 = ops_section["RedispatchingInternal_13.1.A_r3.1"]
    ri_r3 = copy.deepcopy(ri_r31)
    ri_r3["suffix"] = "r3"
    ops_section["RedispatchingInternal_13.1.A_r3"] = ri_r3

    # RedispatchingCrossBorder_13.1.A_r3
    rcb_r31 = ops_section["RedispatchingCrossBorder_13.1.A_r3.1"]
    rcb_r3 = copy.deepcopy(rcb_r31)
    rcb_r3["suffix"] = "r3"
    ops_section["RedispatchingCrossBorder_13.1.A_r3"] = rcb_r3

    # Countertrading_13.1.B_r3
    ct_r31 = ops_section["Countertrading_13.1.B_r3.1"]
    ct_r3 = copy.deepcopy(ct_r31)
    ct_r3["suffix"] = "r3"
    ops_section["Countertrading_13.1.B_r3"] = ct_r3

    # OtherMarketInformation_r3
    omi_section = domains["OtherMarketInformation"]
    omi_r31 = omi_section["OtherMarketInformation_r3.1"]
    omi_r3 = copy.deepcopy(omi_r31)
    omi_r3["suffix"] = "r3"
    omi_section["OtherMarketInformation_r3"] = omi_r3

    # Export_log_r3.csv and Export_oce_log_r3.csv
    el = omi_section.pop("Export_log_r3")
    omi_section["Export_log_r3.csv"] = el

    eol = omi_section.pop("Export_oce_log_r3")
    omi_section["Export_oce_log_r3.csv"] = eol

    # 4. Insert stubs for genuinely missing extracts
    # Load: YearAheadForecastMargin_8.1_r3
    load_section["YearAheadForecastMargin_8.1_r3"] = {
        "title": "Year Ahead Forecast Margin [8.1]",
        "oneliner": (
            "Year-ahead forecast of the margin between available generation "
            "capacity and expected demand."
        ),
        "description": (
            "This dataset contains the year-ahead forecast of the margin between "
            "the available generation capacity and the expected peak demand on the "
            "power system."
        ),
        "compliance": "Article 8.1 of EU Regulation No 543/2013.",
        "suffix": "r3",
        "physical_meaning": (
            "Represents the power system resource adequacy margin in megawatts (MW) "
            "forecasted for the upcoming year."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": "Provided as yearly extracts in the File Library.",
            "time_resolution": "One year (P1Y).",
            "required_columns": (
                "Year, AreaCode, AreaDisplayName, MapCode, Margin[MW], UpdateTime(UTC)"
            ),
            "parsing_key_feature": "Contains the forecasted margin value at a macroscopic system level.",
            "parsing_technical_challenges": (
                "Data needs to be filtered by AreaTypeCode to ensure correct "
                "geographical scoping."
            ),
            "data_quality_issues": (
                "Subject to high forecast uncertainty and variations in TSO "
                "methodologies."
            ),
            "anomalies": {
                "Methodological_Differences": (
                    "TSOs may apply different criteria for estimating available "
                    "capacity and peak load."
                )
            },
        },
    }

    # Generation: InstalledGenerationCapacityAggregated_14.1.A_r3
    gen_section = domains["Generation"]
    gen_section["InstalledGenerationCapacityAggregated_14.1.A_r3"] = {
        "title": "Installed Generation Capacity Aggregated [14.1.A]",
        "oneliner": "Aggregated installed generation capacity by production type.",
        "description": (
            "This dataset provides the aggregated installed generation capacity in "
            "megawatts (MW) for all generation units, classified by production type "
            "(e.g. Wind, Solar, Gas, Coal, Nuclear)."
        ),
        "compliance": "Article 14.1.A of EU Regulation No 543/2013.",
        "suffix": "r3",
        "physical_meaning": (
            "Represents the total net generating capacity of all power plants "
            "connected to the transmission or distribution grids."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": "Provided as yearly extracts in the File Library.",
            "time_resolution": "Yearly timeframe.",
            "required_columns": (
                "Year, AreaCode, AreaDisplayName, ProductionType, InstalledCapacity[MW]"
            ),
            "parsing_key_feature": "Data is aggregated per fuel/technology type rather than individual units.",
            "parsing_technical_challenges": (
                "Ensure to filter by AreaTypeCode to avoid double counting "
                "country and control area levels."
            ),
            "data_quality_issues": (
                "Delays in TSOs updating installed capacity figures following unit "
                "retirements or new additions."
            ),
            "anomalies": {
                "Delayed_Updates": (
                    "Retirements and new grid connections may not be immediately "
                    "reflected."
                )
            },
        },
    }

    # Transmission: PowerTransferDistributionFactors_11.1.B_r3
    trans_section = domains["Transmission"]
    trans_section["PowerTransferDistributionFactors_11.1.B_r3"] = {
        "title": "Power Transfer Distribution Factors [11.1.B]",
        "oneliner": (
            "Flow-based Power Transfer Distribution Factors (PTDFs) for capacity "
            "allocation."
        ),
        "description": (
            "This dataset contains the Power Transfer Distribution Factors (PTDFs) "
            "and Remaining Available Margin (RAM) parameters used in the flow-based "
            "capacity allocation methodology."
        ),
        "compliance": "Article 11.1.B of EU Regulation No 543/2013.",
        "suffix": "r3",
        "physical_meaning": (
            "PTDFs represent the sensitivity of physical flows on critical network "
            "elements (CNECs) to commercial exchanges between bidding zones."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": (
                "Provided as daily or monthly extracts in the File Library."
            ),
            "time_resolution": "Market Time Unit (MTU) resolution.",
            "required_columns": "DateTime(UTC), CNEC_Name, PTDF_Values, Margin",
            "parsing_key_feature": "Core input to the flow-based market coupling algorithm.",
            "parsing_technical_challenges": "Extremely high volume of matrix-like mathematical parameters.",
            "data_quality_issues": (
                "Highly complex mathematical representation that requires "
                "specialized domain knowledge to validate."
            ),
            "anomalies": {
                "High_Granularity_Volume": (
                    "The large size of these datasets requires efficient columnar "
                    "storage to query."
                )
            },
        },
    }

    # Outages: UnavailabilityInTheTransmissionGridAffectedAssets_10.1.A_B_r3
    out_section = domains["Outages"]
    out_section["UnavailabilityInTheTransmissionGridAffectedAssets_10.1.A_B_r3"] = {
        "title": (
            "Unavailability in the Transmission Grid - Affected Assets [10.1.A/B]"
        ),
        "oneliner": (
            "Details of specific transmission assets affected by planned or "
            "unplanned outages."
        ),
        "description": (
            "This dataset details the specific transmission lines, transformers, "
            "and sub-stations affected by planned or unplanned outages."
        ),
        "compliance": "Articles 10.1.A and 10.1.B of EU Regulation No 543/2013.",
        "suffix": "r3",
        "physical_meaning": (
            "Identifies physical assets out of service and their nominal and "
            "remaining capacities."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": "Provided as monthly extracts in the File Library.",
            "time_resolution": "Event-driven outage intervals.",
            "required_columns": (
                "OutageID, AssetName, AssetCode, NominalCapacity, OutageStart, "
                "OutageEnd"
            ),
            "parsing_key_feature": "Tracks asset-level outage lifecycles.",
            "parsing_technical_challenges": (
                "Requires joining with Affected Areas dataset to determine "
                "market impact."
            ),
            "data_quality_issues": (
                "TSOs may update outage durations dynamically, generating "
                "multiple revisions."
            ),
            "anomalies": {
                "Dynamic_Revisions": (
                    "Outage schedules are subject to constant updates as grid "
                    "maintenance proceeds."
                )
            },
        },
    }

    # Outages: UnavailabilityInTheTransmissionGridAffectedAreas_10.1.A_B_r3
    out_section["UnavailabilityInTheTransmissionGridAffectedAreas_10.1.A_B_r3"] = {
        "title": (
            "Unavailability in the Transmission Grid - Affected Areas [10.1.A/B]"
        ),
        "oneliner": (
            "Details of geographical areas affected by transmission asset outages."
        ),
        "description": (
            "This dataset specifies the geographical bidding zones and control areas "
            "affected by transmission grid outages, including the impact on "
            "transfer capacities."
        ),
        "compliance": "Articles 10.1.A and 10.1.B of EU Regulation No 543/2013.",
        "suffix": "r3",
        "physical_meaning": (
            "Quantifies the reduction in cross-border transmission capacity caused "
            "by grid outages."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": "Provided as monthly extracts in the File Library.",
            "time_resolution": "Event-driven outage intervals.",
            "required_columns": (
                "OutageID, OutAreaCode, InAreaCode, ReductionInCapacity[MW]"
            ),
            "parsing_key_feature": (
                "Directly links grid asset outages to cross-border trading limits."
            ),
            "parsing_technical_challenges": (
                "Must be joined on OutageID with the Affected Assets dataset."
            ),
            "data_quality_issues": (
                "TSOs may report capacity reductions as absolute values or "
                "percentage limits depending on the border."
            ),
            "anomalies": {
                "Capacity_Definition_Discrepancies": (
                    "Different borders may report reduction values using "
                    "inconsistent physical definitions."
                )
            },
        },
    }

    # Operations: ExchangedVolumesAndPricesProvidedByActivationOptimisationFunction_IFs_aFRR3.16_r3
    ops_section[
        "ExchangedVolumesAndPricesProvidedByActivationOptimisationFunction_IFs_aFRR3.16_r3"
    ] = {
        "title": (
            "Exchanged Volumes and Prices - aFRR Optimisation Function [aFRR 3.16]"
        ),
        "oneliner": (
            "Exchanged volumes and clearing prices of the automatic Frequency "
            "Restoration Reserve."
        ),
        "description": (
            "This dataset contains the actual exchanged volumes and marginal clearing "
            "prices calculated by the PICASSO activation optimization function."
        ),
        "compliance": (
            "Article 3.16 of the Implementation Framework for the aFRR platform "
            "(PICASSO)."
        ),
        "suffix": "r3",
        "physical_meaning": (
            "Represents the physical cross-border exchange of automatic Frequency "
            "Restoration Reserve (aFRR) energy and its marginal clearing price."
        ),
        "technical_specification": {
            "format_and_frequency_of_extracts": "Provided as monthly extracts in the File Library.",
            "time_resolution": "aFRR Optimization Cycle.",
            "required_columns": "DateTime(UTC), OutAreaCode, InAreaCode, ExchangedVolume[MW], Price",
            "parsing_key_feature": "Extremely high-frequency activation telemetry.",
            "parsing_technical_challenges": "Extremely large volume of records due to sub-minute resolution.",
            "data_quality_issues": (
                "Requires significant aggregation and filtering to match standard "
                "15-minute imbalance settlement periods."
            ),
            "anomalies": {
                "Volume_Noise": (
                    "Sub-minute frequency measurements can exhibit high "
                    "volatility and numeric noise."
                )
            },
        },
    }

    # Write the modified data back to the file
    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    print("Catalog successfully corrected and formatted.")


if __name__ == "__main__":
    main()
