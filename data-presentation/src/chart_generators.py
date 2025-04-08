import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Set, Dict, Optional
from collections import defaultdict

from models import ChartResponse, ChartDataset, ChartDefinition, MappingItem
from models import apply_mapping

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

        # Check if series_role is specified
        if not chart_definition.series_role:
            logger.warning(f"No series_role parameter specified for {chart_definition.chart_type} chart")
            # Return a simple chart if series_role is missing
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

    _simple_chart_types = {"pie", "bar", "line"}
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
        mappings_by_type: Dict[str, Dict[str, Any]],
        label_role: str,
        value_source_role: Optional[str],
        series_role: Optional[str],
        value_aggregation: str
) -> Tuple[List[Any], List[Tuple[Any, float, Any]]]:
    """Extracts field values from messages according to mapping."""
    labels_data = []
    values_data = []

    for msg in messages:
        if not isinstance(msg.get('data'), dict) or 'message_type' not in msg['data']:
            continue

        msg_type = msg['data']['message_type']
        if msg_type not in mappings_by_type:
            continue

        mapped_msg = apply_mapping(msg, mappings_by_type[msg_type])

        label_value = mapped_msg.get(label_role)
        if label_value is not None:
            labels_data.append(label_value)
            if value_aggregation == 'count':
                values_data.append((label_value, 1, mapped_msg.get(series_role)))
            elif value_aggregation == 'sum' and value_source_role:
                try:
                    value = float(mapped_msg.get(value_source_role, 0))
                    values_data.append((label_value, value, mapped_msg.get(series_role)))
                except (ValueError, TypeError):
                    logger.warning(f"Non-numeric value '{mapped_msg.get(value_source_role)}' "
                                   f"for the role {value_source_role}")

    return labels_data, values_data


def generate_chart_data_from_mapping(
        messages: List[Dict[str, Any]],
        chart_definition: ChartDefinition,
        type_mappings: List[MappingItem]
) -> ChartResponse:
    """Generates data for the diagram based on the diagram definition and mappings."""
    mappings_by_type = {item.message_type: item.mapping for item in type_mappings}
    title = chart_definition.title
    chart_type = chart_definition.chart_type

    labels_data, values_data = extract_field_values(
        messages,
        mappings_by_type,
        chart_definition.label_role,
        chart_definition.value_source_role,
        chart_definition.series_role,
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
