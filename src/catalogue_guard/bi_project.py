import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pyarrow as pa
import pyarrow.parquet as pq

from .bi_export import QUERIES, RELATIONSHIPS, export_tables

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
MEASURES = {
    "Catalogue products": (
        "CALCULATE(COUNTROWS(DimProduct), DimProduct[InProductCatalogue] = TRUE())",
        "#,0",
    ),
    "Products with prices": (
        "CALCULATE([Catalogue products], DimProduct[HasObservedPrice] = TRUE())",
        "#,0",
    ),
    "Price coverage": ("DIVIDE([Products with prices], [Catalogue products])", "0.00%"),
    "Products with recall candidates": (
        "CALCULATE([Catalogue products], DimProduct[HasRecallCandidate] = TRUE())",
        "#,0",
    ),
    "Recall coverage": ("DIVIDE([Products with recall candidates], [Catalogue products])", "0.00%"),
    "Missing product names": (
        "CALCULATE([Catalogue products], DimProduct[MissingName] = TRUE())",
        "#,0",
    ),
    "Missing name share": ("DIVIDE([Missing product names], [Catalogue products])", "0.00%"),
    "All three sources": (
        "CALCULATE([Catalogue products], DimProduct[HasObservedPrice] = TRUE(), DimProduct[HasRecallCandidate] = TRUE())",
        "#,0",
    ),
    "Price observations": ("COUNTROWS(FactPrice)", "#,0"),
    "Historical notices": ("COUNTROWS(DimNotice)", "#,0"),
    "Candidate links": ("COUNTROWS(FactRecallLink)", "#,0"),
    "Linked notices": ("DISTINCTCOUNT(FactRecallLink[NoticeId])", "#,0"),
    "Candidate product codes": ("DISTINCTCOUNT(FactRecallLink[ProductCode])", "#,0"),
    "Description review links": (
        "CALCULATE([Candidate links], FactRecallLink[DescriptionReviewFlag] = TRUE())",
        "#,0",
    ),
    "Observed stores": (
        "CALCULATE(DISTINCTCOUNT(FactPrice[LocationId]), FactPrice[LocationId] <> -1)",
        "#,0",
    ),
    "Median comparable price": (
        "IF(CALCULATE(HASONEVALUE(FactPrice[ProductCode]) && HASONEVALUE(FactPrice[Currency]) && HASONEVALUE(FactPrice[PriceUnit]), ALLSELECTED(DimPriceDate), ALLSELECTED(DimLocation)), MEDIAN(FactPrice[ObservedPrice]), BLANK())",
        "0.00",
    ),
    "Price selection guidance": (
        'IF(CALCULATE(HASONEVALUE(FactPrice[ProductCode]) && HASONEVALUE(FactPrice[Currency]) && HASONEVALUE(FactPrice[PriceUnit]), ALLSELECTED(DimPriceDate), ALLSELECTED(DimLocation)), "Same code, currency and reported unit. Packaging changes remain unresolved.", "Select ONE product code, currency and price unit to view a median.")',
        None,
    ),
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def literal(value):
    encoded = (
        "'" + value.replace("'", "''") + "'"
        if isinstance(value, str)
        else (str(value).lower() if isinstance(value, bool) else f"{value}D")
    )
    return {"expr": {"Literal": {"Value": encoded}}}


def color(value):
    return {"solid": {"color": literal(value)}}


def projection(table, column, measure=False):
    field = {
        "Measure" if measure else "Column": {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": column,
        }
    }
    return {"field": field, "queryRef": f"{table}.{column}", "nativeQueryRef": column}


def tabular_type(field):
    if pa.types.is_boolean(field.type):
        return "boolean"
    if pa.types.is_integer(field.type):
        return "int64"
    if pa.types.is_floating(field.type):
        return "double"
    if pa.types.is_date(field.type) or pa.types.is_timestamp(field.type):
        return "dateTime"
    return "string"


def create_model(root, data_directory):
    tables = []
    for name in QUERIES:
        columns = []
        for field in pq.read_schema(root / "data" / f"{name}.parquet"):
            kind = tabular_type(field)
            column = {
                "name": field.name,
                "dataType": kind,
                "sourceColumn": field.name,
                "summarizeBy": "none",
            }
            if kind == "dateTime":
                column["formatString"] = "MMM yyyy" if field.name == "MonthStart" else "yyyy-MM-dd"
            if field.name == "SourceURL":
                column["dataCategory"] = "WebUrl"
            columns.append(column)
        expression = f'let Source = Parquet.Document(File.Contents(DataFolder & "/{name}.parquet")) in Source'
        table = {
            "name": name,
            "columns": columns,
            "partitions": [
                {"name": name, "mode": "import", "source": {"type": "m", "expression": expression}}
            ],
        }
        if name == "DimProduct":
            table["measures"] = [
                {"name": key, "expression": expr, **({"formatString": fmt} if fmt else {})}
                for key, (expr, fmt) in MEASURES.items()
            ]
        tables.append(table)
    model = {
        "compatibilityLevel": 1606,
        "model": {
            "culture": "en-US",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"}],
            "expressions": [
                {
                    "name": "DataFolder",
                    "kind": "m",
                    "expression": '"'
                    + data_directory.replace('"', '""')
                    + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
                }
            ],
            "tables": tables,
            "relationships": [
                {
                    "name": str(uuid4()),
                    "fromTable": fact,
                    "fromColumn": foreign,
                    "toTable": dim,
                    "toColumn": key,
                    "crossFilteringBehavior": "oneDirection",
                }
                for fact, foreign, dim, key in RELATIONSHIPS
            ],
        },
    }
    write_json(root / "Catalogue.SemanticModel" / "model.bim", model)
    write_json(
        root / "Catalogue.SemanticModel" / "definition.pbism", {"version": "4.2", "settings": {}}
    )


def create_report(root, scope, snapshot_date):
    report = root / "Catalogue.Report"
    definition = report / "definition"
    write_json(
        root / "Retail Catalogue Guard.pbip",
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": "Catalogue.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write_json(
        report / "definition.pbir",
        {"version": "4.0", "datasetReference": {"byPath": {"path": "../Catalogue.SemanticModel"}}},
    )
    write_json(
        definition / "version.json",
        {"$schema": SCHEMA + "versionMetadata/1.0.0/schema.json", "version": "2.0.0"},
    )
    write_json(
        definition / "report.json",
        {"$schema": SCHEMA + "report/3.0.0/schema.json", "themeCollection": {}},
    )
    pages = [
        ("coverage", "01 Catalogue coverage"),
        ("recalls", "02 Historical recall evidence"),
        ("prices", "03 Price observations"),
    ]
    write_json(
        definition / "pages" / "pages.json",
        {
            "$schema": SCHEMA + "pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p[0] for p in pages],
            "activePageName": "coverage",
        },
    )

    def visual(page, kind, title, x, y, width, height, roles=None, objects=None):
        name = uuid5(NAMESPACE_URL, f"{page}/{kind}/{title}/{x}/{y}").hex[:20]
        value = {
            "$schema": SCHEMA + "visualContainer/2.9.0/schema.json",
            "name": name,
            "position": {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "z": y + x,
                "tabOrder": y + x,
            },
            "visual": {
                "visualType": kind,
                "drillFilterOtherVisuals": True,
                "visualContainerObjects": {
                    "title": [
                        {
                            "properties": {
                                "show": literal(bool(title)),
                                "text": literal(title),
                                "fontSize": literal(12),
                                "fontColor": color("#163D32"),
                            }
                        }
                    ],
                    "background": [
                        {
                            "properties": {
                                "show": literal(True),
                                "color": color("#FFFFFF"),
                                "transparency": literal(0),
                            }
                        }
                    ],
                },
            },
        }
        if roles:
            value["visual"]["query"] = {
                "queryState": {role: {"projections": fields} for role, fields in roles.items()}
            }
        if kind == "clusteredBarChart":
            value["visual"]["query"]["sortDefinition"] = {
                "sort": [{"field": roles["Y"][0]["field"], "direction": "Descending"}],
                "isDefaultSort": True,
            }
        if kind in {"lineChart", "clusteredBarChart"}:
            objects = {
                **(objects or {}),
                **{
                    axis: [{"properties": {"fontSize": literal(12)}}]
                    for axis in ("categoryAxis", "valueAxis")
                },
            }
        if kind == "lineChart":
            objects = {
                **(objects or {}),
                "categoryAxis": [
                    {"properties": {"axisType": literal("Scalar"), "fontSize": literal(12)}}
                ],
            }
        if kind == "card":
            objects = {
                **(objects or {}),
                "categoryLabels": [{"properties": {"show": literal(False)}}],
            }
        if objects:
            value["visual"]["objects"] = objects
        write_json(definition / "pages" / page / "visuals" / name / "visual.json", value)

    def text(page, text, y, size=11, height=38):
        visual(
            page,
            "textbox",
            "",
            24,
            y,
            1232,
            height,
            objects={
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": text,
                                            "textStyle": {
                                                "fontFamily": "Segoe UI",
                                                "fontSize": f"{size}pt",
                                                "color": "#163D32",
                                            },
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
        )

    def card(page, measure, x, y=118, width=292):
        visual(
            page,
            "card",
            measure,
            x,
            y,
            width,
            105,
            {"Values": [projection("DimProduct", measure, True)]},
            {
                "labels": [
                    {
                        "properties": {
                            "fontSize": literal(29),
                            "color": color("#176448"),
                            "labelDisplayUnits": literal(1),
                        }
                    }
                ]
            },
        )

    for page, title in pages:
        write_json(
            definition / "pages" / page / "page.json",
            {
                "$schema": SCHEMA + "page/2.1.0/schema.json",
                "name": page,
                "displayName": title,
                "displayOption": "FitToPage",
                "width": 1280,
                "height": 800,
            },
        )
        text(page, title + "  |  " + scope.upper() + " SNAPSHOT", 12, 24, 58)
        text(
            page,
            f"Open Food Facts + Open Prices + RappelConso | Built {snapshot_date} | Independent data-quality project",
            66,
        )

    for i, metric in enumerate(
        ["Catalogue products", "Price coverage", "Recall coverage", "Missing name share"]
    ):
        card("coverage", metric, 24 + 310 * i)
    visual(
        "coverage",
        "clusteredBarChart",
        "Catalogue records by evidence coverage",
        24,
        245,
        760,
        385,
        {
            "Category": [projection("DimProduct", "CoverageGroup")],
            "Y": [projection("DimProduct", "Catalogue products", True)],
        },
    )
    card("coverage", "All three sources", 810, 260, 440)
    card("coverage", "Missing product names", 810, 390, 440)
    text(
        "coverage",
        "Decision: identify catalogue gaps before relying on an external match. Large source volume does not mean complete coverage.",
        663,
    )
    text(
        "coverage",
        "The product catalogue is global; recall evidence is French. Coverage percentages are matching coverage, NOT product risk rates.",
        715,
    )

    for i, metric in enumerate(
        [
            "Historical notices",
            "Linked notices",
            "Candidate product codes",
            "Description review links",
        ]
    ):
        card("recalls", metric, 24 + 310 * i)
    visual(
        "recalls",
        "clusteredBarChart",
        "Historical food notices by category",
        24,
        245,
        608,
        350,
        {
            "Category": [projection("DimNotice", "Category")],
            "Y": [projection("DimProduct", "Historical notices", True)],
        },
    )
    visual(
        "recalls",
        "lineChart",
        "Publication history — not a risk trend",
        656,
        245,
        600,
        350,
        {
            "Category": [projection("DimRecallDate", "MonthStart")],
            "Y": [projection("DimProduct", "Historical notices", True)],
        },
    )
    text(
        "recalls",
        "A notice can name several products. Count notices and product-code links separately. Batch applicability requires the original notice.",
        631,
    )
    text(
        "recalls",
        "Categories are translated into English. Source product names, reasons and batch text remain unchanged for traceability.",
        686,
    )
    text(
        "recalls",
        "Description review uses disjoint words. Translation and spelling differences can trigger it; it is not a confirmed mismatch.",
        735,
    )

    for i, (table, field) in enumerate(
        [("DimProduct", "ProductCode"), ("FactPrice", "Currency"), ("FactPrice", "PriceUnit")]
    ):
        visual(
            "prices",
            "slicer",
            field,
            24 + i * 414,
            115,
            394,
            85,
            {"Values": [projection(table, field)]},
            {
                "data": [{"properties": {"mode": literal("Dropdown")}}],
                "general": [{"properties": {"selfFilterEnabled": literal(True)}}],
            },
        )
    card("prices", "Price observations", 24, 220, 380)
    card("prices", "Observed stores", 438, 220, 380)
    card("prices", "Median comparable price", 852, 220, 404)
    visual(
        "prices",
        "lineChart",
        "Monthly median — choose one code, currency and unit",
        24,
        353,
        800,
        325,
        {
            "Category": [projection("DimPriceDate", "MonthStart")],
            "Y": [projection("DimProduct", "Median comparable price", True)],
        },
    )
    visual(
        "prices",
        "clusteredBarChart",
        "Observation coverage by country",
        845,
        353,
        410,
        325,
        {
            "Category": [projection("DimLocation", "CountryCode")],
            "Y": [projection("DimProduct", "Price observations", True)],
        },
    )
    text(
        "prices",
        "Median intentionally stays blank across different products, currencies or units. Prices are observations, not sales or revenue.",
        712,
    )
    text(
        "prices",
        "Filter example: product code 03415581571110, EUR, Unspecified. Packaging and promotional changes still need review.",
        754,
    )


def build_powerbi(database, destination, portable=False):
    root = Path(destination).resolve()
    manifest = export_tables(database, root / "data")
    data_directory = "C:/RetailCatalogueGuard/data" if portable else (root / "data").as_posix()
    create_model(root, data_directory)
    create_report(root, manifest["source_scope"], manifest["source_built_at"][:10])
    (root / "measures.dax").write_text(
        "\n\n".join(f"{name} =\n{expr}" for name, (expr, _) in MEASURES.items()), encoding="utf-8"
    )
    return manifest
