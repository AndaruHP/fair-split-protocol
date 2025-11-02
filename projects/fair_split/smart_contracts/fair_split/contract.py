from algopy import ARC4Contract, Account, Global, gtxn, UInt64, Txn, op, arc4, itxn, subroutine


class FairSplit(ARC4Contract):
    """
    Fair Split Protocol - Marriage Asset Management Smart Contract
    
    Features:
    - Couple registration and invitation system
    - Deposit tracking with tiered point system
    - Mutual approval withdrawal mechanism
    - Automatic asset distribution based on points ratio
    - Platform fee deduction (6.5%)
    """
    
    def __init__(self) -> None:
        self.spouse_1 = Account()
        self.spouse_2 = Account()

        self.spouse_1_points = UInt64(0)
        self.spouse_2_points = UInt64(0)

        self.total_pool = UInt64(0)

        self.contract_status = arc4.String()

        self.spouse_1_approved = arc4.Bool(False)
        self.spouse_2_approved = arc4.Bool(False)

        self.platform_address = Account()
        self.platform_fee_basis_points = UInt64(650) # 6.5%
    
    @arc4.abimethod(allow_actions=["NoOp"], create="require")
    def create_contract(self, platform_addr: Account) -> arc4.String:
        """
        Initialize contract - called by Spouse 1
        
        Args:
            platform_addr: Address to receive platform fees
        
        Returns:
            Status message
        """

        self.spouse_1 = Txn.sender
        self.spouse_2 = Global.zero_address

        self.spouse_1_points = UInt64(0)
        self.spouse_2_points = UInt64(0)
        self.total_pool = UInt64(0)

        self.contract_status = arc4.String("pending_invite")

        self.spouse_1_approved = arc4.Bool(False)
        self.spouse_2_approved = arc4.Bool(False)

        self.platform_address = platform_addr

        return arc4.String("Contract created. Wait for spouse invitation.")
    
    @arc4.abimethod
    def invite_spouse(self, spouse_address: Account) -> arc4.String:
        """
        Invite second spouse - only callable by spouse 1
        
        Args:
            spouse_address: Address of spouse 2 to invite
        
        Returns:
            Status message
        """

        assert Txn.sender == self.spouse_1

        assert self.contract_status == arc4.String("pending_invite"), "Contract not in pending_invite state"

        assert self.spouse_2 == Global.zero_address, "Spouse 2 already invited"

        assert spouse_address != self.spouse_1, "Cannot invite yourself"

        self.spouse_2 = spouse_address

        return arc4.String("Spouse invited. Waiting for acceptance.")
    
    @arc4.abimethod
    def accept_invite(self) -> arc4.String:
        """
        Accept invitation - only callable by invited spouse 2
        
        Returns:
            Status message
        """

        assert Txn.sender == self.spouse_2, "Only invited spouse can accept"

        assert self.contract_status == arc4.String("pending_invite"), "Contract not in pending_invite state"

        self.contract_status = arc4.String("active")
        
        return arc4.String("Invitation accepted. Contract is now active.")
    
    @arc4.abimethod
    def deposit(self, payment: gtxn.PaymentTransaction) -> arc4.String:
        """
        Deposit ALGO to pool and earn points based on tiered system
        
        Point System:
        - < 5 ALGO: 0.5 points
        - >= 5 and < 10 ALGO: 0.75 points
        - >= 10 ALGO: floor(amount / 20) points
        
        Args:
            payment: Payment transaction to contract
        
        Returns:
            Status message with points earned
        """

        assert self.contract_status == arc4.String("active"), "Contract must be active"
        
        assert (Txn.sender == self.spouse_1) or (Txn.sender == self.spouse_2), "Only spouses can deposit"
        
        assert payment.receiver == Global.current_application_address, "Payment must be to contract"

        amount_micro = payment.amount
        amount_algo = amount_micro // UInt64(1_000_000)

        points_earned = self._calculate_points(amount_algo)

        self.total_pool += amount_micro
        
        if Txn.sender == self.spouse_1:
            self.spouse_1_points += points_earned
            return arc4.String("Spouse 1 deposit success")
        else:
            self.spouse_2_points += points_earned
            return arc4.String("Spouse 2 deposit success")
    
    @subroutine
    def _calculate_points(self, amount_algo: UInt64) -> UInt64:
        """
        Calculate points based on deposit amount
        
        Args:
            amount_algo: Deposit amount in ALGO
        
        Returns:
            Points earned (in 100x precision, e.g., 50 = 0.5 points)
        """

        if amount_algo < UInt64(5):
            return UInt64(50)
        elif amount_algo < UInt64(10):
            return UInt64(75)
        else:
            return (amount_algo // UInt64(20)) * UInt64(100)
        

    @arc4.abimethod
    def request_withdrawal(self) -> arc4.String:
        """
        Request withdrawal - initiates the divorce/split process
        Can be called by either spouse
        
        Returns:
            Status message
        """

        assert self.contract_status == arc4.String("active"), "Contract must be active"

        assert (Txn.sender == self.spouse_1) or (Txn.sender == self.spouse_2), "Only spouse can request withdrawal"

        self.contract_status = arc4.String("pending_withdrawal")

        self.spouse_1_approved = arc4.Bool(False)
        self.spouse_2_approved = arc4.Bool(False)

        return arc4.String("Withdrawal requested. Both spouses must approve.")
    
    @arc4.abimethod
    def approve_withdrawal(self) -> arc4.String:
        """
        Approve withdrawal - both spouses must call this
        When both approve, automatic distribution is triggered
        
        Returns:
            Status message
        """

        assert self.contract_status == arc4.String("pending_withdrawal"), "No withdrawal pending"
        
        assert (Txn.sender == self.spouse_1) or (Txn.sender == self.spouse_2), "Only spouses can approve"

        if Txn.sender == self.spouse_1:
            assert not self.spouse_1_approved.native, "Spouse 1 already approved"
            self.spouse_1_approved = arc4.Bool(True)
            
            if self.spouse_2_approved.native:
                self._distribute_funds()
                return arc4.String("Both approved. Funds distributed.")
            else:
                return arc4.String("Spouse 1 approved. Waiting for spouse 2.")
        else:
            assert not self.spouse_2_approved.native, "Spouse 2 already approved"
            self.spouse_2_approved = arc4.Bool(True)
            
            if self.spouse_1_approved.native:
                self._distribute_funds()
                return arc4.String("Both approved. Funds distributed.")
            else:
                return arc4.String("Spouse 2 approved. Waiting for spouse 1.")
    
    @subroutine
    def _distribute_funds(self) -> None:
        """
        Internal function to distribute funds based on points ratio
        Deducts 6.5% platform fee first
        """

        total_points = self.spouse_1_points + self.spouse_2_points

        assert total_points > UInt64(0), "No points to distribute"

        platform_fee = (self.total_pool * self.platform_fee_basis_points) // UInt64(10_000)

        distributable_amount = self.total_pool - platform_fee

        spouse_1_share = (distributable_amount * self.spouse_1_points) // total_points
        spouse_2_share = distributable_amount - spouse_1_share

        if platform_fee > UInt64(0):
            itxn.Payment(
                receiver=self.platform_address,
                amount=platform_fee,
                fee=UInt64(0)
            ).submit()

        if spouse_1_share > UInt64(0):
            itxn.Payment(
                receiver=self.spouse_1,
                amount=spouse_1_share,
                fee=UInt64(0),
            ).submit()
        
        if spouse_2_share > UInt64(0):
            itxn.Payment(
                receiver=self.spouse_2,
                amount=spouse_2_share,
                fee=UInt64(0),
            ).submit()
        
        self.contract_status = arc4.String("completed")

        self.total_pool = UInt64(0)
        self.spouse_1_points = UInt64(0)
        self.spouse_2_points = UInt64(0)
    
    @arc4.abimethod
    def get_contract_info(self) -> tuple[arc4.String, arc4.Address, arc4.Address, arc4.UInt64, arc4.UInt64, arc4.UInt64]:
        """
        Get current contract information
        
        Returns:
            Tuple of (status, spouse_1, spouse_2, spouse_1_points, spouse_2_points, total_pool)
        """
        
        return (
            self.contract_status,
            arc4.Address(self.spouse_1),
            arc4.Address(self.spouse_2),
            arc4.UInt64(self.spouse_1_points),
            arc4.UInt64(self.spouse_2_points),
            arc4.UInt64(self.total_pool)
        )