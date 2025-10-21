#!/usr/bin/env python3
"""
测试机器人配置更新API的脚本
"""
import requests
import json
import sys

def test_robot_config_update():
    """测试机器人配置更新功能"""
    
    # API服务器地址
    base_url = "http://localhost:8001"
    
    print("=== 机器人配置更新API测试 ===\n")
    
    # 1. 首先获取现有机器人列表
    print("1. 获取现有机器人列表...")
    try:
        response = requests.get(f"{base_url}/api/robots")
        if response.status_code == 200:
            robots = response.json()
            print(f"   成功获取到 {len(robots)} 个机器人")
            
            if not robots:
                print("   没有找到机器人，请先注册一个机器人")
                return False
            
            # 选择第一个机器人进行测试
            test_robot = robots[0]
            robot_id = test_robot['id']
            print(f"   选择机器人进行测试: {test_robot['name']} (ID: {robot_id})")
            print(f"   当前配置: IP={test_robot['ip']}, 最大速度={test_robot['maxSpeed']}")
            
        else:
            print(f"   获取机器人列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   获取机器人列表时发生错误: {e}")
        return False
    
    # 2. 测试更新机器人配置
    print("\n2. 测试更新机器人配置...")
    
    # 准备更新数据
    update_data = {
        "name": f"{test_robot['name']}_Updated",
        "maxSpeed": 3.5,
        "battery": 85.0,
        "brand": "TestBrand",
        "gid": "test_group",
        "config": {
            "test_setting": "test_value",
            "updated_at": "2024-01-01"
        },
        "properties": {
            "test_property": "test_prop_value"
        }
    }
    
    try:
        # 发送POST请求更新配置
        response = requests.post(
            f"{base_url}/api/robots/{robot_id}/update",
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✓ 机器人配置更新成功!")
                print(f"   更新的字段: {result.get('updated_fields', [])}")
                
                # 显示更新后的机器人信息
                updated_robot = result.get('robot_info', {})
                print(f"   更新后信息:")
                print(f"     名称: {updated_robot.get('name')}")
                print(f"     IP: {updated_robot.get('ip')}")
                print(f"     最大速度: {updated_robot.get('maxSpeed')}")
                print(f"     电池: {updated_robot.get('battery')}")
                print(f"     品牌: {updated_robot.get('brand')}")
                print(f"     组ID: {updated_robot.get('gid')}")
                print(f"     最后更新: {updated_robot.get('last_update')}")
                
            else:
                print(f"   ✗ 更新失败: {result.get('message', '未知错误')}")
                return False
        else:
            print(f"   ✗ 请求失败: HTTP {response.status_code}")
            try:
                error_info = response.json()
                print(f"   错误信息: {error_info.get('message', '未知错误')}")
            except:
                print(f"   响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"   更新配置时发生错误: {e}")
        return False
    
    # 3. 验证更新是否保存到文件
    print("\n3. 验证更新是否保存到文件...")
    try:
        # 重新获取机器人列表，验证更新是否持久化
        response = requests.get(f"{base_url}/api/robots")
        if response.status_code == 200:
            robots = response.json()
            updated_robot = None
            
            for robot in robots:
                if robot['id'] == robot_id:
                    updated_robot = robot
                    break
            
            if updated_robot:
                print("   ✓ 从文件重新加载的机器人信息:")
                print(f"     名称: {updated_robot['name']}")
                print(f"     最大速度: {updated_robot['maxSpeed']}")
                print(f"     电池: {updated_robot['battery']}")
                print(f"     品牌: {updated_robot['brand']}")
                print(f"     组ID: {updated_robot['gid']}")
                
                # 验证更新是否正确
                if (updated_robot['name'] == update_data['name'] and
                    updated_robot['maxSpeed'] == update_data['maxSpeed'] and
                    updated_robot['battery'] == update_data['battery']):
                    print("   ✓ 配置更新验证成功!")
                    return True
                else:
                    print("   ✗ 配置更新验证失败，数据不匹配")
                    return False
            else:
                print("   ✗ 未找到更新的机器人")
                return False
        else:
            print(f"   ✗ 重新获取机器人列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   验证更新时发生错误: {e}")
        return False

def test_error_cases():
    """测试错误情况"""
    base_url = "http://localhost:8001"
    
    print("\n=== 错误情况测试 ===\n")
    
    # 测试不存在的机器人ID
    print("1. 测试更新不存在的机器人...")
    try:
        fake_id = "non-existent-robot-id"
        response = requests.post(
            f"{base_url}/api/robots/{fake_id}/update",
            json={"name": "Test"},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 404:
            print("   ✓ 正确返回404错误")
        else:
            print(f"   ✗ 期望404，实际返回: {response.status_code}")
            
    except Exception as e:
        print(f"   测试时发生错误: {e}")
    
    # 测试重复名称
    print("\n2. 测试重复机器人名称...")
    try:
        # 先获取两个不同的机器人
        response = requests.get(f"{base_url}/api/robots")
        if response.status_code == 200:
            robots = response.json()
            if len(robots) >= 2:
                robot1_id = robots[0]['id']
                robot2_name = robots[1]['name']
                
                # 尝试将robot1的名称改为robot2的名称
                response = requests.post(
                    f"{base_url}/api/robots/{robot1_id}/update",
                    json={"name": robot2_name},
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 409:
                    print("   ✓ 正确返回409冲突错误")
                else:
                    print(f"   ✗ 期望409，实际返回: {response.status_code}")
            else:
                print("   跳过测试（需要至少2个机器人）")
                
    except Exception as e:
        print(f"   测试时发生错误: {e}")

if __name__ == "__main__":
    print("开始测试机器人配置更新API...")
    
    # 基本功能测试
    success = test_robot_config_update()
    
    if success:
        print("\n✓ 基本功能测试通过!")
        
        # 错误情况测试
        test_error_cases()
        
        print("\n=== 测试完成 ===")
        print("机器人配置更新API功能正常!")
    else:
        print("\n✗ 基本功能测试失败!")
        sys.exit(1)