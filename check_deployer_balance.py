"""
Script to check DEPLOYER account balance
"""
import algokit_utils
from algokit_utils import get_algod_client

def check_balance():
    # Get algod client
    algod_client = get_algod_client()
    
    # Get deployer account
    deployer = algokit_utils.get_account(algod_client, "DEPLOYER")
    
    print("=" * 60)
    print("DEPLOYER Account Info")
    print("=" * 60)
    print(f"Address: {deployer.address}")
    
    # Get account info
    account_info = algod_client.account_info(deployer.address)
    
    balance = account_info.get('amount', 0)
    min_balance = account_info.get('min-balance', 0)
    
    print(f"\nCurrent Balance: {balance:,} microAlgos ({balance / 1_000_000:.6f} ALGO)")
    print(f"Minimum Required: {min_balance:,} microAlgos ({min_balance / 1_000_000:.6f} ALGO)")
    print(f"Available (spendable): {balance - min_balance:,} microAlgos ({(balance - min_balance) / 1_000_000:.6f} ALGO)")
    
    # Check if account needs funding
    # For app creation, we need at least 0.1 ALGO for transaction fee + MBR increase
    recommended_balance = min_balance + 2_000_000  # MBR + 2 ALGO buffer
    
    print(f"\nRecommended Balance: {recommended_balance:,} microAlgos ({recommended_balance / 1_000_000:.6f} ALGO)")
    
    if balance < min_balance:
        print("\n⚠️  WARNING: Balance is below minimum! Account cannot transact.")
        print(f"   Need at least: {(min_balance - balance) / 1_000_000:.6f} ALGO")
    elif balance < recommended_balance:
        print("\n⚠️  WARNING: Balance is low for app deployment.")
        print(f"   Recommended to add: {(recommended_balance - balance) / 1_000_000:.6f} ALGO")
    else:
        print("\n✅ Balance is sufficient for deployment!")
    
    print("\n" + "=" * 60)
    print("To fund this account on TestNet:")
    print(f"1. Visit: https://bank.testnet.algorand.network/")
    print(f"2. Paste address: {deployer.address}")
    print("=" * 60)

if __name__ == "__main__":
    check_balance()

