import sys
from unittest.mock import MagicMock

# Mock tigeropen and all its submodules before they are imported
mock_tigeropen = MagicMock()
sys.modules['tigeropen'] = mock_tigeropen
sys.modules['tigeropen.tiger_open_config'] = mock_tigeropen.tiger_open_config
sys.modules['tigeropen.common'] = mock_tigeropen.common
sys.modules['tigeropen.common.util'] = mock_tigeropen.common.util
sys.modules['tigeropen.common.util.signature_utils'] = mock_tigeropen.common.util.signature_utils
sys.modules['tigeropen.trade'] = mock_tigeropen.trade
sys.modules['tigeropen.trade.trade_client'] = mock_tigeropen.trade.trade_client
sys.modules['tigeropen.trade.model'] = mock_tigeropen.trade.model
sys.modules['tigeropen.quote'] = mock_tigeropen.quote
sys.modules['tigeropen.quote.quote_client'] = mock_tigeropen.quote.quote_client
sys.modules['tigeropen.push'] = mock_tigeropen.push
sys.modules['tigeropen.push.push_client'] = mock_tigeropen.push.push_client
