public class ArrayCopyDirectionSmoke {
    static void copy(Object src, int s, Object dst, int d, int n) {
        System.arraycopy(src, s, dst, d, n);
    }
    public static void main(String[] args) {
        for (int round = 0; round < 50; round++) {
            for (int s = 0; s < 12; s++) for (int d = 0; d < 12; d++) {
                for (int n = 0; n <= 24; n++) {
                    int[] ints = new int[64];
                    long[] longs = new long[64];
                    for (int i = 0; i < 64; i++) {
                        ints[i] = i * 0x1234567;
                        longs[i] = 0x1234567800000000L + i;
                    }
                    copy(ints, s, ints, d, n);
                    copy(longs, s, longs, d, n);
                    for (int i = 0; i < 64; i++) {
                        int original = i >= d && i < d + n ? s + i - d : i;
                        if (ints[i] != original * 0x1234567
                                || longs[i] != 0x1234567800000000L + original) {
                            throw new AssertionError("same array s="+s+" d="+d+" n="+n+" index="+i);
                        }
                    }
                    int[] dstI = new int[64];
                    long[] dstL = new long[64];
                    copy(ints, s, dstI, d, n);
                    copy(longs, s, dstL, d, n);
                    for (int i = 0; i < 64; i++) {
                        int ei = i >= d && i < d + n ? ints[s + i - d] : 0;
                        long el = i >= d && i < d + n ? longs[s + i - d] : 0;
                        if (dstI[i] != ei || dstL[i] != el) throw new AssertionError("distinct arrays");
                    }
                }
            }
        }
        System.out.println("PASS: int/long arraycopy, overlap in both directions, same range, zero length, distinct arrays");
    }
}
