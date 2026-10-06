/*
 * Exercise reference CAS and repeated ConcurrentHashMap.transfer compilation.
 * Run with G1 and C2, both with and without compressed oops.
 */
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;

public class ConcurrentHashMapResizeSmoke {
    private static final int THREADS = 4;
    private static final int KEYS = 8192;

    public static void main(String[] args) throws Exception {
        for (int round = 0; round < 24; round++) {
            ConcurrentHashMap<Integer, Integer> map = new ConcurrentHashMap<>(1);
            CountDownLatch start = new CountDownLatch(1);
            AtomicReference<Throwable> failure = new AtomicReference<>();
            Thread[] workers = new Thread[THREADS];
            for (int t = 0; t < THREADS; t++) {
                final int base = t * KEYS;
                workers[t] = new Thread(() -> {
                    try {
                        start.await();
                        for (int i = 0; i < KEYS; i++) {
                            int key = base + i;
                            if (map.putIfAbsent(key, key ^ 0x5a5a) != null) {
                                throw new AssertionError("duplicate key " + key);
                            }
                        }
                    } catch (Throwable e) {
                        failure.compareAndSet(null, e);
                    }
                });
                workers[t].start();
            }
            start.countDown();
            for (Thread worker : workers) worker.join();
            if (failure.get() != null) throw new AssertionError(failure.get());
            if (map.size() != THREADS * KEYS) throw new AssertionError("size " + map.size());
            for (int key = 0; key < THREADS * KEYS; key++) {
                Integer value = map.get(key);
                if (value == null || value != (key ^ 0x5a5a)) {
                    throw new AssertionError("wrong value for " + key);
                }
            }
            if ((round & 3) == 0) System.gc();
        }
        System.out.println("ConcurrentHashMapResizeSmoke PASS");
    }
}
