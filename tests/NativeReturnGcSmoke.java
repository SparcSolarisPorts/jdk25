import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Exercises interpreted/compiled JNI returns while G1 stops the world. */
public class NativeReturnGcSmoke {
    private static native Object echo(Object value);
    private static native long echoLong(long value);
    private static volatile Object sink;
    public static void main(String[] args) throws Exception {
        System.load(args[0]);
        int workers = args.length > 1 ? Integer.parseInt(args[1]) : 32;
        int iterations = args.length > 2 ? Integer.parseInt(args[2]) : 2000;
        CountDownLatch start = new CountDownLatch(1);
        AtomicBoolean running = new AtomicBoolean(true);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread[] threads = new Thread[workers];
        for (int w = 0; w < workers; w++) {
            final int id = w;
            threads[w] = new Thread(() -> {
                try {
                    start.await();
                    for (int i = 0; i < iterations; i++) {
                        byte[] value = new byte[256 + ((i * 17 + id) & 4095)];
                        value[0] = (byte)i;
                        if (echo(value) != value || value[0] != (byte)i)
                            throw new AssertionError("JNI reference identity/payload");
                        long token = ((long)id << 48) | (0x123456780000L + i);
                        if (echoLong(token) != token) throw new AssertionError("JNI long result");
                        // Allocate immediately after returning from native code.
                        sink = new Object[] { value, new byte[512 + (i & 2047)] };
                    }
                } catch (Throwable t) { failure.compareAndSet(null, t); }
            }, "native-return-" + w);
            threads[w].start();
        }
        Thread gc = new Thread(() -> {
            try {
                start.await();
                while (running.get()) { System.gc(); Thread.sleep(10); }
            } catch (Throwable t) { failure.compareAndSet(null, t); }
        }, "native-return-gc");
        gc.start();
        start.countDown();
        try {
            for (Thread thread : threads) thread.join();
        } finally { running.set(false); gc.join(); }
        if (failure.get() != null) throw new AssertionError("Worker failed", failure.get());
        System.out.println("PASS: JNI native returns, reference/long results, allocation and concurrent GC");
    }
}
