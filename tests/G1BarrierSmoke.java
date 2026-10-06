import java.util.HashMap;

public class G1BarrierSmoke {
    static final HashMap<Integer, byte[]> map = new HashMap<>();
    static volatile long checksum;
    static void churn(int round) {
        for (int key = 0; key < 16384; key++) {
            byte[] value = new byte[128];
            value[0] = (byte)(round ^ key);
            map.put(key, value);
        }
        long sum = 0;
        for (int key = 0; key < 16384; key++) {
            byte[] value = map.get(key);
            if (value == null || value[0] != (byte)(round ^ key))
                throw new AssertionError("corrupted map at " + round + "/" + key);
            sum += value[0];
        }
        if (sum != -8192) throw new AssertionError("wrong checksum: " + sum);
        checksum = sum;
    }
    public static void main(String[] args) {
        for (int round = 0; round < 100; round++) {
            churn(round);
            if (round % 10 == 0) System.gc();
        }
        System.out.println("PASS: HashMap updates, allocations, G1 collections and readback");
    }
}
