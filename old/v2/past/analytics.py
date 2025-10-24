# past/analytics.py

class PastStrategies:
    """
    Handles storage and analysis of all frozen (historical) strategy objects.
    Provides methods to generate dashboard graphs and metrics.
    """

    def __init__(self):
        self.frozen_strategies = []  # List of frozen Strategy objects, ordered by time

    def add_frozen_strategy(self, strategy):
        """
        Add a frozen Strategy object for analytics.
        """
        if getattr(strategy, 'status', None) == 'frozen':
            self.frozen_strategies.append(strategy)

    def generate_graphs(self, stock_data=None):
        """
        Generate graph-ready data structures:
        - Time buffer graph (ahead/behind schedule over time)
        - Actual vs. Target portfolio growth
        Args:
            stock_data: dictionary keyed by asset symbol (for price/time series data)
        Returns:
            dict containing data for all dashboard visualizations
        """
        # Placeholder implementation—extend for real calculations
        return {
            "time_buffer_graph": [],          # e.g., [{"date": ..., "buffer_months": ...}, ...]
            "actual_vs_target_graph": [],     # e.g., [{"date": ..., "actual": ..., "target": ...}, ...]
        }

    def calculate_metrics(self, stock_data=None):
        """
        Compute dashboard numeric metrics:
        - Actual and target IRR
        - Progress (percent to goal)
        - Time buffer value
        - Milestone markers (if any)
        Args:
            stock_data: asset price data for quantitative calculations
        Returns:
            dict of computed scalar metrics
        """
        # Placeholder implementation—extend with live logic
        return {
            "current_IRR": None,
            "target_IRR": None,
            "percent_to_goal": None,
            "time_buffer": None,
            "milestones": []
        }

    def clear(self):
        """
        Reset the frozen strategies list (for testing or reloading sessions).
        """
        self.frozen_strategies.clear()
