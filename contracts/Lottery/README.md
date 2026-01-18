### Vulnerabilities

The magic numbers can be derived using the following algorithm:

1. Each number `N` is a composite of two prime numbers `p` and `q`
2. Compute square roots of `magic` modulo `p` and modulo `q`.
3. Combine the roots using the Chinese Remainder Theorem to obtain valid `x` modulo `N`.
4. Any resulting `x` satisfies `mulmod(x, x, N) == magic`.

### Attack

1. There’s a cheeky signature collision between `Lottery` and `LotteryExtension` that prevents some `solveMulMod` functions from being usable.
2. Go to `factordb.com`, paste in `N`, and retrieve its prime factors.
3. Plug the `magic` value along with `p` and `q` into `solve.py` and run it.
4. Use the resulting `x` as the argument to `solveMulMod`:

```solidity
        ILotteryExtension(address(lottery)).solveMulmod93740(0, 22944716803525420696533866530183787158952213232330281032959477737241389970872);
        ILotteryExtension(address(lottery)).solveMulmod90174(1, 40289530849315046632803046237695507888814621779004955301521665942329666711931);
        ILotteryExtension(address(lottery)).solveMulmod89443(2, 25763313276182728748094861671409962815748632632615992537054984139247576418966);
```
