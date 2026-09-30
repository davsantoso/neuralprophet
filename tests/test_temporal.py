"""Check the one-step forecast boundary against NeuralProphet itself."""

import logging
import os
from pathlib import Path
import unittest
import warnings

import pandas as pd

from cargo_forecast.data import load_bps_data, to_neuralprophet


class TemporalPredictionTests(unittest.TestCase):
    def test_target_month_actual_does_not_change_its_forecast(self):
        matplotlib_cache = Path(".mpl-cache").resolve()
        matplotlib_cache.mkdir(exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
        warnings.filterwarnings("ignore", category=FutureWarning)
        logging.getLogger("NP.plotly").setLevel(logging.CRITICAL)
        from neuralprophet import NeuralProphet, set_log_level, set_random_seed

        set_log_level("ERROR")
        set_random_seed(42)
        data = load_bps_data()
        train = to_neuralprophet(data.iloc[:84], "bongkar")
        validation = to_neuralprophet(data.iloc[:96], "bongkar")
        model = NeuralProphet(
            n_lags=3,
            n_forecasts=1,
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            epochs=3,
            learning_rate=0.01,
        )
        model.fit(train, freq="MS", progress=None)
        original = model.predict(validation).set_index("ds")
        changed = validation.copy()
        changed.loc[changed["ds"] == pd.Timestamp("2024-01-01"), "y"] += 10_000
        altered = model.predict(changed).set_index("ds")
        january = pd.Timestamp("2024-01-01")
        february = pd.Timestamp("2024-02-01")
        self.assertAlmostEqual(original.loc[january, "yhat1"], altered.loc[january, "yhat1"], places=5)
        self.assertNotAlmostEqual(original.loc[february, "yhat1"], altered.loc[february, "yhat1"], places=1)


if __name__ == "__main__":
    unittest.main()

