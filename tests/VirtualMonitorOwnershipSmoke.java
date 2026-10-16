import java.lang.reflect.Method;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

public class VirtualMonitorOwnershipSmoke {
    private static final Method START;
    static {
        try {
            START = Thread.class.getMethod("startVirtualThread", Runnable.class);
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }

    private static Thread start(boolean virtual, Runnable task,
                                AtomicReference<Throwable> failure) throws Exception {
        Runnable checked = () -> {
            try { task.run(); }
            catch (Throwable t) { failure.compareAndSet(null, t); }
        };
        if (virtual) return (Thread) START.invoke(null, checked);
        Thread thread = new Thread(checked);
        thread.setDaemon(true);
        thread.start();
        return thread;
    }

    private static void finish(Thread thread, AtomicReference<Throwable> failure) throws Exception {
        thread.join(10_000);
        Throwable t = failure.get();
        if (t != null) throw new AssertionError("worker failed", t);
        check(!thread.isAlive(), "worker did not finish");
    }

    private static void waitCase(boolean virtual, boolean interrupt) throws Exception {
        Object lock = new Object();
        CountDownLatch waiting = new CountDownLatch(1);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        boolean[] notified = { false };
        Thread worker = start(virtual, () -> {
            synchronized (lock) {
                check(Thread.holdsLock(lock), "not owner after monitorenter");
                waiting.countDown();
                try {
                    while (!notified[0]) lock.wait();
                    check(!interrupt, "wait returned normally instead of throwing InterruptedException");
                } catch (InterruptedException e) {
                    check(interrupt, "unexpected interrupt");
                }
                check(Thread.holdsLock(lock), "not owner after wait/interrupt");
            }
        }, failure);
        check(waiting.await(10, TimeUnit.SECONDS), "worker did not enter monitor");
        if (interrupt) {
            worker.interrupt();
        } else {
            synchronized (lock) {
                notified[0] = true;
                lock.notifyAll();
            }
        }
        finish(worker, failure);
    }

    private static void contention(boolean virtual) throws Exception {
        Object lock = new Object();
        CountDownLatch attempting = new CountDownLatch(1);
        AtomicInteger entered = new AtomicInteger();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread[] workers = new Thread[16];
        synchronized (lock) {
            for (int i = 0; i < workers.length; ++i) {
                workers[i] = start(virtual, () -> {
                    attempting.countDown();
                    synchronized (lock) {
                        check(Thread.holdsLock(lock), "contended monitorenter returned without ownership");
                        Thread.yield();
                        check(Thread.holdsLock(lock), "lost ownership after yield");
                        entered.incrementAndGet();
                    }
                }, failure);
            }
            check(attempting.await(10, TimeUnit.SECONDS), "no worker attempted monitor entry");
            check(entered.get() == 0, "worker entered a monitor owned by the main thread");
        }
        for (Thread worker : workers) finish(worker, failure);
        check(entered.get() == workers.length, "missing monitor entries");
    }

    public static void main(String[] args) throws Exception {
        for (boolean virtual : new boolean[] { false, true }) {
            for (int i = 0; i < 64; ++i) {
                waitCase(virtual, false);
                waitCase(virtual, true);
            }
            contention(virtual);
        }
        System.out.println("PASS: platform/virtual monitor contention, wait/notify, interrupt and ownership");
    }
}
