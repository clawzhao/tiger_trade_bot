import os
import sys
from unittest.mock import MagicMock

# Build a comprehensive mock for tigeropen package

mock_tigeropen = MagicMock()
mock_tigeropen.__version__ = "3.5.7"

# tigeropen.tiger_open_config
mock_tigeropen.tiger_open_config = MagicMock()
mock_tigeropen.tiger_open_config.TigerOpenClientConfig = MagicMock

# tigeropen.common.util.signature_utils
mock_common_util = MagicMock()
mock_common_util.signature_utils = MagicMock()
mock_common_util.signature_utils.read_private_key = MagicMock(return_value=b"fake_key")
mock_tigeropen.common = MagicMock()
mock_tigeropen.common.util = mock_common_util
mock_tigeropen.common.util.signature_utils = mock_common_util.signature_utils

# tigeropen.trade.trade_client
mock_trade = MagicMock()
mock_trade.TradeClient = MagicMock
# tigeropen.trade.domain.order
mock_order_mod = MagicMock()
mock_order_mod.Order = MagicMock
# tigeropen.trade.domain.contract
mock_contract_mod = MagicMock()
mock_contract_mod.Contract = MagicMock
# Assemble domain
mock_domain = MagicMock()
mock_domain.order = mock_order_mod
mock_domain.contract = mock_contract_mod
mock_trade.domain = mock_domain
mock_tigeropen.trade = mock_trade

# tigeropen.quote.quote_client
mock_quote = MagicMock()
mock_quote.QuoteClient = MagicMock
mock_tigeropen.quote = mock_quote

# tigeropen.push.push_client
mock_push = MagicMock()
mock_push.PushClient = MagicMock
mock_tigeropen.push = mock_push

# Register all modules in sys.modules BEFORE any imports
sys.modules['tigeropen'] = mock_tigeropen
sys.modules['tigeropen.tiger_open_config'] = mock_tigeropen.tiger_open_config
sys.modules['tigeropen.common'] = mock_tigeropen.common
sys.modules['tigeropen.common.util'] = mock_tigeropen.common.util
sys.modules['tigeropen.common.util.signature_utils'] = mock_tigeropen.common.util.signature_utils
sys.modules['tigeropen.trade'] = mock_tigeropen.trade
sys.modules['tigeropen.trade.trade_client'] = mock_tigeropen.trade.trade_client
sys.modules['tigeropen.trade.domain'] = mock_tigeropen.trade.domain
sys.modules['tigeropen.trade.domain.order'] = mock_tigeropen.trade.domain.order
sys.modules['tigeropen.trade.domain.contract'] = mock_tigeropen.trade.domain.contract
sys.modules['tigeropen.quote'] = mock_tigeropen.quote
sys.modules['tigeropen.quote.quote_client'] = mock_tigeropen.quote.quote_client
sys.modules['tigeropen.push'] = mock_tigeropen.push
sys.modules['tigeropen.push.push_client'] = mock_tigeropen.push.push_client
