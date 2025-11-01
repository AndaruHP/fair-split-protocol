from algopy import ARC4Contract, UInt64, Account, Txn, Global, String
from algopy.arc4 import abimethod
from algopy import itxn  # ✅ Perbaikan: import itxn module, bukan Itxn class


class FairSplit(ARC4Contract):
    """
    FairSplitV2 — Fair split between two partners based on deposits and earned points.
    """

    def __init__(self) -> None:
        self.partner1 = Account()
        self.partner2 = Account()
        self.p1_points = UInt64(0)
        self.p2_points = UInt64(0)

    @abimethod()
    def setup(self, p1: Account, p2: Account) -> String:
        """Initialize partners."""
        self.partner1 = p1
        self.partner2 = p2
        self.p1_points = UInt64(0)
        self.p2_points = UInt64(0)
        return String("Partners set successfully!")

    @abimethod()
    def deposit(self) -> String:
        """
        Called when a partner deposits Algo into the contract.
        Calculates contribution points based on deposit amount.
        """
        sender = Txn.sender
        amount_micro = Txn.amount
        amount_algo = amount_micro // UInt64(1_000_000)

        points_earned = UInt64(0)
        if amount_algo >= UInt64(10):
            points_earned = UInt64(2)
        elif amount_algo >= UInt64(5):
            points_earned = UInt64(1)
        elif amount_algo > UInt64(0):
            points_earned = UInt64(1)

        if sender == self.partner1:
            self.p1_points = self.p1_points + points_earned
        elif sender == self.partner2:
            self.p2_points = self.p2_points + points_earned
        else:
            return String("Sender not a registered partner!")

        return String("Deposit recorded and points updated!")

    @abimethod()
    def calculate(self) -> String:
        """
        Split contract balance based on accumulated points.
        """
        total_balance = Global.current_application_address.balance
        # ✅ Perbaikan: balance adalah property, bukan method (tanpa ())

        total_points = self.p1_points + self.p2_points
        if total_points == UInt64(0):
            return String("No deposits recorded yet.")

        p1_share = (total_balance * self.p1_points) // total_points
        p2_share = (total_balance * self.p2_points) // total_points

        # ✅ Perbaikan: gunakan itxn.Payment (huruf kapital P)
        itxn.Payment(
            receiver=self.partner1,
            amount=p1_share,
            fee=UInt64(0),  # gunakan UInt64(0) untuk inner transaction
        ).submit()

        itxn.Payment(
            receiver=self.partner2,
            amount=p2_share,
            fee=UInt64(0),
        ).submit()

        return String("Split complete.")