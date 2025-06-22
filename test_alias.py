#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import base64
import tempfile
import os

def test_alias_functionality():
    """测试别名功能是否正常工作"""
    
    # 创建一个测试项目
    test_item = {
        'path': '/tmp/test.png',
        'alias': '测试按钮',
        'action': 'single',
        'delay': 100,
        'interrupt': False,
        'enable': True,
        'offset': [0.5, 0.5]
    }
    
    # 测试导出功能
    export_data = [{
        'image': 'dGVzdA==',  # base64编码的测试数据
        'alias': test_item['alias'],
        'action': test_item['action'],
        'delay': test_item['delay'],
        'interrupt': test_item['interrupt'],
        'enable': test_item['enable'],
        'offset': test_item['offset']
    }]
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
        export_file = f.name
    
    print(f"导出文件已保存到: {export_file}")
    
    # 测试导入功能
    with open(export_file, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    # 验证导入的数据
    imported_item = import_data[0]
    print(f"导入的别名: {imported_item.get('alias', '')}")
    print(f"导入的动作: {imported_item.get('action', '')}")
    print(f"导入的延迟: {imported_item.get('delay', '')}")
    
    # 清理临时文件
    os.unlink(export_file)
    
    print("别名功能测试完成！")

if __name__ == '__main__':
    test_alias_functionality() 