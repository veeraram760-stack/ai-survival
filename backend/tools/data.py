"""
Data analysis and processing tools for agents
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from .base import Tool, tool_registry
from ..execution.llm_providers import get_llm_provider
import logging

logger = logging.getLogger("ai_survival.tools.data")


class DataAnalysisTool(Tool):
    """Analyze data and generate insights"""

    def __init__(self):
        super().__init__(
            name="analyze_data",
            description="Analyze datasets and generate insights using Python/pandas",
            cost=0.005,
        )

    async def execute(
        self,
        data: List[Dict[str, Any]],
        analysis_type: str = "summary",
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze data"""

        try:
            df = pd.DataFrame(data)

            if analysis_type == "summary":
                result = {
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "missing": df.isnull().sum().to_dict(),
                    "numeric_summary": df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {},
                }
            elif analysis_type == "correlation":
                numeric_df = df.select_dtypes(include=[np.number])
                if len(numeric_df.columns) > 1:
                    result = {"correlation": numeric_df.corr().to_dict()}
                else:
                    result = {"error": "Not enough numeric columns for correlation"}
            elif analysis_type == "groupby":
                group_col = kwargs.get("group_by")
                agg_col = kwargs.get("aggregate")
                if group_col and agg_col:
                    result = {"grouped": df.groupby(group_col)[agg_col].mean().to_dict()}
                else:
                    result = {"error": "group_by and aggregate columns required"}
            else:
                result = {"error": f"Unknown analysis type: {analysis_type}"}

            return {"status": "success", "analysis": result}
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return {"status": "failed", "error": str(e)}


class CSVImportTool(Tool):
    """Import and process CSV files"""

    def __init__(self):
        super().__init__(
            name="import_csv",
            description="Import and parse CSV data from file or URL",
            cost=0.001,
        )

    async def execute(
        self,
        source: str,
        source_type: str = "file",
        **kwargs
    ) -> Dict[str, Any]:
        """Import CSV data"""

        try:
            if source_type == "file":
                df = pd.read_csv(source)
            elif source_type == "url":
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(source)
                    response.raise_for_status()
                    from io import StringIO
                    df = pd.read_csv(StringIO(response.text))
            else:
                return {"status": "failed", "error": "source_type must be 'file' or 'url'"}

            return {
                "status": "success",
                "shape": df.shape,
                "columns": list(df.columns),
                "sample": df.head(10).to_dict("records"),
                "dtypes": df.dtypes.astype(str).to_dict(),
            }
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return {"status": "failed", "error": str(e)}


class ChartGenerationTool(Tool):
    """Generate charts and visualizations"""

    def __init__(self):
        super().__init__(
            name="generate_chart",
            description="Generate charts and visualizations from data",
            cost=0.01,
        )

    async def execute(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        x_column: str,
        y_column: str,
        title: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chart specification (Vega-Lite)"""

        try:
            # Return Vega-Lite spec that can be rendered by frontend
            spec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": {"values": data},
                "mark": chart_type,
                "encoding": {
                    "x": {"field": x_column, "type": "quantitative" if chart_type != "bar" else "nominal"},
                    "y": {"field": y_column, "type": "quantitative"},
                },
            }
            if title:
                spec["title"] = title

            return {
                "status": "success",
                "chart_spec": spec,
                "chart_type": chart_type,
            }
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return {"status": "failed", "error": str(e)}


class SQLQueryTool(Tool):
    """Execute SQL queries against databases"""

    def __init__(self):
        super().__init__(
            name="sql_query",
            description="Execute SQL queries against connected databases",
            cost=0.002,
        )
        # Database connections would be configured here
        self.connections = {}

    async def execute(
        self,
        query: str,
        connection: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute SQL query"""

        # In production, this would connect to actual databases
        # For now, return structure for async execution
        return {
            "status": "success",
            "query": query,
            "connection": connection,
            "note": "SQL execution requires configured database connections",
            "mock_result": {
                "columns": [],
                "rows": [],
                "row_count": 0,
            },
        }


class ReportGenerationTool(Tool):
    """Generate automated reports"""

    def __init__(self):
        super().__init__(
            name="generate_report",
            description="Generate formatted reports from data and analysis",
            cost=0.02,
        )
        self.llm = get_llm_provider()

    async def execute(
        self,
        data: List[Dict[str, Any]],
        report_type: str = "summary",
        template: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate report"""

        prompt = f"""
Generate a {report_type} report from this data:
{data[:5]}...

Include: executive summary, key findings, data highlights, recommendations.
Format as markdown.
"""

        result = await self.llm.generate(prompt, max_tokens=3000, temperature=0.5)

        if result["status"] == "success":
            return {
                "status": "success",
                "report_type": report_type,
                "report": result["output"],
                "format": "markdown",
            }
        return result


# Register tools
tool_registry.register(DataAnalysisTool())
tool_registry.register(CSVImportTool())
tool_registry.register(ChartGenerationTool())
tool_registry.register(SQLQueryTool())
tool_registry.register(ReportGenerationTool())