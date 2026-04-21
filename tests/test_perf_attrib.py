import numpy as np
import pandas as pd
import unittest

from empyrical_plus.perf_attrib import perf_attrib


class PerfAttribTestCase(unittest.TestCase):

    def test_perf_attrib_simple(self):

        start_date = '2017-01-01'
        periods = 2
        dts = pd.date_range(start_date, periods=periods)
        dts.name = 'dt'

        tickers = ['stock1', 'stock2']
        styles = ['risk_factor1', 'risk_factor2']

        returns = pd.Series(data=[0.1, 0.1], index=dts)

        factor_returns = pd.DataFrame(
            columns=styles,
            index=dts,
            data={'risk_factor1': [.1, .1],
                  'risk_factor2': [.1, .1]}
        )

        index = pd.MultiIndex.from_product(
            [dts, tickers], names=['dt', 'ticker'])

        positions = pd.Series([0.2857142857142857, 0.7142857142857143,
                               0.2857142857142857, 0.7142857142857143],
                              index=index)

        factor_loadings = pd.DataFrame(
            columns=styles,
            index=index,
            data={'risk_factor1': [0.25, 0.25, 0.25, 0.25],
                  'risk_factor2': [0.25, 0.25, 0.25, 0.25]}
        )

        expected_perf_attrib_output = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2', 'total_returns',
                     'common_returns', 'specific_returns',
                     'tilt_returns', 'timing_returns'],
            data={'risk_factor1': [0.025, 0.025],
                  'risk_factor2': [0.025, 0.025],
                  'common_returns': [0.05, 0.05],
                  'specific_returns': [0.05, 0.05],
                  'tilt_returns': [0.05, 0.05],
                  'timing_returns': [0.0, 0.0],
                  'total_returns': returns}
        )

        expected_exposures_portfolio = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2'],
            data={'risk_factor1': [0.25, 0.25],
                  'risk_factor2': [0.25, 0.25]}
        )

        exposures_portfolio, perf_attrib_output = perf_attrib(returns,
                                                              positions,
                                                              factor_returns,
                                                              factor_loadings)

        pd.testing.assert_frame_equal(expected_perf_attrib_output,
                                           perf_attrib_output)

        pd.testing.assert_frame_equal(expected_exposures_portfolio,
                                           exposures_portfolio)

        # test long and short positions
        positions = pd.Series([0.5, -0.5, 0.5, -0.5], index=index)

        exposures_portfolio, perf_attrib_output = perf_attrib(returns,
                                                              positions,
                                                              factor_returns,
                                                              factor_loadings)

        expected_perf_attrib_output = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2', 'total_returns',
                     'common_returns', 'specific_returns',
                     'tilt_returns', 'timing_returns'],
            data={'risk_factor1': [0.0, 0.0],
                  'risk_factor2': [0.0, 0.0],
                  'common_returns': [0.0, 0.0],
                  'specific_returns': [0.1, 0.1],
                  'tilt_returns': [0.0, 0.0],
                  'timing_returns': [0.0, 0.0],
                  'total_returns': returns}
        )

        expected_exposures_portfolio = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2'],
            data={'risk_factor1': [0.0, 0.0],
                  'risk_factor2': [0.0, 0.0]}
        )

        pd.testing.assert_frame_equal(expected_perf_attrib_output,
                                           perf_attrib_output)

        pd.testing.assert_frame_equal(expected_exposures_portfolio,
                                           exposures_portfolio)

        # test long and short positions with tilt exposure
        positions = pd.Series([1.0, -0.5, 1.0, -0.5], index=index)

        exposures_portfolio, perf_attrib_output = perf_attrib(returns,
                                                              positions,
                                                              factor_returns,
                                                              factor_loadings)

        expected_perf_attrib_output = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2', 'total_returns',
                     'common_returns', 'specific_returns',
                     'tilt_returns', 'timing_returns'],
            data={'risk_factor1': [0.0125, 0.0125],
                  'risk_factor2': [0.0125, 0.0125],
                  'common_returns': [0.025, 0.025],
                  'specific_returns': [0.075, 0.075],
                  'tilt_returns': [0.025, 0.025],
                  'timing_returns': [0.0, 0.0],
                  'total_returns': returns}
        )

        expected_exposures_portfolio = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2'],
            data={'risk_factor1': [0.125, 0.125],
                  'risk_factor2': [0.125, 0.125]}
        )

        pd.testing.assert_frame_equal(expected_perf_attrib_output,
                                           perf_attrib_output)

        pd.testing.assert_frame_equal(expected_exposures_portfolio,
                                           exposures_portfolio)

