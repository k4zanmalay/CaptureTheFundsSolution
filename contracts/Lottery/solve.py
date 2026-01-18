def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)


def modinv(a, m):
    g, x, _ = egcd(a, m)
    if g != 1:
        raise ValueError("No modular inverse")
    return x % m


def tonelli_shanks(n, p):
    """
    Solve x^2 = n (mod p), p prime.
    Returns one root x; the other is p-x.
    """
    assert pow(n, (p - 1) // 2, p) == 1, "Not a quadratic residue"

    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)

    # Factor p-1 = q * 2^s with q odd
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1

    # Find z, a quadratic non-residue
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1

    c = pow(z, q, p)
    x = pow(n, (q + 1) // 2, p)
    t = pow(n, q, p)
    m = s

    while t != 1:
        i = 1
        temp = pow(t, 2, p)
        while temp != 1:
            temp = pow(temp, 2, p)
            i += 1

        b = pow(c, 1 << (m - i - 1), p)
        x = (x * b) % p
        t = (t * b * b) % p
        c = (b * b) % p
        m = i

    return x


def crt(a1, m1, a2, m2):
    """
    Solve:
      x = a1 (mod m1)
      x = a2 (mod m2)
    """
    inv = modinv(m1, m2)
    t = (a2 - a1) * inv % m2
    return a1 + t * m1


def solve_mulmod(magic, p, q):
    N = p * q

    # Roots mod p and q
    rp = tonelli_shanks(magic % p, p)
    rq = tonelli_shanks(magic % q, q)

    roots = set()

    for sp in (rp, p - rp):
        for sq in (rq, q - rq):
            x = crt(sp, p, sq, q) % N
            roots.add(x)

    return list(roots)


# -----------------------------
# Example usage
# -----------------------------
magic = 93740
p = 203397122864352332654381286768283559441  # first prime factor
q = 460873158062510114581873162474391926043  # second prime factor

solutions = solve_mulmod(magic, p, q)

print("Valid x values:")
for x in solutions:
    print(x)
    assert (x * x) % (p * q) == magic
