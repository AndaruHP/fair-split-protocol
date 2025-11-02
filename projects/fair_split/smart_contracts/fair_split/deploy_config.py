import logging
import json
from pathlib import Path

import algokit_utils
from algokit_utils import get_algod_client, get_indexer_client
from algosdk.transaction import ApplicationCreateTxn, OnComplete, StateSchema, wait_for_confirmation
from algosdk import logic

logger = logging.getLogger(__name__)


def deploy() -> None:
    """
    Deploy Fair Split Protocol to the network.
    Manual deployment without using generated client.
    """
    # Get clients from environment
    algod_client = get_algod_client()

    # Get deployer account from environment
    deployer = algokit_utils.get_account(algod_client, "DEPLOYER")

    logger.info("=" * 60)
    logger.info("Deploying Fair Split Protocol")
    logger.info("=" * 60)
    logger.info(f"Deployer Address: {deployer.address}")

    # Platform address is now hardcoded in contract
    platform_address = "KO64H7YGWF6EEGP3EALQZTFR66UNYSRJLZOYGWGP5GTV2E4PBQDWFZNMIY"
    logger.info(
        f"Platform Fee Address (hardcoded in contract): {platform_address}")
    logger.info("Creating application...")

    try:
        # Get artifacts path
        artifacts_path = Path(__file__).parent.parent / \
            "artifacts" / "fair_split"

        # Read approval and clear programs
        approval_path = artifacts_path / "FairSplit.approval.teal"
        clear_path = artifacts_path / "FairSplit.clear.teal"

        if not approval_path.exists():
            raise FileNotFoundError(
                f"Approval program not found at {approval_path}")
        if not clear_path.exists():
            raise FileNotFoundError(f"Clear program not found at {clear_path}")

        logger.info("Reading TEAL programs...")
        approval_teal = approval_path.read_text()
        clear_teal = clear_path.read_text()

        # Compile programs
        logger.info("Compiling programs...")
        approval_result = algod_client.compile(approval_teal)
        clear_result = algod_client.compile(clear_teal)

        # Convert base64 string to bytes
        import base64
        approval_program = base64.b64decode(approval_result["result"])
        clear_program = base64.b64decode(clear_result["result"])

        # Get suggested params
        params = algod_client.suggested_params()

        # Manual schema based on FairSplit contract state variables
        # UInt64: spouse_1_points, spouse_2_points, total_pool, platform_fee_basis_points = 4
        # Bytes: spouse_1, spouse_2, contract_status, spouse_1_approved, spouse_2_approved, platform_address = 6
        global_uints = 4
        global_bytes = 6
        local_uints = 0
        local_bytes = 0

        logger.info(
            f"Schema: Global({global_uints}u, {global_bytes}b), Local({local_uints}u, {local_bytes}b)")

        # Calculate method selector from signature (no parameters now)
        from algosdk.abi import Method
        from algosdk import encoding

        method_obj = Method.from_signature("create_contract()string")
        method_selector = method_obj.get_selector()
        logger.info(f"Using method selector: {method_selector.hex()}")

        # Only method selector needed - no arguments
        app_args = [
            method_selector,
        ]

        logger.info("Creating application transaction...")
        txn = ApplicationCreateTxn(
            sender=deployer.address,
            sp=params,
            on_complete=OnComplete.NoOpOC,
            approval_program=approval_program,
            clear_program=clear_program,
            global_schema=StateSchema(
                num_uints=global_uints,
                num_byte_slices=global_bytes,
            ),
            local_schema=StateSchema(
                num_uints=local_uints,
                num_byte_slices=local_bytes,
            ),
            app_args=app_args,
        )

        # Sign and send
        logger.info("Signing and sending transaction...")
        signed_txn = txn.sign(deployer.private_key)
        tx_id = algod_client.send_transaction(signed_txn)

        logger.info(f"Transaction sent with ID: {tx_id}")
        logger.info("Waiting for confirmation...")

        # Wait for confirmation
        confirmed_txn = wait_for_confirmation(algod_client, tx_id, 4)

        # Get app ID
        app_id = confirmed_txn.get("application-index")
        app_address = logic.get_application_address(app_id)

        logger.info("=" * 60)
        logger.info("✅ Deployment Successful!")
        logger.info("=" * 60)
        logger.info(f"App ID: {app_id}")
        logger.info(f"App Address: {app_address}")
        logger.info(f"Spouse 1 (Creator): {deployer.address}")
        logger.info(f"Platform Address: {platform_address}")
        logger.info(f"Transaction ID: {tx_id}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📝 Next Steps:")
        logger.info("1. Opt-in both spouses (if needed)")
        logger.info("2. Invite Spouse 2 using invite_spouse method")
        logger.info("3. Spouse 2 accepts using accept_invite method")
        logger.info("4. Both spouses can deposit using deposit method")
        logger.info("")
        logger.info(f"📱 View on AlgoExplorer:")
        logger.info(f"   https://testnet.algoexplorer.io/application/{app_id}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ Deployment Failed!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        logger.error("=" * 60)
        raise
