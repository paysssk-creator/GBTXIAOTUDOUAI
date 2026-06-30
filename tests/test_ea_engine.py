# -*- coding: utf-8 -*-
"""Tests for gbt.ea_engine"""
import unittest

from gbt.ea_engine import AddMode, EAConfig, EAEngine, EADecision, IntervalMode, MultiplierMode, PositionSnapshot


class TestEAEngine(unittest.TestCase):
    def test_initial_shares(self):
        cfg = EAConfig(base_lots=2)
        ea = EAEngine(cfg)
        self.assertEqual(ea.initial_shares(), 200)

    def test_addition_lots_half_multiplier(self):
        cfg = EAConfig(add_mode=AddMode.HALF_MULTIPLIER, base_lots=4)
        ea = EAEngine(cfg)
        self.assertEqual(ea.addition_lots(1), 4)
        self.assertEqual(ea.addition_lots(2), 2)
        self.assertEqual(ea.addition_lots(3), 1)

    def test_addition_lots_increment(self):
        cfg = EAConfig(add_mode=AddMode.INCREMENT_LOTS, base_lots=1, increment_lots=2)
        ea = EAEngine(cfg)
        self.assertEqual(ea.addition_lots(1), 1)
        self.assertEqual(ea.addition_lots(2), 3)
        self.assertEqual(ea.addition_lots(3), 5)

    def test_addition_lots_custom(self):
        cfg = EAConfig(add_mode=AddMode.CUSTOM_LOTS, custom_lots_sequence=[1, 2, 3])
        ea = EAEngine(cfg)
        self.assertEqual(ea.addition_lots(1), 1)
        self.assertEqual(ea.addition_lots(2), 2)
        self.assertEqual(ea.addition_lots(4), 1)

    def test_addition_lots_order_coefficient(self):
        cfg = EAConfig(add_mode=AddMode.ORDER_COEFFICIENT, base_lots=2, order_coefficient=0.5)
        ea = EAEngine(cfg)
        self.assertEqual(ea.addition_lots(1), 2)
        self.assertEqual(ea.addition_lots(2), 3)
        self.assertEqual(ea.addition_lots(3), 4)

    def test_multiplier_sequence(self):
        cfg = EAConfig(multiplier_mode=MultiplierMode.SEQUENCE,
                       multiplier_sequence=[2, 3],
                       add_mode=AddMode.HALF_MULTIPLIER,
                       base_lots=2)
        ea = EAEngine(cfg)
        self.assertEqual(ea.addition_lots(1), 4)
        self.assertEqual(ea.addition_lots(2), 3)
        self.assertEqual(ea.addition_lots(3), 2)

    def test_atr_calculation(self):
        highs = [11, 12, 13, 12, 14]
        lows = [9, 10, 11, 10, 12]
        closes = [10, 11, 12, 11, 13]
        atr = EAEngine.calculate_atr(highs, lows, closes, period=3)
        self.assertGreater(atr, 0)

    def test_profit_pyramid_decision(self):
        cfg = EAConfig(
            base_lots=1,
            profit_add_enabled=True,
            profit_interval_mode=IntervalMode.FIXED,
            profit_fixed_spacing=1.0,
        )
        ea = EAEngine(cfg)
        pos = PositionSnapshot(code="sh600519", total_shares=100, avg_cost=100.0,
                               additions=0, last_add_price=100.0)
        dec = ea.decide("sh600519", 101.1, "buy", position=pos)
        self.assertEqual(dec.action, "add_profit")
        self.assertEqual(dec.shares, 100)
        self.assertIn("盈利加仓", dec.reason)

    def test_loss_dca_decision(self):
        cfg = EAConfig(
            base_lots=1,
            loss_add_enabled=True,
            loss_interval_mode=IntervalMode.FIXED,
            loss_fixed_spacing=1.0,
        )
        ea = EAEngine(cfg)
        pos = PositionSnapshot(code="sh600519", total_shares=100, avg_cost=100.0,
                               additions=0, last_add_price=100.0)
        dec = ea.decide("sh600519", 98.9, "buy", position=pos)
        self.assertEqual(dec.action, "add_loss")
        self.assertIn("亏损加仓", dec.reason)

    def test_stop_loss(self):
        cfg = EAConfig(stop_loss_points=50)  # 0.5元
        ea = EAEngine(cfg)
        pos = PositionSnapshot(code="sh600519", total_shares=100, avg_cost=100.0)
        dec = ea.decide("sh600519", 99.4, "buy", position=pos)
        self.assertEqual(dec.action, "close")
        self.assertIn("止损", dec.reason)

    def test_take_profit(self):
        cfg = EAConfig(take_profit_points=100)  # 1.0元
        ea = EAEngine(cfg)
        pos = PositionSnapshot(code="sh600519", total_shares=100, avg_cost=100.0)
        dec = ea.decide("sh600519", 101.1, "buy", position=pos)
        self.assertEqual(dec.action, "close")
        self.assertIn("止盈", dec.reason)

    def test_validate_buy_not_lot_multiple(self):
        cfg = EAConfig()
        ea = EAEngine(cfg)
        dec = EADecision(action="open", code="sh600519", shares=150, price=10.0, reason="test")
        ok, reason = ea.validate_decision(dec, available_cash=100000)
        self.assertFalse(ok)
        self.assertIn("100", reason)

    def test_validate_insufficient_cash(self):
        cfg = EAConfig(base_lots=10)
        ea = EAEngine(cfg)
        dec = EADecision(action="open", code="sh600519", shares=1000, price=100.0, reason="test")
        ok, reason = ea.validate_decision(dec, available_cash=1000)
        self.assertFalse(ok)
        self.assertIn("现金不足", reason)

    def test_config_roundtrip(self):
        cfg = EAConfig()
        d = cfg.to_dict()
        cfg2 = EAConfig.from_dict(d)
        self.assertEqual(cfg.base_lots, cfg2.base_lots)
        self.assertEqual(cfg.add_mode, cfg2.add_mode)


if __name__ == "__main__":
    unittest.main()
