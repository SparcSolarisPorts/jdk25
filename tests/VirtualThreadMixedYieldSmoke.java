import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.LockSupport;

public class VirtualThreadMixedYieldSmoke {
    public static void main(String[] args) throws Exception {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread[] threads = new Thread[8];
        for (int t = 0; t < threads.length; t++) {
            final int seed = t;
            threads[t] = Thread.ofVirtual().start(() -> {
                try {
                    Object live = new Object();
                    int identity = System.identityHashCode(live);
                    long value = seed;
                    for (int i = 0; i < 20000; i++) {
                        long expected = (value * 31) ^ i;
                        value = expected;
                        LockSupport.parkNanos(1000);
                        if (value != expected || System.identityHashCode(live) != identity) {
                            throw new AssertionError("live value changed across park");
                        }
                    }
                } catch (Throwable e) {
                    failure.compareAndSet(null, e);
                }
            });
        }
        for (Thread t : threads) t.join();
        if (failure.get() != null) throw new AssertionError(failure.get());
        System.out.println("PASS: virtual-thread mixed yield/resume and live values");
    }
}
