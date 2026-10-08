import java.nio.ByteOrder;
import jdk.internal.misc.Unsafe;

public class UnsafeAlignmentSmoke {
    static final Unsafe U = Unsafe.getUnsafe();
    static final long BASE = U.arrayBaseOffset(byte[].class);
    static final boolean BIG = ByteOrder.nativeOrder() == ByteOrder.BIG_ENDIAN;
    static void check(boolean ok, String what) {
        if (!ok) throw new AssertionError(what);
    }
    static long expected(byte[] a, int p, int n) {
        long v = 0;
        for (int i = 0; i < n; i++) {
            int j = BIG ? p + i : p + n - 1 - i;
            v = (v << 8) | (a[j] & 255L);
        }
        return v;
    }
    static void run(byte[] a, long nativeAddress, int iteration) {
        for (int offset = 0; offset < 8; offset++) {
            int p = 16 + offset;
            long field = BASE + p;
            for (int i = 0; i < 8; i++) a[p + i] = (byte)(iteration + i * 37);
            check(U.getShort(a, field) == (short)expected(a, p, 2), "short load");
            check(U.getChar(a, field) == (char)expected(a, p, 2), "char load");
            check(U.getInt(a, field) == (int)expected(a, p, 4), "int load");
            check(U.getLong(a, field) == expected(a, p, 8), "long load");
            check(Float.floatToRawIntBits(U.getFloat(a, field)) == (int)expected(a, p, 4), "float bits");
            check(Double.doubleToRawLongBits(U.getDouble(a, field)) == expected(a, p, 8), "double bits");
            long value = 0x8123456789abcdefL ^ iteration;
            a[p - 1] = 0x55; a[p + 8] = 0x66;
            U.putLong(a, field, value);
            check(expected(a, p, 8) == value, "long store");
            check(a[p - 1] == 0x55 && a[p + 8] == 0x66, "store boundary");
            U.putInt(a, field, (int)value);
            check(expected(a, p, 4) == (value & 0xffffffffL), "int store");
            U.putShort(a, field, (short)value);
            check(expected(a, p, 2) == (value & 65535), "short store");
            U.putChar(a, field, (char)value);
            check(expected(a, p, 2) == (value & 65535), "char store");
            // Finite patterns also check the floating point bit-transfer path.
            U.putFloat(a, field, Float.intBitsToFloat(0x41234567));
            check(expected(a, p, 4) == 0x41234567L, "float store");
            U.putDouble(a, field, Double.longBitsToDouble(0x4123456789abcdefL));
            check(expected(a, p, 8) == 0x4123456789abcdefL, "double store");
            long address = nativeAddress + offset;
            U.putLong(null, address, value);
            check(U.getLong(null, address) == value, "native long");
            U.putInt(null, address, (int)value);
            check(U.getInt(null, address) == (int)value, "native int");
        }
    }
    public static void main(String[] args) {
        long nativeAddress = U.allocateMemory(64);
        try {
            byte[] a = new byte[64];
            for (int i = 0; i < Integer.getInteger("iterations", 30000); i++) run(a, nativeAddress, i);
        } finally { U.freeMemory(nativeAddress); }
        System.out.println("PASS: plain Unsafe primitive accesses, every alignment, heap/native memory and bit patterns");
    }
}
