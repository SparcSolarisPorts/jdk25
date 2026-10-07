import java.util.Arrays;

/** Checks allocation, cloning and copies against element-by-element results. */
public class ArrayHeaderSmoke {
    static volatile Object escaped;
    static class Payload {
        int first;
        Object reference;
        long wide;
    }
    static int[] allocateInts(int n) { return new int[n]; }
    static Object[] allocateObjects(int n) { return new Object[n]; }
    static byte[] allocateBytes(int n) { return new byte[n]; }
    static int[] cloneInts(int[] a) { return a.clone(); }
    static Object[] cloneObjects(Object[] a) { return a.clone(); }
    static void copy(int[] src, int s, int[] dst, int d, int n) {
        System.arraycopy(src, s, dst, d, n);
    }
    static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        for (int round = 0; round < 40000; round++) {
            int n = round % 129;
            int[] ints = allocateInts(n);
            byte[] bytes = allocateBytes(n);
            Object[] objects = allocateObjects(n);
            check(ints.length == n && bytes.length == n && objects.length == n,
                  "allocation length: " + n);
            for (int i = 0; i < n; i++) {
                check(ints[i] == 0 && bytes[i] == 0 && objects[i] == null,
                      "allocation not zeroed");
                ints[i] = i * 0x13579 + round;
                objects[i] = ints;
            }
            int[] ic = cloneInts(ints);
            Object[] oc = cloneObjects(objects);
            check(ic != ints && Arrays.equals(ic, ints), "int clone");
            check(oc != objects && Arrays.equals(oc, objects), "object clone");
            Payload p = new Payload();
            escaped = p;
            check(p.first == 0 && p.reference == null && p.wide == 0,
                  "instance fields not zeroed");
            p.first = round;
            p.reference = oc;
            p.wide = 0x1234567800000000L | round;
            synchronized (p) {
                synchronized (p) {
                    check(p.first == round && p.reference == oc &&
                          p.wide == (0x1234567800000000L | round),
                          "locking overwrote fields");
                }
            }
            check(p.getClass() == Payload.class && p instanceof Payload,
                  "class lookup");
            System.identityHashCode(p);
        }
        int[] src = new int[64];
        for (int i = 0; i < src.length; i++) src[i] = i * 0x1234567;
        for (int round = 0; round < 40; round++) {
            for (int s = 0; s < 12; s++) {
                for (int d = 0; d < 12; d++) {
                    for (int n = 0; n <= 24; n++) {
                        int[] dst = new int[64];
                        int[] expected = new int[64];
                        Arrays.fill(dst, -1);
                        Arrays.fill(expected, -1);
                        for (int i = 0; i < n; i++) expected[d + i] = src[s + i];
                        copy(src, s, dst, d, n);
                        check(Arrays.equals(dst, expected),
                              "disjoint copy: " + s + "," + d + "," + n);
                        dst = src.clone();
                        expected = src.clone();
                        for (int i = 0; i < n; i++) expected[d + i] = src[s + i];
                        copy(dst, s, dst, d, n);
                        check(Arrays.equals(dst, expected),
                              "overlap copy: " + s + "," + d + "," + n);
                    }
                }
            }
        }
        System.out.println("ArrayHeaderSmoke passed");
    }
}
