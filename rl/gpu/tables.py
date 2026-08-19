"""Device lookup tables for the batched GPU engine."""

import torch

from . import constants as C


class Tables:
    def __init__(self, device):
        d = torch.device(device)

        def t(data, dtype):
            return torch.tensor(data, device=d, dtype=dtype)

        self.device = d
        self.seed_cost = t(C.SEED_COST, torch.float32)
        self.crop_first = t(C.CROP_FIRST, torch.int32)
        self.crop_max_day = t(C.CROP_MAX_YIELD_DAY, torch.int32)
        self.crop_interval = t(C.CROP_INTERVAL, torch.int32)
        self.crop_max_yield = t(C.CROP_MAX_YIELD, torch.int16)
        self.crop_ongoing = t(C.CROP_ONGOING, torch.bool)
        self.water_window = t(C.WATER_WINDOW_START, torch.int32)

        self.animal_struct = t(C.ANIMAL_STRUCT, torch.int16)
        self.animal_cost = t(C.ANIMAL_COST, torch.float32)
        self.animal_product = t(C.ANIMAL_PRODUCT, torch.int64)
        self.animal_first = t(C.ANIMAL_FIRST, torch.int32)
        self.animal_interval = t(C.ANIMAL_INTERVAL, torch.int32)
        self.animal_max_held = t(C.ANIMAL_MAX_HELD, torch.int16)
        self.animal_shed = t(C.ANIMAL_SHED, torch.int64)

        self.base_price = t(C.BASE_PRICE, torch.float32)
        self.land_prices = t(C.LAND_PRICES, torch.float32)
        self.hire_fib = t(C.HIRE_FIB, torch.float32)

        self.mkt_t = t(C.MKT_T, torch.float32)
        self.mkt_below_f = t(C.MKT_BELOW_F, torch.int64)
        self.mkt_below_t = t(C.MKT_BELOW_T, torch.float32)
        self.mkt_above_f = t(C.MKT_ABOVE_F, torch.int64)
        self.mkt_above_t = t(C.MKT_ABOVE_T, torch.float32)
        self.i0 = t([C.MARKET_I0] * C.N_PRODUCT, torch.float32)

        self.shop_consume = t(C.SHOP_CONSUME, torch.int32)
        self.town_center = t(C.TOWN_CENTER, torch.int32)

        dx = [0] * 18
        dy = [0] * 18
        dx[C.OP_NORTH], dy[C.OP_NORTH] = 0, -1
        dx[C.OP_SOUTH], dy[C.OP_SOUTH] = 0, 1
        dx[C.OP_EAST], dy[C.OP_EAST] = 1, 0
        dx[C.OP_WEST], dy[C.OP_WEST] = -1, 0
        self.move_dx = t(dx, torch.int64)
        self.move_dy = t(dy, torch.int64)

        self.shed_x = t([p[0] for p in C.SHED_TILES], torch.int64)
        self.shed_y = t([p[1] for p in C.SHED_TILES], torch.int64)
        self.spawn = t(list(C.SPAWN), torch.int64)
        self.yy = torch.arange(C.BOARD, device=d).view(1, 1, C.BOARD, 1)
        self.xx = torch.arange(C.BOARD, device=d).view(1, 1, 1, C.BOARD)
        self.price_table = None  # filled lazily by engine.attach_price_table
