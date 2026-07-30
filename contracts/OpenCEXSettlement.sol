// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
/** OpenCEX NC settlement — proprietary commercial license */
interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}
contract OpenCEXSettlement {
    string public constant name = "OpenCEX";
    string public constant version = "1";
    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant ORDER_TYPEHASH = keccak256("Order(address maker,address sellToken,address buyToken,uint256 sellAmount,uint256 buyAmount,uint256 nonce,uint256 expiry,uint256 salt)");
    mapping(bytes32 => uint256) public filled;
    mapping(address => mapping(uint256 => bool)) public cancelled;
    struct Order { address maker; address sellToken; address buyToken; uint256 sellAmount; uint256 buyAmount; uint256 nonce; uint256 expiry; uint256 salt; }
    event OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker, uint256 sellAmount, uint256 buyAmount);
    constructor() {
        uint256 chainId; assembly { chainId := chainid() }
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes(name)), keccak256(bytes(version)), chainId, address(this)));
    }
    function hashOrder(Order calldata o) public view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, keccak256(abi.encode(
            ORDER_TYPEHASH, o.maker, o.sellToken, o.buyToken, o.sellAmount, o.buyAmount, o.nonce, o.expiry, o.salt))));
    }
    function fillOrder(Order calldata o, bytes calldata signature) external returns (uint256) {
        require(block.timestamp < o.expiry, "expired");
        require(!cancelled[o.maker][o.nonce], "cancelled");
        bytes32 orderHash = hashOrder(o);
        require(filled[orderHash] == 0, "filled");
        require(_recover(orderHash, signature) == o.maker, "bad sig");
        filled[orderHash] = o.sellAmount;
        require(IERC20(o.buyToken).transferFrom(msg.sender, o.maker, o.buyAmount), "buy");
        require(IERC20(o.sellToken).transferFrom(o.maker, msg.sender, o.sellAmount), "sell");
        emit OrderFilled(orderHash, o.maker, msg.sender, o.sellAmount, o.buyAmount);
        return o.sellAmount;
    }
    function cancelOrder(uint256 nonce) external { cancelled[msg.sender][nonce] = true; }
    function _recover(bytes32 digest, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "sig");
        bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset); s := calldataload(add(sig.offset, 32)); v := byte(0, calldataload(add(sig.offset, 64))) }
        if (v < 27) v += 27;
        return ecrecover(digest, v, r, s);
    }
}
