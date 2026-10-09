import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicIntegerArray;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.LockSupport;

public class VirtualThreadMixedYieldSmoke {
    public static void main(String[] args) throws Exception {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread[] threads = new Thread[8];
        AtomicIntegerArray progress = new AtomicIntegerArray(threads.length);
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
                        progress.set(seed, i + 1);
                    }
                } catch (Throwable e) {
                    failure.compareAndSet(null, e);
                }
            });
        }
        // Keep the original untimed joins: replacing them with timed joins
        // could hide a missed termination-latch notification.
        Thread watchdog = new Thread(() -> {
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(90);
            try {
                while (true) {
                    Thread.sleep(5000);
                    for (int i = 0; i < threads.length; i++) {
                        System.out.println("worker=" + i + " state=" + threads[i].getState()
                                + " alive=" + threads[i].isAlive()
                                + " iterations=" + progress.get(i));
                    }
                    if (System.nanoTime() >= deadline) {
                        System.err.println("FAIL: original virtual-thread joins did not finish within 90 seconds");
                        System.exit(2);
                    }
                }
            } catch (InterruptedException finished) {
                // Main finished every original join.
            }
        }, "mixed-yield-watchdog");
        watchdog.setDaemon(true);
        watchdog.start();
        for (Thread t : threads) t.join();
        watchdog.interrupt();
        if (failure.get() != null) throw new AssertionError(failure.get());
        for (int i = 0; i < threads.length; i++) {
            if (progress.get(i) != 20000) {
                throw new AssertionError("worker " + i + " completed only " + progress.get(i));
            }
        }
        System.out.println("PASS: virtual-thread mixed yield/resume and live values");
    }
}
