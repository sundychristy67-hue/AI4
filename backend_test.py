import requests
import sys
from datetime import datetime
import json

class BonusWalletTester:
    def __init__(self, base_url="https://vaultlink.preview.emergentagent.com"):
        self.base_url = base_url
        self.api = f"{base_url}/api"
        self.admin_token = None
        self.portal_token = "8efe2582-3866-4874-a5f2-3b9999130633"
        self.client_id = "55532916-671e-4c0c-940b-50d848352870"
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

    def test_portal_validation(self):
        """Test portal token validation"""
        success, response = self.run_test(
            "Portal Token Validation",
            "GET",
            f"portal/validate/{self.portal_token}",
            200
        )
        return success and response.get('valid') == True

    def test_portal_wallets(self):
        """Test portal wallets endpoint"""
        success, response = self.run_test(
            "Portal Wallets API",
            "GET",
            "portal/wallets",
            200,
            headers={'X-Portal-Token': self.portal_token}
        )
        
        if success:
            # Verify dual wallet structure
            required_fields = ['real_balance', 'bonus_balance', 'total_in', 'total_out', 
                             'total_real_loaded', 'total_bonus_loaded', 'total_bonus_earned']
            for field in required_fields:
                if field not in response:
                    print(f"   ⚠️  Missing field: {field}")
                    return False
            print(f"   💰 Real Balance: ${response.get('real_balance', 0):.2f}")
            print(f"   🎁 Bonus Balance: ${response.get('bonus_balance', 0):.2f}")
        
        return success

    def test_portal_games(self):
        """Test portal games endpoint"""
        success, response = self.run_test(
            "Portal Games API",
            "GET",
            "portal/games",
            200,
            headers={'X-Portal-Token': self.portal_token}
        )
        
        if success:
            games = response.get('games', [])
            print(f"   🎮 Found {len(games)} games")
            for game in games[:3]:  # Show first 3 games
                print(f"   - {game.get('name', 'Unknown')} (Credentials: {game.get('has_credentials', False)})")
        
        return success

    def test_load_to_game_validation(self):
        """Test load-to-game validation (should fail with insufficient balance)"""
        success, response = self.run_test(
            "Load to Game Validation",
            "POST",
            "portal/load-to-game",
            400,  # Expecting 400 for insufficient balance
            data={
                "game_id": "test-game-id",
                "amount": 1000.00,  # Large amount to trigger insufficient balance
                "wallet_type": "real"
            },
            headers={'X-Portal-Token': self.portal_token}
        )
        return success  # 400 is expected for validation error

    def test_bonus_tasks(self):
        """Test bonus tasks endpoint"""
        success, response = self.run_test(
            "Portal Bonus Tasks API",
            "GET",
            "portal/bonus-tasks",
            200,
            headers={'X-Portal-Token': self.portal_token}
        )
        
        if success:
            tasks = response.get('tasks', [])
            bonus_history = response.get('bonus_history', [])
            wallet_balance = response.get('wallet_bonus_balance', 0)
            
            print(f"   📋 Active Tasks: {len(tasks)}")
            print(f"   🏆 Bonus History: {len(bonus_history)} entries")
            print(f"   💰 Bonus Wallet: ${wallet_balance:.2f}")
            
            # Check task structure
            for task in tasks:
                if 'id' in task and 'title' in task and 'progress' in task:
                    print(f"   - {task['title']}: {task['progress']}/{task.get('target', 0)}")
        
        return success

    def test_admin_dashboard_stats(self):
        """Test admin dashboard stats with bonus distributed"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Admin Dashboard Stats",
            "GET",
            "admin/dashboard-stats",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            # Check for bonus distributed field
            bonus_distributed = response.get('total_bonus_distributed', 0)
            earnings_distributed = response.get('total_earnings_distributed', 0)
            print(f"   💰 Total Bonus Distributed: ${bonus_distributed:.2f}")
            print(f"   💸 Total Earnings Distributed: ${earnings_distributed:.2f}")
            print(f"   👥 Total Clients: {response.get('total_clients', 0)}")
            print(f"   📊 Pending Orders: {response.get('pending_orders', 0)}")
        
        return success

    def test_admin_client_detail(self):
        """Test admin client detail with wallet balances"""
        if not self.admin_token:
            return False
            
        success, response = self.run_test(
            "Admin Client Detail",
            "GET",
            f"admin/clients/{self.client_id}",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            wallet = response.get('wallet', {})
            client = response.get('client', {})
            
            print(f"   👤 Client: {client.get('display_name', 'Unknown')}")
            print(f"   💰 Real Balance: ${wallet.get('real_balance', 0):.2f}")
            print(f"   🎁 Bonus Balance: ${wallet.get('bonus_balance', 0):.2f}")
            print(f"   📈 Referral Count: {client.get('valid_referral_count', 0)}")
            print(f"   🎯 Referral Tier: {client.get('referral_tier', 0)}")
        
        return success

    def test_admin_wallet_adjustment(self):
        """Test admin wallet adjustment functionality"""
        if not self.admin_token:
            return False
            
        # Test bonus wallet adjustment
        success, response = self.run_test(
            "Admin Bonus Wallet Adjustment",
            "POST",
            f"admin/clients/{self.client_id}/adjust-wallet",
            200,
            data={
                "amount": 5.00,
                "wallet_type": "bonus",
                "reason": "Test bonus adjustment for Phase 1 testing"
            },
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            new_balances = response.get('new_balances', {})
            print(f"   ✅ Adjustment successful")
            print(f"   💰 New Real Balance: ${new_balances.get('real_balance', 0):.2f}")
            print(f"   🎁 New Bonus Balance: ${new_balances.get('bonus_balance', 0):.2f}")
        
        return success

def main():
    print("🚀 Starting Bonus Wallet System Phase 1 Testing...")
    print("=" * 60)
    
    tester = BonusWalletTester()
    
    # Test sequence
    tests = [
        ("Admin Authentication", tester.test_admin_login),
        ("Portal Token Validation", tester.test_portal_validation),
        ("Portal Wallets API", tester.test_portal_wallets),
        ("Portal Games API", tester.test_portal_games),
        ("Load to Game Validation", tester.test_load_to_game_validation),
        ("Portal Bonus Tasks API", tester.test_bonus_tasks),
        ("Admin Dashboard Stats", tester.test_admin_dashboard_stats),
        ("Admin Client Detail", tester.test_admin_client_detail),
        ("Admin Wallet Adjustment", tester.test_admin_wallet_adjustment),
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
        print("✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())