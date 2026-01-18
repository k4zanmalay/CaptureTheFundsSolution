### Vulnerabilities

1. Collateral value is calculated directly from the pool’s reserves:
```solidity
    function _getCollateral(Position storage pos, AssetType assetType) internal view returns (
        uint256 shares,
        uint256 underlying,
        uint256 usdValue
    ) {
        (ILendingPool pool, IERC20 asset,,) = _getPoolAndAsset(assetType);
        
        if (assetType == AssetType.A) {
            shares = pos.collateralAShares;
        } else {
            shares = pos.collateralBShares;
        }
        
 >>>    underlying = pool.convertToAssets(shares);
        uint8 decimals = IERC20Metadata(address(asset)).decimals();
        usdValue = (underlying * priceOracle.getPrice(asset)) / (10 ** decimals);
    }
```
The `poolCash` value can be manipulated using a flash loan:
```solidity
    function _convertToAssets(uint256 shares, Math.Rounding rounding) internal view virtual returns (uint256) {
        return shares.mulDiv(totalAssets() + 1, totalSupply() + 10 ** _decimalsOffset(), rounding);
    }

    function totalAssets() public view override(ERC4626, IERC4626) returns (uint256) {
>>>     uint256 poolCash = _poolCash;
        uint256 currentDebt = (totalBorrowNormalized * index) / 1e18;
        return poolCash + currentDebt;
    }
```
By withdrawing a large amount of funds via a flash loan, an attacker can significantly reduce the apparent collateral value, pushing active loans underwater:
```solidity
    function flashloanWithdraw(uint256 amount) external onlyFlashloanContract nonReentrant returns (uint256) {
        require(amount <= _poolCash, "LendingPool: Not enough cash for flashloan");
        _flashloanActive = true;  // Mark flashloan as active
>>>     _poolCash -= amount;
        IERC20(asset()).safeTransfer(msg.sender, amount);
        return amount;
    }
```

2. The `_flashloanActive` guard that is supposed to block interactions during a flash loan can be reset by repaying a tiny amount of the loan:
```solidity
    function flashloanReturn(uint256 amount) external onlyFlashloanContract nonReentrant {
        _poolCash += amount;
>>>     _flashloanActive = false;  // Mark flashloan as complete
    }
```
3. Flash loan fees can be minimized by nesting flash loans inside each other:
```solidity
    function flashloan(
        IERC20 asset,
        uint256 amount,
        address receiver,
        bytes calldata data
    ) external {
        ---SNIP---

        IERC20 token = asset;
        // The contract should start with zero balance for this asset.
        uint256 initialBalance = token.balanceOf(address(this));

        // Add 1 wei instead of rounding up. It’s preferable for the user to slightly overpay to avoid rounding logic and reduce gas overhead.
        uint256 fee = (amount * flashloanFee) / 10000 + 1;
        // Transfer the requested amount to the receiver.
        token.safeTransfer(receiver, amount);

        ---SNIP---

        // After callback, the contract must have recovered at least its original balance plus the fee.
>>>     require(token.balanceOf(address(this)) >= initialBalance + fee, "FlashLoaner: Insufficient repayment");
```
For example, borrowing 10,000 USDC with a 5% fee requires repaying 10,500 USDC.
Instead, you can borrow 5,000 USDC, then borrow another 5,000 USDC inside the first loan’s callback, repay the inner loan, and end up repaying only 10,250 USDC total. By nesting even deeper, the fees can be reduced further.

### Attack

The flow is mostly the same across all pools. The main goal is to drain the pools and force `CommunityInsurance` to cover the losses, effectively draining it as well:
1. Pick a pool and check if there are loans that can be liquidated by `CommunityInsurance`. If the loan size is too small, borrow more to make it worthwhile.
2. Take a flash loan of the collateral asset whose price you want to push down.
3. Once the position becomes liquidatable, call `CommunityInsurance.liquidateBadDebt` in the callback.
4. Repeat for all pools

This attack is fairly tricky and comes with a lot of caveats. You need to carefully manage repayments, collateral, and debt token values so that `CommunityInsurance` doesn’t receive any assets when it redeems the debt pool shares it gets during liquidation. For a clearer picture, it’s best to look directly at the implementation in `solution.sol`.
