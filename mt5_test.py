from app.mt5_robot import MT5Robot
r = MT5Robot()
print('connect:', r.connect())
print('account:', r.account_info())
print('positions:', len(r.get_positions()))
print('ea_active:', r.is_ea_active())
