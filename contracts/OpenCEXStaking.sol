// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}
contract OpenCEXStaking {
    IERC20 public immutable stakingToken; IERC20 public immutable rewardToken;
    address public owner; uint256 public rewardRatePerSecond; uint256 public totalStaked; uint256 public minLockSeconds;
    struct Position { uint256 amount; uint256 rewardDebt; uint256 unlockAt; }
    mapping(address => Position) public positions;
    uint256 public accRewardPerShare; uint256 public lastUpdate;
    event Staked(address indexed user, uint256 amount, uint256 unlockAt);
    event Unstaked(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 amount);
    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
    constructor(address _staking, address _reward, uint256 _minLock) {
        stakingToken = IERC20(_staking); rewardToken = IERC20(_reward); owner = msg.sender; minLockSeconds = _minLock; lastUpdate = block.timestamp;
    }
    function setRewardRate(uint256 rate) external onlyOwner { _updatePool(); rewardRatePerSecond = rate; }
    function _updatePool() internal {
        if (block.timestamp <= lastUpdate) return;
        if (totalStaked > 0 && rewardRatePerSecond > 0) {
            accRewardPerShare += ((block.timestamp - lastUpdate) * rewardRatePerSecond * 1e18) / totalStaked;
        }
        lastUpdate = block.timestamp;
    }
    function stake(uint256 amount) external {
        require(amount > 0); _updatePool(); Position storage p = positions[msg.sender];
        if (p.amount > 0) {
            uint256 pending = (p.amount * accRewardPerShare) / 1e18 - p.rewardDebt;
            if (pending > 0) { rewardToken.transfer(msg.sender, pending); emit RewardClaimed(msg.sender, pending); }
        }
        require(stakingToken.transferFrom(msg.sender, address(this), amount));
        p.amount += amount; p.rewardDebt = (p.amount * accRewardPerShare) / 1e18;
        p.unlockAt = block.timestamp + minLockSeconds; totalStaked += amount;
        emit Staked(msg.sender, amount, p.unlockAt);
    }
    function unstake(uint256 amount) external {
        Position storage p = positions[msg.sender]; require(p.amount >= amount && block.timestamp >= p.unlockAt);
        _updatePool();
        uint256 pending = (p.amount * accRewardPerShare) / 1e18 - p.rewardDebt;
        p.amount -= amount; p.rewardDebt = (p.amount * accRewardPerShare) / 1e18; totalStaked -= amount;
        if (pending > 0) { rewardToken.transfer(msg.sender, pending); emit RewardClaimed(msg.sender, pending); }
        require(stakingToken.transfer(msg.sender, amount)); emit Unstaked(msg.sender, amount);
    }
    function claim() external {
        _updatePool(); Position storage p = positions[msg.sender];
        uint256 pending = (p.amount * accRewardPerShare) / 1e18 - p.rewardDebt;
        p.rewardDebt = (p.amount * accRewardPerShare) / 1e18; require(pending > 0);
        rewardToken.transfer(msg.sender, pending); emit RewardClaimed(msg.sender, pending);
    }
}
