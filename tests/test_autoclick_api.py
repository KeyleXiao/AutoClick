import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import types
mock_pg = types.SimpleNamespace(moveTo=lambda *a, **k: None, click=lambda *a, **k: None, mouseDown=lambda *a, **k: None, mouseUp=lambda *a, **k: None, position=lambda: (0,0), screenshot=lambda: None, FAILSAFE=True)
sys.modules["pyautogui"] = mock_pg
import json
import base64
import os
import tempfile
from autoclick_api import load_items, cleanup_items


def test_load_and_cleanup_items():
    with open('demo/small.png', 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    data = [{
        'image': encoded,
        'action': 'double',
        'delay': 100,
        'interrupt': True,
        'enable': True
    }]
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tmp:
        json.dump(data, tmp)
        config_path = tmp.name
    items = load_items(config_path)
    assert len(items) == 1
    item = items[0]
    assert item['action'] == 'double'
    assert item['delay'] == 100
    assert item['interrupt'] is True
    assert item['enable'] is True
    assert os.path.exists(item['path'])
    cleanup_items(items)
    assert not os.path.exists(item['path'])
    os.unlink(config_path)
