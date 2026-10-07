import java.util.Arrays;

public class CompactStringEqualsSmoke {
    private static volatile int sink;
    private static void check(byte[] a, byte[] b, char[] ca, char[] cb, boolean equal) {
        if (Arrays.equals(a, b) != equal || Arrays.equals(ca, cb) != equal
                || new String(ca).equals(new String(cb)) != equal) {
            throw new AssertionError("Equality mismatch, length=" + a.length);
        }
        sink++;
    }
    public static void main(String[] args) {
        for (int round = 0; round < 300; round++) {
            for (int len = 0; len <= 129; len++) {
                byte[] a = new byte[len];
                char[] ca = new char[len];
                for (int i = 0; i < len; i++) {
                    a[i] = (byte)(i * 37 + round);
                    ca[i] = (char)((round & 1) == 0 ? (i * 37 & 255) : 0x400 + i);
                }
                byte[] b = a.clone();
                char[] cb = ca.clone();
                check(a, b, ca, cb, true);
                for (int i = 0; i < len; i++) {
                    b[i] ^= 1;
                    cb[i] ^= 1;
                    check(a, b, ca, cb, false);
                    b[i] ^= 1;
                    cb[i] ^= 1;
                }
            }
        }
        if ("abc".equals(null) || "abc".equals(new Object())
                || "abc".equals("abcd") || !Arrays.equals((byte[])null, null)) {
            throw new AssertionError("Edge case mismatch");
        }
        System.out.println("PASS: Latin1/UTF16 strings and byte/char arrays, every mismatch position; " + sink + " checks");
    }
}
