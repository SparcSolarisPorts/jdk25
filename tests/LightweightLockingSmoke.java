import java.lang.reflect.Method;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;

public class LightweightLockingSmoke {
    private final Object[] locks = new Object[16];
    private long count;
    private boolean ready;
    private synchronized native long nativeIncrement();
    private synchronized native long nativeCount();
    private static final AtomicReference<Throwable> failure = new AtomicReference<>();

    LightweightLockingSmoke() {
        for (int i = 0; i < locks.length; i++) locks[i] = new Object();
    }
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    private synchronized void increment() { count++; }
    private void recursive(Object lock, int depth) {
        synchronized (lock) {
            check(Thread.holdsLock(lock), "recursive ownership");
            if (depth != 0) recursive(lock, depth - 1);
        }
    }
    private void nested(int depth, boolean gc) {
        if (depth == locks.length) {
            for (Object lock : locks) check(Thread.holdsLock(lock), "nested ownership");
            if (gc) System.gc();
            return;
        }
        synchronized (locks[depth]) { nested(depth + 1, gc); }
    }
    private void exercise() {
        recursive(locks[0], 6);
        nested(0, false); // exceeds LockStack capacity
        synchronized (locks[0]) {
            synchronized (locks[1]) {
                synchronized (locks[0]) { check(Thread.holdsLock(locks[0]), "nonadjacent recursion"); }
            }
        }
        synchronized (locks[2]) {
            System.identityHashCode(locks[2]); // inflation while owned
            check(Thread.holdsLock(locks[2]), "hash ownership");
        }
        try {
            synchronized (locks[3]) { throw new IllegalStateException("test"); }
        } catch (IllegalStateException expected) { }
        check(!Thread.holdsLock(locks[3]), "exception exit");
    }
    private static Thread start(Runnable body, boolean virtual) throws Exception {
        Runnable guarded = () -> {
            try { body.run(); } catch (Throwable t) { failure.compareAndSet(null, t); }
        };
        if (virtual) {
            Method m = Thread.class.getMethod("startVirtualThread", Runnable.class);
            return (Thread)m.invoke(null, guarded);
        }
        Thread t = new Thread(guarded);
        t.start();
        return t;
    }
    private static void join(Thread t) throws Exception {
        t.join(30000);
        check(!t.isAlive(), "thread timed out");
        if (failure.get() != null) throw new AssertionError("worker failed", failure.get());
    }
    public static void main(String[] args) throws Exception {
        boolean virtual = args.length > 0 && args[0].equals("virtual");
        boolean jni = args.length > 0 && args[0].equals("native");
        if (jni) System.loadLibrary("LightweightLockingSmoke");
        LightweightLockingSmoke test = new LightweightLockingSmoke();
        for (int i = 0; i < 10000; i++) test.exercise();
        test.nested(0, true);
        Thread[] workers = new Thread[4];
        for (int i = 0; i < workers.length; i++) {
            workers[i] = start(() -> {
                for (int n = 0; n < 20000; n++) {
                    test.increment();
                    if (jni) test.nativeIncrement();
                    if ((n & 1023) == 0) test.exercise();
                }
            }, virtual);
        }
        for (Thread t : workers) join(t);
        check(test.count == 80000, "lost updates: " + test.count);
        if (jni) {
            check(test.nativeCount() == 80000, "JNI lost updates");
            synchronized (test) { test.nativeIncrement(); }
            check(test.nativeCount() == 80001, "recursive JNI lock");
        }
        CountDownLatch waiting = new CountDownLatch(1);
        Thread waiter = start(() -> {
            synchronized (test) {
                waiting.countDown();
                while (!test.ready) {
                    try { test.wait(10000); } catch (InterruptedException e) { throw new AssertionError(e); }
                }
                check(Thread.holdsLock(test), "wait reacquisition");
            }
        }, virtual);
        waiting.await();
        synchronized (test) { test.ready = true; test.notifyAll(); }
        join(waiter);
        if (virtual) {
            for (int i = 0; i < 32; i++) {
                final Object lock = new Object();
                join(start(() -> {
                    synchronized (lock) {
                        synchronized (lock) {
                            for (int n = 0; n < 8; n++) {
                                try { Thread.sleep(1); } catch (InterruptedException e) { throw new AssertionError(e); }
                                check(Thread.holdsLock(lock), "ownership after virtual-thread remount");
                                if (n == 4) System.gc();
                            }
                        }
                    }
                }, true));
            }
        }
        System.out.println("PASS lightweight locking " + (virtual ? "virtual" : jni ? "native" : "platform"));
    }
}
