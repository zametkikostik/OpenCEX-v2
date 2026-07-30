// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}
contract OpenCEXSettlementV2 {
    string public constant name = "OpenCEX"; string public constant version = "2";
    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant ORDER_TYPEHASH = keccak256("Order(address maker,address sellToken,address buyToken,uint256 sellAmount,uint256 buyAmount,uint256 nonce,uint256 expiry,uint256 salt)");
    address public owner; address public feeRecipient; uint16 public feeBps; uint16 public constant MAX_FEE_BPS = 100;
    mapping(bytes32 => uint256) public filled; mapping(address => mapping(uint256 => bool)) public cancelled;
    struct Order { address maker; address sellToken; address buyToken; uint256 sellAmount; uint256 buyAmount; uint256 nonce; uint256 expiry; uint256 salt; }
    event OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker, uint256 sellAmount, uint256 buyAmount, uint256 protocolFee);
    event FeeConfigUpdated(address recipient, uint16 feeBps);
    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
    constructor(address _feeRecipient, uint16 _feeBps) {
        require(_feeBps <= MAX_FEE_BPS, "fee"); owner = msg.sender; feeRecipient = _feeRecipient; feeBps = _feeBps;
        uint256 chainId; assembly { chainId := chainid() }
        DOMAIN_SEPARATOR = keccak256(abi.encode(keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"), keccak256(bytes(name)), keccak256(bytes(version)), chainId, address(this)));
    }
    function setFeeConfig(address r, uint16 b) external onlyOwner { require(b <= MAX_FEE_BPS && r != address(0)); feeRecipient = r; feeBps = b; emit FeeConfigUpdated(r, b); }
    function hashOrder(Order calldata o) public view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, keccak256(abi.encode(ORDER_TYPEHASH, o.maker, o.sellToken, o.buyToken, o.sellAmount, o.buyAmount, o.nonce, o.expiry, o.salt))));
    }
    function fillOrder(Order calldata o, bytes calldata signature) external returns (uint256) {
        require(block.timestamp < o.expiry, "expired"); require(!cancelled[o.maker][o.nonce], "cancelled");
        bytes32 orderHash = hashOrder(o); require(filled[orderHash] == 0, "filled"); require(_recover(orderHash, signature) == o.maker, "bad sig");
        filled[orderHash] = o.sellAmount;
        uint256 fee = (o.sellAmount * uint256(feeBps)) / 10000; uint256 toTaker = o.sellAmount - fee;
        require(IERC20(o.buyToken).transferFrom(msg.sender, o.maker, o.buyAmount), "buy");
        require(IERC20(o.sellToken).transferFrom(o.maker, msg.sender, toTaker), "sell");
        if (fee > 0) require(IERC20(o.sellToken).transferFrom(o.maker, feeRecipient, fee), "fee");
        emit OrderFilled(orderHash, o.maker, msg.sender, o.sellAmount, o.buyAmount, fee); return toTaker;
    }
    function cancelOrder(uint256 nonce) external { cancelled[msg.sender][nonce] = true; }
    function _recover(bytes32 digest, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "sig"); bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset); s := calldataload(add(sig.offset, 32)); v := byte(0, calldataload(add(sig.offset, 64))) }
        if (v < 27) v += 27; return ecrecover(digest, v, r, s);
    }
}
