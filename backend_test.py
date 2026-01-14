import requests
import sys
from datetime import datetime
import json

class Phase6Tester:
    def __init__(self, base_url="https://master-deploy.preview.emergentagent.com"):
        self.base_url = base_url
        self.api = f"{base_url}/api"
        self.admin_token = None
        self.test_client_id = None
        self.test_order_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.json()}")
                except:
                    print(f"   Response: {response.text}")

            return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login and get token"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@test.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            return True
        return False

    def test_public_games_access(self):
        """Test public games endpoint (no auth required)"""
        success, response = self.run_test(
            "Public Games Access",
            "GET",
            "public/games?limit=10",
            200
        )
        
        if success:
            games = response if isinstance(response, list) else response.get('games', [])
            print(f"   🎮 Found {len(games)} public games")
            for game in games[:3]:  # Show first 3 games
                print(f"   - {game.get('name', 'Unknown')} (Available: {game.get('availability_status', 'unknown')})")
        
        return success

    def test_public_site_info(self):
        """Test public site info endpoint"""
        success, response = self.run_test(
            "Public Site Info",
            "GET",
            "public/site-info",
            200
        )
        
        if success:
            print(f"   🏢 Site Name: {response.get('name', 'Unknown')}")
            print(f"   📞 Support Text: {response.get('support_text', 'N/A')}")
        
        return success

    def test_ai_test_info(self):
        """Test AI Test Spot info endpoint"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "AI Test Spot Info",
            "GET",
            "admin/test/ai-test/info",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            print(f"   🤖 Test Mode: {response.get('test_mode', False)}")
            scenarios = response.get('available_scenarios', [])
            print(f"   📋 Available Scenarios: {len(scenarios)}")
            for scenario in scenarios:
                print(f"   - {scenario.get('name', 'Unknown')}")
        
        return success

    def test_ai_test_simulate(self):
        """Test AI Test Spot simulation"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "AI Test Simulation",
            "POST",
            "admin/test/ai-test/simulate",
            200,
            data={
                "messages": [
                    {"role": "user", "content": "What is my balance?"}
                ],
                "test_scenario": "client_query"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            print(f"   🤖 Test Mode: {response.get('test_mode', False)}")
            print(f"   💬 Response: {response.get('response', {}).get('content', 'No response')[:50]}...")
            print(f"   🆔 Test ID: {response.get('test_id', 'N/A')}")
        
        return success

    def test_create_test_client(self):
        """Test creating a test client for payment simulation"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Create Test Client",
            "POST",
            "admin/test/data/create-test-client",
            200,
            data={"display_name": "Phase6 Test Client"},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            client = response.get('client', {})
            self.test_client_id = client.get('client_id')
            print(f"   👤 Created Client: {client.get('display_name', 'Unknown')}")
            print(f"   🆔 Client ID: {self.test_client_id}")
        
        return success

    def test_payment_simulate(self):
        """Test payment simulation"""
        if not self.admin_token or not self.test_client_id:
            return False
            
        success, response = self.run_test(
            "Payment Simulation",
            "POST",
            "admin/test/payment/simulate",
            200,
            data={
                "client_id": self.test_client_id,
                "amount": 50.00,
                "payment_type": "cashin",
                "payment_method": "GCash",
                "notes": "Phase 6 test payment"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            self.test_order_id = response.get('order_id')
            print(f"   💰 Amount: ${response.get('amount', 0):.2f}")
            print(f"   📋 Order ID: {self.test_order_id}")
            print(f"   ⚠️  Test Mode: {response.get('test_mode', False)}")
        
        return success

    def test_payment_pending(self):
        """Test getting pending payments"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Pending Payments",
            "GET",
            "admin/test/payment/pending?test_only=true",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            orders = response.get('orders', [])
            print(f"   📋 Pending Orders: {len(orders)}")
            print(f"   📊 Total: {response.get('total', 0)}")
        
        return success

    def test_payment_action_received(self):
        """Test marking payment as received"""
        if not self.admin_token or not self.test_order_id:
            return False
            
        success, response = self.run_test(
            "Mark Payment Received",
            "POST",
            "admin/test/payment/action",
            200,
            data={
                "order_id": self.test_order_id,
                "action": "received"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            print(f"   ✅ Action: {response.get('action', 'unknown')}")
            print(f"   💰 Message: {response.get('message', 'N/A')}")
            wallet = response.get('new_wallet_balance', {})
            print(f"   💵 Real Balance: ${wallet.get('real', 0):.2f}")
            print(f"   🎁 Bonus Balance: ${wallet.get('bonus', 0):.2f}")
        
        return success

    def test_payment_stats(self):
        """Test payment panel statistics"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Payment Panel Stats",
            "GET",
            "admin/test/data/stats",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            stats = response.get('stats', {})
            print(f"   👥 Test Clients: {stats.get('test_clients', 0)}")
            print(f"   📋 Test Orders: {stats.get('test_orders', 0)}")
            print(f"   🤖 AI Test Conversations: {stats.get('ai_test_conversations', 0)}")
            print(f"   ⏳ Pending Payments: {stats.get('pending_payments', 0)}")
        
        return success

    def test_ai_test_logs(self):
        """Test AI test logs endpoint"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "AI Test Logs",
            "GET",
            "admin/test/ai-test/logs?limit=10",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            logs = response.get('logs', [])
            print(f"   📝 Test Logs: {len(logs)}")
            print(f"   🤖 Test Mode: {response.get('test_mode', False)}")
        
        return success

def main():
    print("🚀 Starting Phase 6 Testing - AI Test Spot & Payment Panel...")
    print("=" * 60)
    
    tester = Phase6Tester()
    
    # Test sequence for Phase 6 features
    tests = [
        ("Public Games Access (No Auth)", tester.test_public_games_access),
        ("Public Site Info", tester.test_public_site_info),
        ("Admin Authentication", tester.test_admin_login),
        ("AI Test Spot Info", tester.test_ai_test_info),
        ("AI Test Simulation", tester.test_ai_test_simulate),
        ("AI Test Logs", tester.test_ai_test_logs),
        ("Create Test Client", tester.test_create_test_client),
        ("Payment Simulation", tester.test_payment_simulate),
        ("Pending Payments", tester.test_payment_pending),
        ("Mark Payment Received", tester.test_payment_action_received),
        ("Payment Panel Stats", tester.test_payment_stats),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} - Exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Print results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"❌ Failed Tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("✅ All Phase 6 tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())