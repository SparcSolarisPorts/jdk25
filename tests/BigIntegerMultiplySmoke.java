import java.math.BigInteger;
import java.util.Random;

public class BigIntegerMultiplySmoke {
    // Independent base-256 multiplication: no BigInteger.multiply in the oracle.
    static BigInteger expected(byte[] a, byte[] b) {
        byte[] out = new byte[a.length + b.length];
        for (int i = a.length - 1; i >= 0; --i) {
            int carry = 0;
            for (int j = b.length - 1; j >= 0; --j) {
                int k = i + j + 1;
                int n = (a[i] & 255) * (b[j] & 255) + (out[k] & 255) + carry;
                out[k] = (byte)n;
                carry = n >>> 8;
            }
            out[i] = (byte)carry;
        }
        return new BigInteger(1, out);
    }
    public static void main(String[] args) {
        Random rng = new Random(21025);
        int[] limbs = {1, 2, 3, 7, 8, 15, 16, 17, 31, 32, 33, 63, 64, 65, 96};
        int cases = 0;
        for (int repeat = 0; repeat < 12; ++repeat) {
            for (int x : limbs) for (int y : limbs) {
                byte[] a = new byte[x * 4], b = new byte[y * 4];
                rng.nextBytes(a); rng.nextBytes(b);
                a[0] |= (byte)128; b[0] |= (byte)128;
                BigInteger aa = new BigInteger(1, a), bb = new BigInteger(1, b);
                BigInteger product = aa.multiply(bb);
                if (!product.equals(expected(a, b)))
                    throw new AssertionError("multiply mismatch: " + x + "/" + y + " round " + repeat);
                ++cases;
            }
        }
        System.out.println("PASS: " + cases + " BigInteger products checked independently");
    }
}
