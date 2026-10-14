import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.nio.ByteOrder;
import java.util.Arrays;
import jdk.incubator.vector.ByteVector;

public class VectorMemoryAlignmentSmoke {
    static void exercise(MemorySegment target, byte[] bytes, int offset) {
        target.fill((byte) 0xa5);
        ByteVector value = ByteVector.fromArray(ByteVector.SPECIES_64, bytes, 0);
        value.intoMemorySegment(target, offset, ByteOrder.nativeOrder());
        byte[] actual = ByteVector.fromMemorySegment(ByteVector.SPECIES_64,
                target, offset, ByteOrder.nativeOrder()).toArray();
        if (!Arrays.equals(bytes, actual)) throw new AssertionError("Bits changed at " + offset);
        byte[] all = target.toArray(ValueLayout.JAVA_BYTE);
        for (int i = 0; i < all.length; i++) {
            byte expected = i >= offset && i < offset + 8 ? bytes[i - offset] : (byte) 0xa5;
            if (all[i] != expected) throw new AssertionError("Unexpected write at " + i);
        }
        ByteVector.zero(ByteVector.SPECIES_64).intoMemorySegment(target, offset, ByteOrder.nativeOrder());
        all = target.toArray(ValueLayout.JAVA_BYTE);
        for (int i = 0; i < all.length; i++) {
            byte expected = i >= offset && i < offset + 8 ? 0 : (byte) 0xa5;
            if (all[i] != expected) throw new AssertionError("Unexpected zero write at " + i);
        }
    }
    public static void main(String[] args) {
        MemorySegment byteTarget = MemorySegment.ofArray(new byte[64]);
        MemorySegment floatTarget = MemorySegment.ofArray(new float[16]);
        byte[] bits = {0x7f, (byte) 0xf0, 0, 0, 0, 0, 0, 1};
        for (int pass = 0; pass < 20000; pass++) {
            bits[7] = (byte) pass;
            for (int offset = 0; offset < 8; offset++) {
                exercise(byteTarget, bits, offset);
                exercise(floatTarget, bits, offset);
            }
        }
        System.out.println("PASS: eight-byte vector loads/stores, all alignments, byte/float backing and zero stores");
    }
}
