import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Set, Dict, Optional
from collections import defaultdict

from src.models import ChartResponse, ChartDataset, ChartDefinition

logger = logging.getLogger(__name__)


class ChartGenerator(ABC):
    """Abstract base class for all diagram generators."""

    @abstractmethod
    def generate(self,
                 unique_labels: List[str],
                 values_data: List[Tuple[Any, float, Any]],
                 chart_definition: ChartDefinition) -> ChartResponse:
        """Generates data for a diagram of a specific type."""
        pass

    def _aggregate_values_for_label(self,
                                    unique_labels: List[str],
                                    values_data: List[Tuple[Any, float, Any]]) -> List[float]:
        """Aggregates values for unique labels."""
        aggregated = defaultdict(float)

        for label, value, _ in values_data:
            if label is not None:
                aggregated[label] += value

        # Return values in the same order as labels
        return [aggregated.get(label, 0) for label in unique_labels]

    def _aggregate_values_for_series(self,
                                     unique_labels: List[str],
                                     values_data: List[Tuple[Any, float, Any]],
                                     series: Any) -> List[float]:
        """Aggregates values for a specific series by label."""
        aggregated = defaultdict(float)

        for label, value, s in values_data:
            if label is not None and s == series:
                aggregated[label] += value

        return [aggregated.get(label, 0) for label in unique_labels]


class SimpleChartGenerator(ChartGenerator):
    """Data generator for simple charts (pie, bar, line)."""

    def generate(self,
                 unique_labels: List[str],
                 values_data: List[Tuple[Any, float, Any]],
                 chart_definition: ChartDefinition) -> ChartResponse:
        aggregated_values = self._aggregate_values_for_label(unique_labels, values_data)

        datasets = [ChartDataset(label="Data", data=aggregated_values)]

        return ChartResponse(
            chartType=chart_definition.chart_type,
            title=chart_definition.title,
            labels=[str(label) for label in unique_labels],
            datasets=datasets
        )


class AdvancedChartGenerator(ChartGenerator):
    """Data generator for advanced charts with series (stacked bar)."""

    def generate(self,
                 unique_labels: List[str],
                 values_data: List[Tuple[Any, float, Any]],
                 chart_definition: ChartDefinition) -> ChartResponse:

        # Check if series_field is specified
        if not chart_definition.series_field:
            logger.warning(f"No series_field parameter specified for {chart_definition.chart_type} chart")
            # Return a simple chart if series_field is missing
            aggregated_values = self._aggregate_values_for_label(unique_labels, values_data)
            datasets = [ChartDataset(label="Data", data=aggregated_values)]
        else:
            unique_series = sorted(list(set(filter(None, [s for _, _, s in values_data]))))

            if not unique_series:
                logger.warning(f"No series found for {chart_definition.chart_type} chart")
                datasets = []
            else:
                # Create a dataset for each series
                datasets = []
                for series in unique_series:
                    series_values = self._aggregate_values_for_series(unique_labels, values_data, series)
                    datasets.append(ChartDataset(label=str(series), data=series_values))

        return ChartResponse(
            chartType=chart_definition.chart_type,
            title=chart_definition.title,
            labels=[str(label) for label in unique_labels],
            datasets=datasets
        )


class ChartGeneratorFactory:
    """Factory for creating chart generators of the required type."""

    _simple_chart_types = {"pie", "bar", "line", "doughnut"}
    _advanced_chart_types = {"stacked_bar"}

    @classmethod
    def get_generator(cls, chart_type: str) -> ChartGenerator:
        if chart_type in cls._simple_chart_types:
            return SimpleChartGenerator()
        elif chart_type in cls._advanced_chart_types:
            return AdvancedChartGenerator()
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    @classmethod
    def get_supported_types(cls) -> Set[str]:
        return cls._simple_chart_types.union(cls._advanced_chart_types)

def extract_field_values(
        messages: List[Dict[str, Any]],
        label_field: str,
        value_field: Optional[str],
        series_field: Optional[str],
        value_aggregation: str
) -> Tuple[List[Any], List[Tuple[Any, float, Any]]]:
    """Extracts field values directly from message data."""
    labels_data = []
    values_data = []
    
    logger.info(f"Extracting data: label_field={label_field}, value_field={value_field}, series_field={series_field}")

    for msg in messages:
        data_items = msg.get('data', [])
        if not isinstance(data_items, list):
            data_items = [data_items] if data_items else []
        
        for data_item in data_items:
            if not isinstance(data_item, dict):
                continue
                
            label_value = data_item.get(label_field)
            if label_value is not None:
                labels_data.append(label_value)
                
                if value_aggregation == 'count':
                    values_data.append((label_value, 1, data_item.get(series_field)))
                elif value_aggregation == 'sum' and value_field:
                    try:
                        # Handle empty strings or convert to numeric
                        value_str = data_item.get(value_field, "0")
                        if value_str == "":
                            value_str = "0"
                        # Remove any non-numeric characters (like commas)
                        value_str = ''.join(c for c in str(value_str) if c.isdigit() or c == '.' or c == '-')
                        value = float(value_str)
                        values_data.append((label_value, value, data_item.get(series_field)))
                    except (ValueError, TypeError):
                        logger.warning(f"Non-numeric value '{data_item.get(value_field)}' "
                                      f"for field {value_field}")

    # Log extracted data for debugging
    logger.info(f"Extracted {len(labels_data)} labels and {len(values_data)} value points")
    return labels_data, values_data


def generate_chart_data_from_data(
        messages: List[Dict[str, Any]],
        chart_definition: ChartDefinition
) -> ChartResponse:
    """Generates chart data directly from messages using field names."""
    title = chart_definition.title
    chart_type = chart_definition.chart_type

    labels_data, values_data = extract_field_values(
        messages,
        chart_definition.label_field,
        chart_definition.value_field,
        chart_definition.series_field,
        chart_definition.value_aggregation
    )

    unique_labels = sorted(list(set(filter(None, labels_data))))
    if not unique_labels:
        logger.warning("No labels for the diagram were found")
        return ChartResponse(
            chartType=chart_type,
            title=title,
            labels=[],
            datasets=[]
        )

    try:
        chart_generator = ChartGeneratorFactory.get_generator(chart_type)
        return chart_generator.generate(unique_labels, values_data, chart_definition)
    except ValueError as e:
        logger.error(f"Error during diagram generation: {str(e)}")
        return ChartResponse(
            chartType=chart_type,
            title=title,
            labels=[],
            datasets=[]
        )
