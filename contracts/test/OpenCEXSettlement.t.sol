// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
import "../OpenCEXSettlement.sol";

contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    function mint(address to, uint256 amount) external { balanceOf[to] += amount; }
    function approve(address spender, uint256 amount) external returns (bool) { allowance[msg.sender][spender] = amount; return true; }
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(allowance[from][msg.sender] >= amount, "allow");
        allowance[from][msg.sender] -= amount;
        require(balanceOf[from] >= amount, "bal");
        balanceOf[from] -= amount; balanceOf[to] += amount; return true;
    }
}

contract OpenCEXSettlementTest is Test {
    OpenCEXSettlement internal settlement;
    MockERC20 internal sellToken;
    MockERC20 internal buyToken;
    uint256 internal makerPk = 0xA11CE;
    address internal maker;
    address internal taker = address(0xB0B);

    function setUp() public {
        settlement = new OpenCEXSettlement();
        sellToken = new MockERC20(); buyToken = new MockERC20();
        maker = vm.addr(makerPk);
        sellToken.mint(maker, 1000 ether); buyToken.mint(taker, 1000 ether);
        vm.prank(maker); sellToken.approve(address(settlement), type(uint256).max);
        vm.prank(taker); buyToken.approve(address(settlement), type(uint256).max);
    }

    function _order(uint256 sa, uint256 ba, uint256 nonce, uint256 expiry) internal view returns (OpenCEXSettlement.Order memory) {
        return OpenCEXSettlement.Order(maker, address(sellToken), address(buyToken), sa, ba, nonce, expiry, 1);
    }

    function _sign(OpenCEXSettlement.Order memory o) internal view returns (bytes memory) {
        bytes32 digest = settlement.hashOrder(o);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(makerPk, digest);
        return abi.encodePacked(r, s, v);
    }

    function test_FillOrder_Success() public {
        OpenCEXSettlement.Order memory o = _order(10 ether, 20 ether, 1, block.timestamp + 1 days);
        vm.prank(taker);
        assertEq(settlement.fillOrder(o, _sign(o)), 10 ether);
        assertEq(sellToken.balanceOf(taker), 10 ether);
        assertEq(buyToken.balanceOf(maker), 20 ether);
    }

    function test_FillOrder_RevertExpired() public {
        OpenCEXSettlement.Order memory o = _order(1 ether, 1 ether, 2, block.timestamp - 1);
        vm.prank(taker); vm.expectRevert("expired"); settlement.fillOrder(o, _sign(o));
    }

    function test_FillOrder_RevertBadSig() public {
        OpenCEXSettlement.Order memory o = _order(1 ether, 1 ether, 3, block.timestamp + 1 days);
        bytes32 digest = settlement.hashOrder(o);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(0xDEAD, digest);
        vm.prank(taker); vm.expectRevert("bad sig"); settlement.fillOrder(o, abi.encodePacked(r, s, v));
    }

    function test_FillOrder_RevertDoubleFill() public {
        OpenCEXSettlement.Order memory o = _order(1 ether, 1 ether, 4, block.timestamp + 1 days);
        bytes memory sig = _sign(o);
        vm.prank(taker); settlement.fillOrder(o, sig);
        vm.prank(taker); vm.expectRevert("filled"); settlement.fillOrder(o, sig);
    }

    function test_CancelOrder() public {
        vm.prank(maker); settlement.cancelOrder(99);
        OpenCEXSettlement.Order memory o = _order(1 ether, 1 ether, 99, block.timestamp + 1 days);
        vm.prank(taker); vm.expectRevert("cancelled"); settlement.fillOrder(o, _sign(o));
    }

    function test_HashOrder_Stable() public {
        OpenCEXSettlement.Order memory o = _order(1, 1, 1, block.timestamp + 1);
        assertEq(settlement.hashOrder(o), settlement.hashOrder(o));
    }
}
