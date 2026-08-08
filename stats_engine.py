import numpy as np
import pandas as pd
from scipy import stats

class CivicStatsEngine:
    @staticmethod
    def calculate_resolution_stats(resolution_times):
        """
        Calculates descriptive statistics & IQR/Fences for resolution times (in hours).
        """
        if not resolution_times or len(resolution_times) < 2:
            return {"error": "Not enough data for statistical calculation"}

        arr = np.array(resolution_times)
        
        # Central Tendency
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        try:
            mode_val = float(stats.mode(arr, keepdims=False)[0])
        except Exception:
            mode_val = mean_val

        # Dispersion
        var_val = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0
        std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        range_val = max_val - min_val

        # Quartiles and Outlier Detection (IQR & Fences)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1
        lower_fence = q1 - (1.5 * iqr)
        upper_fence = q3 + (1.5 * iqr)

        outliers = [float(x) for x in arr if x < lower_fence or x > upper_fence]

        return {
            "mean": round(mean_val, 2),
            "median": round(median_val, 2),
            "mode": round(mode_val, 2),
            "range": round(range_val, 2),
            "variance": round(var_val, 2),
            "std_dev": round(std_val, 2),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "lower_fence": round(lower_fence, 2),
            "upper_fence": round(upper_fence, 2),
            "outliers_count": len(outliers)
        }

    @staticmethod
    def category_frequency_distribution(categories_list):
        """Calculates frequency distribution for complaint categories."""
        df = pd.Series(categories_list)
        freq = df.value_counts().to_dict()
        total = len(categories_list)
        perc = {k: round((v / total) * 100, 2) for k, v in freq.items()}
        return {"frequencies": freq, "percentages": perc}